import json

from zilli.privacy.entities import EntityMap, EntityReplacer, EntityRestorer


class TestEntityReplacer:
    def test_replace_plain_text(self):
        replacer = EntityReplacer()
        result, emap = replacer.replace("Contact me at alice@example.com please")
        assert "alice@example.com" not in result
        assert "[EMAIL]" in result
        assert emap.get("[EMAIL]") == "alice@example.com"

    def test_replace_multiple_same_category(self):
        replacer = EntityReplacer()
        result, emap = replacer.replace("a@x.com and b@y.com")
        assert "[EMAIL]" in result
        assert "[EMAIL_1]" in result
        assert emap.get("[EMAIL]") == "a@x.com"
        assert emap.get("[EMAIL_1]") == "b@y.com"

    def test_replace_no_pii_unchanged(self):
        replacer = EntityReplacer()
        result, emap = replacer.replace("Just a plain sentence.")
        assert result == "Just a plain sentence."
        assert emap.replacements == {}

    def test_replace_dict(self):
        replacer = EntityReplacer()
        data = {"user": {"phone": "13800138000", "email": "alex@corp.com"}, "note": "hello"}
        result, emap = replacer.replace(data)
        assert "[PHONE]" in result["user"]["phone"]
        assert "[EMAIL]" in result["user"]["email"]
        assert result["note"] == "hello"
        assert emap.get("[PHONE]") == "13800138000"
        assert emap.get("[EMAIL]") == "alex@corp.com"

    def test_replace_nested_list(self):
        replacer = EntityReplacer()
        data = [{"users": ["alice@a.com", "bob@b.com"]}]
        result, emap = replacer.replace(data)
        assert "[EMAIL]" in result[0]["users"][0]
        assert "[EMAIL_1]" in result[0]["users"][1]

    def test_replace_json_string(self):
        replacer = EntityReplacer()
        raw = json.dumps({"customer": "Jane Doe", "phone": "13900139000"})
        result, emap = replacer.replace(raw)
        parsed = json.loads(result)
        assert parsed["customer"] == "Jane Doe"
        assert "[PHONE]" in parsed["phone"]
        assert emap.get("[PHONE]") == "13900139000"

    def test_replace_scalar_values(self):
        replacer = EntityReplacer()
        result, emap = replacer.replace(42)
        assert result == 42
        assert emap.replacements == {}


class TestEntityRestorer:
    def test_restore_plain_text(self):
        replacer = EntityReplacer()
        restorer = EntityRestorer()
        original = "Call 13800138000 today"
        sanitized, emap = replacer.replace(original)
        restored = restorer.restore(sanitized, emap)
        assert restored == original

    def test_restore_nested_dict(self):
        replacer = EntityReplacer()
        restorer = EntityRestorer()
        original = {"user": {"phone": "13800138000", "email": "a@x.com"}, "tags": ["x"]}
        sanitized, emap = replacer.replace(original)
        restored = restorer.restore(sanitized, emap)
        assert restored == original

    def test_restore_json_string(self):
        replacer = EntityReplacer()
        restorer = EntityRestorer()
        original = json.dumps({"patient": "Lucy Liu", "mrn": "13911113999"})
        sanitized, emap = replacer.replace(original)
        restored = restorer.restore(sanitized, emap)
        assert json.loads(restored) == json.loads(original)

    def test_restore_multiple_same_category(self):
        replacer = EntityReplacer()
        restorer = EntityRestorer()
        original = "Mail a@x.com and b@y.com now"
        sanitized, emap = replacer.replace(original)
        restored = restorer.restore(sanitized, emap)
        assert restored == original

    def test_restore_unknown_placeholder_ignored(self):
        restorer = EntityRestorer()
        emap = EntityMap(replacements={"[NAME]": "Alice"})
        assert restorer.restore("Hi [NAME] and [PHONE]", emap) == "Hi Alice and [PHONE]"

    def test_restore_empty_map_unchanged(self):
        restorer = EntityRestorer()
        emap = EntityMap()
        assert restorer.restore("plain text", emap) == "plain text"

    def test_restore_scalar_passthrough(self):
        restorer = EntityRestorer()
        emap = EntityMap(replacements={"[NAME]": "Alice"})
        assert restorer.restore(7, emap) == 7

    def test_roundtrip_nested_mixed(self):
        replacer = EntityReplacer()
        restorer = EntityRestorer()
        original = {
            "report": [
                {"contact": "CEO: carol@board.com", "amount": 100},
                "note: phone 13900000000",
            ]
        }
        sanitized, emap = replacer.replace(original)
        restored = restorer.restore(sanitized, emap)
        assert restored == original

    def test_entity_map_serialization(self):
        emap = EntityMap(replacements={"[NAME]": "Alice"}, findings=[])
        data = emap.to_dict()
        assert data["replacements"]["[NAME]"] == "Alice"
        assert data["findings"] == 0
        emap2 = EntityMap.from_dict(data)
        assert emap2.get("[NAME]") == "Alice"
