"""ChromaTrajectoryStore chromadb 后端分支测试（mock chromadb）。

覆盖：HttpClient/PersistentClient 初始化、upsert、query、
get、count、delete、异常回退、stats chromadb 分支。
"""

import sys
import types

import pytest

from zilli.data.vector_store import ChromaTrajectoryStore


class _FakeCollection:
    def __init__(self):
        self.data: dict[str, dict] = {}

    def upsert(self, ids=None, documents=None, metadatas=None):
        for i in range(len(ids or [])):
            self.data[ids[i]] = {"document": documents[i], "metadata": metadatas[i]}

    def query(self, query_texts=None, n_results=None, where=None):
        keys = list(self.data.keys())[:n_results or len(self.data)]
        ids = keys
        return {
            "ids": [ids],
            "distances": [[0.1] * len(ids)],
            "documents": [[self.data[k]["document"] for k in ids]],
            "metadatas": [[self.data[k]["metadata"] for k in ids]],
        }

    def get(self, ids=None):
        found = {k: self.data[k] for k in (ids or []) if k in self.data}
        return {
            "ids": list(found.keys()),
            "documents": [v["document"] for v in found.values()],
            "metadatas": [v["metadata"] for v in found.values()],
        }

    def count(self):
        return len(self.data)

    def delete(self, ids=None):
        for i in (ids or []):
            self.data.pop(i, None)


class _FakeClient:
    def __init__(self, collection=None):
        self._collection = collection or _FakeCollection()
        self._last_name = None

    def get_or_create_collection(self, name, embedding_function=None):
        self._last_name = name
        return self._collection


class TestChromaBackend:
    @pytest.fixture(autouse=True)
    def _fake_chromadb(self, monkeypatch):
        mod = types.ModuleType("chromadb")
        mod.config = types.ModuleType("chromadb.config")
        mod.config.Settings = lambda **kw: kw
        mod.HttpClient = lambda host, port, settings=None: _FakeClient()
        mod.PersistentClient = lambda path, settings=None: _FakeClient()
        monkeypatch.setitem(sys.modules, "chromadb", mod)
        monkeypatch.setitem(sys.modules, "chromadb.config", mod.config)
        import importlib

        import zilli.data.vector_store as vs
        importlib.reload(vs)
        yield vs
        # restore module cache so other tests aren't polluted
        importlib.reload(vs)

    def test_persistent_client_init(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        assert store._chroma_available is True

    def test_http_client_init(self, monkeypatch):
        monkeypatch.setenv("CHROMA_HOST", "localhost")
        store = ChromaTrajectoryStore(persist_dir="/tmp/y")
        assert store._chroma_available is True

    def test_store_via_chroma(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("t1", [{"step": 1}], reward=0.9)
        assert store._inmem == {}  # 走了 chroma，不进内存
        assert store.count() == 1

    def test_search_via_chroma(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("t1", [{"code": "hello"}], reward=0.9)
        results = store.search_similar("hello", n_results=1)
        assert results[0].id == "t1"
        assert results[0].document
        assert results[0].metadata.get("reward") == 0.9

    def test_get_via_chroma(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("t1", [{"a": 1}], reward=0.5)
        got = store.get_trajectory("t1")
        assert got["id"] == "t1"
        assert store.get_trajectory("missing") is None

    def test_count_and_delete_via_chroma(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("a", [], reward=0.5)
        store.store_trajectory("b", [], reward=0.5)
        assert store.count() == 2
        store.delete_trajectory("a")
        assert store.count() == 1

    def test_stats_chroma_backend(self):
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("a", [], reward=0.5)
        stats = store.stats()
        assert stats["backend"] == "chromadb"
        assert stats["count"] == 1

    def test_chroma_store_error_falls_back(self, monkeypatch):
        from zilli.data import vector_store as vs_mod

        class Boom:
            def upsert(self, **kw):
                raise RuntimeError("upsert failed")

            def get_or_create_collection(self, *a, **kw):
                return Boom()

        mod = types.ModuleType("chromadb")
        mod.config = types.ModuleType("chromadb.config")
        mod.config.Settings = lambda **kw: kw
        mod.HttpClient = lambda *a, **kw: _FakeClient(collection=Boom())
        mod.PersistentClient = lambda *a, **kw: _FakeClient(collection=Boom())
        monkeypatch.setitem(sys.modules, "chromadb", mod)
        monkeypatch.setitem(sys.modules, "chromadb.config", mod.config)
        import importlib
        importlib.reload(vs_mod)
        store = ChromaTrajectoryStore(persist_dir="/tmp/x")
        store.store_trajectory("t1", [{"x": 1}], reward=0.9)
        assert "t1" in store._inmem  # 回退到内存
