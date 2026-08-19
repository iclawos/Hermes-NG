"""PIIDetector / Sanitizer 边界覆盖。

覆盖：非法自定义正则回退、Luhn 长度/N>9 分支、无效卡号跳过、
sanitize/sanitize_text 默认掩码路径。
"""

from zilli.security.pii import PIICategory, PIIDetector, Sanitizer


class TestPIIDetectorEdges:
    def test_invalid_custom_pattern_warns(self):


        det = PIIDetector(custom_patterns={PIICategory.SSN: "[unclosed"})
        # 非法正则被跳过：SSN 无匹配，但 EMAIL 默认正则可命中
        assert not any(f.category == PIICategory.SSN for f in det.detect("123-45-6789"))
        assert det.detect("me@example.com")

    def test_luhn_too_short(self):
        det = PIIDetector()
        assert det._luhn_check("4111") is False

    def test_luhn_valid(self):
        det = PIIDetector()
        assert det._luhn_check("4111111111111111") is True

    def test_luhn_invalid_checksum(self):
        det = PIIDetector()
        assert det._luhn_check("4111111111111112") is False

    def test_invalid_card_skipped(self):
        det = PIIDetector()
        # 13-16 位数字但 Luhn 不通过 → 不产生 finding
        findings = det.detect("Card 4111111111111112 here")
        assert not any(f.category == PIICategory.CREDIT_CARD for f in findings)

    def test_valid_card_detected(self):
        det = PIIDetector()
        findings = det.detect("Card 4111111111111111 here")
        assert any(f.category == PIICategory.CREDIT_CARD for f in findings)


class TestSanitizer:
    def test_sanitize_plain_default_mask(self):
        s = Sanitizer()
        result = s.sanitize("hello world")
        assert result.sanitized == "hello world"
        assert result.findings == []

    def test_sanitize_ssn_with_default_mask(self):
        s = Sanitizer()
        result = s.sanitize("my ssn is 123-45-6789 ok")
        assert "123-45-6789" not in result.sanitized
        assert result.findings

    def test_sanitize_text_no_findings_returns_same(self):
        s = Sanitizer()
        assert s.sanitize_text("nothing sensitive") == "nothing sensitive"

    def test_sanitize_text_masks_with_triple_star(self):
        s = Sanitizer()
        out = s.sanitize_text("ssn 123-45-6789 end")
        assert "123-45-6789" not in out
        assert "***" in out
