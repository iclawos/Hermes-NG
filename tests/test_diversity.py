from __future__ import annotations

from zilli.evolution.diversity import (
    DiversityController,
    code_fingerprint,
    fingerprint_similarity,
    jaccard_similarity,
    ngram_fingerprint,
)


def test_code_fingerprint_extracts_elements():
    source = "import os\ndef foo(x):\n    return x + 1\n\n\nclass Bar:\n    pass\n"
    fp = code_fingerprint(source)
    assert "foo" in fp["functions"]
    assert "Bar" in fp["classes"]
    assert fp["n_lines"] == 8


def test_jaccard_similarity():
    a = {"a", "b", "c"}
    b = {"a", "b", "d"}
    sim = jaccard_similarity(a, b)
    assert sim == 2 / 4


def test_identical_fingerprints_have_similarity_1():
    source = "def foo(x):\n    return x + 1\n\n\ndef bar(y):\n    return y * 2\n"
    fp1 = code_fingerprint(source)
    fp2 = code_fingerprint(source)
    assert fingerprint_similarity(fp1, fp2) > 0.99


def test_different_fingerprints_have_low_similarity():
    fp1 = code_fingerprint("def foo(): pass")
    fp2 = code_fingerprint("class Bar: pass")
    assert fingerprint_similarity(fp1, fp2) < 0.5


def test_ngram_fingerprint():
    result = ngram_fingerprint("hello", n=2)
    assert "he" in result
    assert "el" in result
    assert "ll" in result
    assert "lo" in result


def test_diversity_controller_accepts_novel():
    dc = DiversityController(novelty_threshold=0.5, population_size=10)
    assert dc.add_entry("a", "def foo(): pass", score=1.0)
    assert dc.add_entry("a", "class Bar: pass", score=0.8)
    assert len(dc.population) == 2


def test_diversity_controller_rejects_similar():
    dc = DiversityController(novelty_threshold=0.9, population_size=10)
    dc.add_entry("a", "def foo(x): return x + 1", score=1.0)
    assert not dc.add_entry("b", "def bar(x): return x - 1", score=0.9)


def test_diversity_metrics():
    dc = DiversityController(population_size=10, novelty_threshold=0.2)
    dc.add_entry("a", "def foo(): return 1", score=1.0)
    dc.add_entry("b", "class Bar: pass", score=0.5)
    metrics = dc.diversity_metrics()
    assert metrics["population_size"] == 2
    assert metrics["unique_functions"] >= 1


def test_prune_keeps_top():
    dc = DiversityController(population_size=3)
    for i in range(10):
        dc.add_entry(f"e{i}", f"def fn{i}(): return {i}", score=float(i))
    assert len(dc.population) <= 3


def test_next_generation_increments():
    dc = DiversityController()
    assert dc.diversity_metrics()["generation"] == 0
    dc.next_generation()
    assert dc.diversity_metrics()["generation"] == 1


def test_select_parent():
    dc = DiversityController()
    parent = dc.select_parent([0.1, 0.9], ["weak", "strong"])
    assert parent in ("weak", "strong")


def test_logging_does_not_crash():
    dc = DiversityController()
    dc.log_diversity()
    dc.add_entry("a", "def foo(): pass", score=1.0)
    dc.log_diversity()
    assert len(dc.diversity_log) == 2
