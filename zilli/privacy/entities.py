from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from zilli.security.pii import PIEFinding, PIIDetector

logger = logging.getLogger("zilli.privacy.entities")

_PLACEHOLDER_RE = re.compile(r"\[([A-Z_]+)(?:_(\d+))?\]")


@dataclass
class EntityMap:
    """Placeholder → original value mapping produced by EntityReplacer."""

    replacements: dict[str, str] = field(default_factory=dict)
    findings: list[PIEFinding] = field(default_factory=list)

    def get(self, placeholder: str) -> Optional[str]:
        return self.replacements.get(placeholder)

    def to_dict(self) -> dict[str, Any]:
        return {"replacements": self.replacements, "findings": len(self.findings)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntityMap":
        return cls(replacements=dict(data.get("replacements", {})), findings=[])


class EntityReplacer:
    """Replace PII entities with category placeholders (e.g. ``[NAME]``).

    Supports nested structures: plain strings, dicts, lists, and JSON-encoded
    strings. Each distinct occurrence of the same category gets a unique
    placeholder (``[NAME]``, ``[NAME_1]``, ``[NAME_2]`` ...) so the mapping is
    unambiguous when restored.
    """

    def __init__(self, detector: Optional[PIIDetector] = None):
        self.detector = detector or PIIDetector()

    def replace(self, value: Any) -> tuple[Any, EntityMap]:
        entity_map = EntityMap()
        counters: dict[str, int] = {}
        result = self._replace_value(value, entity_map, counters)
        return result, entity_map

    def _replace_value(
        self, value: Any, entity_map: EntityMap, counters: dict[str, int]
    ) -> Any:
        if isinstance(value, dict):
            return {
                k: self._replace_value(v, entity_map, counters)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._replace_value(v, entity_map, counters) for v in value]
        if isinstance(value, tuple):
            return tuple(self._replace_value(v, entity_map, counters) for v in value)
        if isinstance(value, str):
            return self._replace_text(value, entity_map, counters)
        return value

    def _replace_text(
        self, text: str, entity_map: EntityMap, counters: dict[str, int]
    ) -> str:
        stripped = text.strip()
        if stripped.startswith(("{", "[")) and _looks_like_json(text):
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if parsed is not None:
                replaced = self._replace_value(parsed, entity_map, counters)
                return json.dumps(replaced, ensure_ascii=False)
            return self._replace_inline(text, entity_map, counters)
        return self._replace_inline(text, entity_map, counters)

    def _replace_inline(
        self, text: str, entity_map: EntityMap, counters: dict[str, int]
    ) -> str:
        findings = self.detector.detect(text)
        if not findings:
            return text
        findings.sort(key=lambda f: f.start)
        steps = []
        for finding in findings:
            placeholder = self._placeholder_for(finding.category.value, counters)
            entity_map.replacements[placeholder] = finding.text
            steps.append((finding.start, finding.end, placeholder))
        result = text
        for start, end, placeholder in reversed(steps):
            result = result[:start] + placeholder + result[end:]
        return result

    def _placeholder_for(self, category: str, counters: dict[str, int]) -> str:
        index = counters.get(category, 0)
        counters[category] = index + 1
        if index == 0:
            return f"[{category.upper()}]"
        return f"[{category.upper()}_{index}]"


class EntityRestorer:
    """Restore placeholders back to original values.

    Mirrors EntityReplacer's nested traversal: dicts, lists, tuples and
    JSON-encoded strings are handled recursively, so a model response that
    echoes the structure of the sanitized request is restored faithfully.
    """

    def restore(self, value: Any, entity_map: EntityMap) -> Any:
        if not entity_map.replacements:
            return value
        return self._restore_value(value, entity_map)

    def _restore_value(self, value: Any, entity_map: EntityMap) -> Any:
        if isinstance(value, dict):
            return {
                k: self._restore_value(v, entity_map)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._restore_value(v, entity_map) for v in value]
        if isinstance(value, tuple):
            return tuple(self._restore_value(v, entity_map) for v in value)
        if isinstance(value, str):
            return self._restore_text(value, entity_map)
        return value

    def _restore_text(self, text: str, entity_map: EntityMap) -> str:
        stripped = text.strip()
        if stripped.startswith(("{", "[")) and _looks_like_json(text):
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if parsed is not None:
                restored = self._restore_value(parsed, entity_map)
                return json.dumps(restored, ensure_ascii=False)
        return self._restore_inline(text, entity_map)

    def _restore_inline(self, text: str, entity_map: EntityMap) -> str:
        matches = list(_PLACEHOLDER_RE.finditer(text))
        if not matches:
            return text
        result = text
        for match in reversed(matches):
            placeholder = match.group(0)
            original = entity_map.replacements.get(placeholder)
            if original is None:
                continue
            result = result[: match.start()] + original + result[match.end():]
        return result


def _looks_like_json(text: str) -> bool:
    return text[:1] in ("{", "[") and text[-1:] in ("}", "]")


__all__ = ["EntityMap", "EntityReplacer", "EntityRestorer"]
