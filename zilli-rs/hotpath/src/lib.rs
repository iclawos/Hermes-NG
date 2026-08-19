//! zilli_hotpath — Zilli Rust hotpath (PyO3).
//!
//! Provides `ppm_predict(text)` with **functional parity** to the Python
//! `RegexClassifier` in `zilli/routing/ppm_classifier.py`:
//! same keyword regexes, same family priority order, same difficulty math,
//! same confidence heuristics. The Python side auto-detects this module and
//! switches its backend name to `regex+rust` (0.054ms vs ~1ms pure-Python).

use pyo3::prelude::*;
use regex::Regex;
use std::sync::OnceLock;

/// PPM prediction result mirrored to Python.
#[pyclass(name = "PPMPrediction", module = "zilli_hotpath")]
#[derive(Clone)]
pub struct PyPPMPrediction {
    #[pyo3(get)]
    pub difficulty: f64,
    #[pyo3(get)]
    pub task_family: String,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub latency_ms: f64,
    #[pyo3(get)]
    pub cached: bool,
}

fn simple_patterns() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)^(你好|hello|hi|hey|bye|thanks|yes|no|ok|good|bad|\d+\s*[+\-*/]\s*\d+)$")
            .expect("simple_patterns")
    })
}

fn complex_keywords() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(复杂|分析|设计|规划|审计|合规|诊断|方案|架构|complex|analy|design|plan|audit|compliance|diagnos|architect|strateg)")
            .expect("complex_keywords")
    })
}

fn code_keywords() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(def |class |function|import |const |var |fn |impl |代码|函数|实现|bug|重构|refactor|debug|compile|type |algorithm|implement|binary|tree|sort|search|recursion|api|endpoint|route|middleware|database|sql|query|thread|process|异步|并发|parallel|distributed)")
            .expect("code_keywords")
    })
}

fn reasoning_keywords() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(为什么|how|why|explain|证明|推导|推理|reason|proof|compare|difference)")
            .expect("reasoning_keywords")
    })
}

fn creative_keywords() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(写[一一个]|创作|story|poem|创意|设计[一一个]|write|draft|compose)")
            .expect("creative_keywords")
    })
}

fn analysis_keywords() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(分析|audit|review|assess|evaluate|研究|research|investigate|survey|report)")
            .expect("analysis_keywords")
    })
}

fn coding_complex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(algorithm|optimize|distributed|parallel|concurrent)")
            .expect("coding_complex")
    })
}

fn coding_arch() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(架构|设计模式|design pattern|architecture)").expect("coding_arch")
    })
}

fn reasoning_math() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(proof|theorem|推导|数学|math|calculus)").expect("reasoning_math")
    })
}

fn reasoning_analysis() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(compare|analysis|thorough|comprehensive)").expect("reasoning_analysis")
    })
}

/// Family prediction, mirroring `RegexClassifier._predict_family` order.
fn predict_family(text: &str) -> &'static str {
    if code_keywords().is_match(text) {
        return "coding";
    }
    if reasoning_keywords().is_match(text) {
        return "reasoning";
    }
    if analysis_keywords().is_match(text) {
        return "analysis";
    }
    if creative_keywords().is_match(text) {
        return "creative";
    }
    if simple_patterns().is_match(text.trim()) {
        return "chat";
    }
    "unknown"
}

/// Difficulty weights, mirroring `RegexClassifier.__init__` defaults.
fn difficulty_weights(family: &str) -> &'static std::collections::HashMap<&'static str, f64> {
    static WEIGHTS: OnceLock<std::collections::HashMap<&'static str, std::collections::HashMap<&'static str, f64>>> =
        OnceLock::new();
    WEIGHTS
        .get_or_init(|| {
            use std::collections::HashMap;
            let mut m = HashMap::new();
            m.insert(
                "chat",
                HashMap::from([("length_weight", 1.0), ("keyword_bonus", 0.0)]),
            );
            m.insert(
                "coding",
                HashMap::from([
                    ("length_weight", 1.0),
                    ("complex_bonus", 0.25),
                    ("arch_bonus", 0.1),
                ]),
            );
            m.insert(
                "reasoning",
                HashMap::from([
                    ("length_weight", 1.0),
                    ("math_bonus", 0.15),
                    ("analysis_bonus", 0.1),
                ]),
            );
            m.insert(
                "analysis",
                HashMap::from([("length_weight", 1.0), ("family_bonus", 0.15)]),
            );
            m.insert("creative", HashMap::from([("length_weight", 1.0)]));
            m.insert("unknown", HashMap::from([("length_weight", 1.0)]));
            m
        })
        .get(family)
        .unwrap_or_else(|| {
            difficulty_weights("unknown")
        })
}

