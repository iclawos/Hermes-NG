import json

from zilli.data.vector_store import ChromaTrajectoryStore, VectorSearchResult


class TestInMemoryFallback:
    def test_store_and_get(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("t1", [{"step": 1}], reward=0.9)
        result = store.get_trajectory("t1")
        assert result is not None
        assert result["id"] == "t1"
        assert json.loads(result["document"]) == [{"step": 1}]
        assert result["metadata"]["reward"] == 0.9

    def test_type_classification_golden(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("g1", [], reward=0.9)
        assert store.get_trajectory("g1")["metadata"]["type"] == "golden"

    def test_type_classification_failure(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("f1", [], reward=0.2)
        assert store.get_trajectory("f1")["metadata"]["type"] == "failure"

    def test_type_classification_neutral(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("n1", [], reward=0.5)
        assert store.get_trajectory("n1")["metadata"]["type"] == "neutral"

    def test_custom_type_preserved(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("c1", [], reward=0.9, metadata={"type": "custom"})
        assert store.get_trajectory("c1")["metadata"]["type"] == "custom"

    def test_custom_metadata_merged(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("m1", [], reward=0.9, metadata={"task": "coding", "lang": "py"})
        meta = store.get_trajectory("m1")["metadata"]
        assert meta["task"] == "coding"
        assert meta["lang"] == "py"

    def test_get_missing_returns_none(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        assert store.get_trajectory("missing") is None

    def test_count(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        assert store.count() == 0
        store.store_trajectory("a", [], reward=0.5)
        store.store_trajectory("b", [], reward=0.5)
        assert store.count() == 2

    def test_delete(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("d1", [], reward=0.5)
        store.delete_trajectory("d1")
        assert store.get_trajectory("d1") is None
        assert store.count() == 0

    def test_stats(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store.store_trajectory("s1", [], reward=0.5)
        stats = store.stats()
        assert stats["collection"] == "zilli_trajectories"
        assert stats["count"] == 1
        assert stats["backend"] in ("chromadb", "in_memory")


class TestInMemorySearch:
    def test_keyword_search(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store._chroma_available = False
        store.store_trajectory("py", [{"code": "def hello python"}], reward=0.9)
        store.store_trajectory("js", [{"code": "function hello javascript"}], reward=0.9)
        results = store.search_similar("python code")
        assert len(results) >= 1
        assert results[0].id == "py"

    def test_search_filter_metadata(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store._chroma_available = False
        store.store_trajectory("g1", [{"x": "same content"}], reward=0.9)
        store.store_trajectory("f1", [{"x": "same content"}], reward=0.1)
        results = store.search_similar("same content", filter_metadata={"type": "golden"})
        assert all(r.metadata.get("type") == "golden" for r in results)
        assert any(r.id == "g1" for r in results)
        assert not any(r.id == "f1" for r in results)

    def test_search_empty_query(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store._chroma_available = False
        store.store_trajectory("a", [{"x": "data"}], reward=0.5)
        results = store.search_similar("")
        assert len(results) == 1

    def test_search_n_results_limit(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store._chroma_available = False
        for i in range(10):
            store.store_trajectory(f"t{i}", [{"x": "common term"}], reward=0.5)
        results = store.search_similar("common term", n_results=3)
        assert len(results) == 3

    def test_keyword_score_partial_match(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        assert store._keyword_score("foo bar", "foo baz") == 0.5
        assert store._keyword_score("", "anything") == 0.0
        assert store._keyword_score("foo", "") == 0.0

    def test_distance_is_inverse_score(self):
        store = ChromaTrajectoryStore(persist_dir="/nonexistent_dir_xyz/nope")
        store._chroma_available = False
        store.store_trajectory("full", [{"x": "alpha beta"}], reward=0.5)
        results = store.search_similar("alpha beta")
        assert results[0].distance == 0.0


class TestVectorSearchResult:
    def test_defaults(self):
        r = VectorSearchResult(id="x", distance=0.5)
        assert r.metadata == {}
        assert r.document == ""