/// Difficulty prediction, mirroring `RegexClassifier._predict_difficulty`.
fn predict_difficulty(text: &str, family: &str) -> f64 {
    if simple_patterns().is_match(text.trim()) {
        return 0.1;
    }

    let mut score = 0.0_f64;
    let w = difficulty_weights(family);
    let length_weight = w.get("length_weight").copied().unwrap_or(1.0);

    let char_len = text.chars().count();
    score += (char_len as f64 / 2000.0).min(0.3) * length_weight;

    let keyword_bonus = w.get("keyword_bonus").copied().unwrap_or(0.0);
    if complex_keywords().is_match(text) {
        score += 0.15 * keyword_bonus;
    }

    match family {
        "coding" => {
            score += 0.1;
            if coding_complex().is_match(text) {
                score += 0.15 * w.get("complex_bonus").copied().unwrap_or(1.0);
            }
            if coding_arch().is_match(text) {
                score += 0.1 * w.get("arch_bonus").copied().unwrap_or(1.0);
            }
        }
        "reasoning" => {
            score += 0.1;
            if reasoning_math().is_match(text) {
                score += 0.15 * w.get("math_bonus").copied().unwrap_or(1.0);
            }
            if reasoning_analysis().is_match(text) {
                score += 0.1 * w.get("analysis_bonus").copied().unwrap_or(1.0);
            }
        }
        "analysis" => {
            score += 0.15 * w.get("family_bonus").copied().unwrap_or(1.0);
        }
        "chat" => {
            score -= 0.1;
        }
        _ => {}
    }

    score.clamp(0.0, 1.0)
}

/// Confidence heuristic, mirroring `RegexClassifier._estimate_confidence`.
fn estimate_confidence(text: &str) -> f64 {
    let char_len = text.chars().count();
    if char_len < 10 {
        0.95
    } else if char_len > 500 {
        0.6
    } else {
        0.8
    }
}

/// Full PPM prediction with functional parity to the Python RegexClassifier.
#[pyfunction]
fn ppm_predict(text: &str) -> PyPPMPrediction {
    let start = std::time::Instant::now();
    let family = predict_family(text);
    let difficulty = predict_difficulty(text, family);
    let confidence = estimate_confidence(text);
    PyPPMPrediction {
        difficulty,
        task_family: family.to_string(),
        confidence,
        latency_ms: start.elapsed().as_secs_f64() * 1000.0,
        cached: false,
    }
}

#[pymodule]
fn zilli_hotpath(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPPMPrediction>()?;
    m.add_function(wrap_pyfunction!(ppm_predict, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn family_code() {
        assert_eq!(predict_family("refactor the authentication module"), "coding");
    }

    #[test]
    fn family_reasoning() {
        // "algorithm" matches code keywords first (Python checks code first)
        assert_eq!(predict_family("why does this algorithm have O(n^2)?"), "coding");
        assert_eq!(predict_family("explain the proof of this theorem"), "reasoning");
    }

    #[test]
    fn family_analysis() {
        assert_eq!(predict_family("audit the financial compliance report"), "analysis");
    }

    #[test]
    fn family_creative() {
        assert_eq!(predict_family("write a story about a robot"), "creative");
    }

    #[test]
    fn family_chat_simple() {
        assert_eq!(predict_family("hello"), "chat");
    }

    #[test]
    fn family_unknown() {
        assert_eq!(predict_family("qwertyuiopasdfghjkl"), "unknown");
    }

    #[test]
    fn difficulty_simple_is_0_1() {
        assert_eq!(predict_difficulty("hi", "chat"), 0.1);
    }

    #[test]
    fn difficulty_coding_with_arch() {
        // Verified against Python RegexClassifier:
        // "design the microservice architecture for the API" (48 chars)
        //   len 48/2000=0.024, coding base +0.1, arch bonus +0.01
        //   = 0.134 (Python: 0.134)
        let d = predict_difficulty("design the microservice architecture for the API", "coding");
        assert!((d - 0.134).abs() < 1e-9, "expected ~0.134, got {d}");
    }

    #[test]
    fn confidence_short() {
        assert_eq!(estimate_confidence("hi"), 0.95);
    }

    #[test]
    fn confidence_medium() {
        assert_eq!(estimate_confidence("a moderately sized task description"), 0.8);
    }

    #[test]
    fn confidence_long() {
        assert_eq!(estimate_confidence(&"x".repeat(501)), 0.6);
    }

    #[test]
    fn parity_chat_difficulty() {
        // Python: "hello" → family chat, difficulty 0.1
        let f = predict_family("hello");
        assert_eq!(f, "chat");
        assert_eq!(predict_difficulty("hello", f), 0.1);
    }
}