from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger("zilli.loops.unknowns")


class UnknownCategory(str, Enum):
    KNOWN_KNOWN = "known_known"
    KNOWN_UNKNOWN = "known_unknown"
    UNKNOWN_KNOWN = "unknown_known"
    UNKNOWN_UNKNOWN = "unknown_unknown"


@dataclass
class UnknownItem:
    id: str
    description: str
    category: UnknownCategory
    context: str = ""
    resolved: bool = False
    resolution: str = ""
    impact: str = ""
    discovered_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0


@dataclass
class BlindSpotReport:
    unknowns: list[UnknownItem]
    suggested_prompts: list[str]
    codebase_gaps: list[str]
    risk_areas: list[str]
    generated_at: float = field(default_factory=time.time)


@dataclass
class ImplementationNote:
    timestamp: float
    category: str
    decision: str
    reason: str
    deviation: bool = False
    original_plan: str = ""


@dataclass
class QuizQuestion:
    question: str
    options: list[str]
    correct_answer: int
    explanation: str


@dataclass
class QuizResult:
    total_questions: int
    correct_answers: int
    passed: bool
    score: float
    questions: list[QuizQuestion] = field(default_factory=list)


class UnknownsDiscovery:
    """Discovers unknowns before, during, and after implementation.

    Implements the Fable 5 methodology for finding unknowns:
    - Pre-implementation: blind spot pass, brainstorms, interviews, references
    - During implementation: implementation notes with deviation tracking
    - Post-implementation: pitches/explainers, quizzes
    """

    def __init__(self, work_dir: str = "./unknowns"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._notes_file = self.work_dir / "implementation-notes.md"
        self._unknowns_file = self.work_dir / "unknowns.json"
        self._unknowns: list[UnknownItem] = []
        self._notes: list[ImplementationNote] = []
        self._load()

    def _load(self) -> None:
        if self._unknowns_file.exists():
            try:
                data = json.loads(self._unknowns_file.read_text())
                for u in data:
                    if "category" in u and not isinstance(u["category"], UnknownCategory):
                        u["category"] = UnknownCategory(u["category"])
                self._unknowns = [UnknownItem(**u) for u in data]
            except Exception as e:
                logger.warning("Failed to load unknowns: %s", e)

    def _save(self) -> None:
        data = [
            {
                "id": u.id,
                "description": u.description,
                "category": u.category.value,
                "context": u.context,
                "resolved": u.resolved,
                "resolution": u.resolution,
                "impact": u.impact,
                "discovered_at": u.discovered_at,
                "resolved_at": u.resolved_at,
            }
            for u in self._unknowns
        ]
        self._unknowns_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def blind_spot_pass(
        self,
        task_description: str,
        codebase_context: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
    ) -> BlindSpotReport:
        """Analyze codebase and task to find unknown unknowns.

        Args:
            task_description: What the user wants to accomplish
            codebase_context: Relevant code/files context
            llm_fn: Async function that takes a prompt and returns LLM response
        """
        prompt = f"""You are helping a developer discover their unknowns before implementation.

Task: {task_description}

Codebase context:
{codebase_context}

Analyze this task and identify:
1. Unknown Unknowns - things the developer doesn't know they don't know
2. Known Unknowns - things they know they need to figure out
3. Codebase gaps - missing pieces that could block implementation
4. Risk areas - potential failure points

For each unknown, provide:
- A clear description
- Why it matters for this task
- Suggested prompt to discover more

Format your response as JSON:
{{
    "unknowns": [
        {{"description": "...", "category": "unknown_unknown|known_unknown", "impact": "high|medium|low", "suggested_prompt": "..."}}
    ],
    "codebase_gaps": ["..."],
    "risk_areas": ["..."]
}}"""

        response = await llm_fn(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"unknowns": [], "codebase_gaps": [], "risk_areas": []}

        unknowns = []
        for i, u in enumerate(data.get("unknowns", [])):
            unknowns.append(UnknownItem(
                id=f"bs_{int(time.time())}_{i}",
                description=u.get("description", ""),
                category=UnknownCategory(u.get("category", "unknown_unknown")),
                impact=u.get("impact", "medium"),
                context=task_description,
            ))

        suggested_prompts = [u.get("suggested_prompt", "") for u in data.get("unknowns", [])]

        report = BlindSpotReport(
            unknowns=unknowns,
            suggested_prompts=suggested_prompts,
            codebase_gaps=data.get("codebase_gaps", []),
            risk_areas=data.get("risk_areas", []),
        )

        self._unknowns.extend(unknowns)
        self._save()

        return report

    async def generate_interview_questions(
        self,
        task_description: str,
        existing_unknowns: list[UnknownItem],
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
    ) -> list[str]:
        """Generate interview questions to resolve unknowns."""
        unknowns_text = "\n".join([
            f"- {u.description} ({u.category.value}, impact: {u.impact})"
            for u in existing_unknowns if not u.resolved
        ])

        prompt = f"""Based on the task and unresolved unknowns, generate interview questions.

Task: {task_description}

Unresolved unknowns:
{unknowns_text}

Generate 3-5 interview questions that would help clarify the most critical unknowns.
Prioritize questions where the answer would change the architecture or approach.

Format as JSON array: ["question 1", "question 2", ...]"""

        response = await llm_fn(prompt)

        try:
            questions = json.loads(response)
            if isinstance(questions, list):
                return questions
        except json.JSONDecodeError:
            pass

        return [
            f"What is the expected behavior for: {u.description}?"
            for u in existing_unknowns[:3] if not u.resolved
        ]

    def log_decision(
        self,
        category: str,
        decision: str,
        reason: str,
        deviation: bool = False,
        original_plan: str = "",
    ) -> None:
        """Log an implementation decision or deviation."""
        note = ImplementationNote(
            timestamp=time.time(),
            category=category,
            decision=decision,
            reason=reason,
            deviation=deviation,
            original_plan=original_plan,
        )
        self._notes.append(note)

        with open(self._notes_file, "a") as f:
            f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(note.timestamp))}\n")
            f.write(f"**Category**: {category}\n")
            if deviation:
                f.write(f"**DEVIATION from plan**: {original_plan}\n")
            f.write(f"**Decision**: {decision}\n")
            f.write(f"**Reason**: {reason}\n")

    def get_notes(self, deviation_only: bool = False) -> list[ImplementationNote]:
        """Get implementation notes, optionally filtered to deviations only."""
        if deviation_only:
            return [n for n in self._notes if n.deviation]
        return self._notes

    async def generate_quiz(
        self,
        changes_summary: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
        num_questions: int = 5,
    ) -> list[QuizQuestion]:
        """Generate quiz questions about the changes made."""
        prompt = f"""Based on these changes, generate {num_questions} quiz questions to verify understanding.

Changes summary:
{changes_summary}

For each question:
- Ask about a specific behavior or decision
- Provide 4 multiple choice options
- Indicate the correct answer (0-indexed)
- Provide an explanation

Format as JSON:
[
    {{
        "question": "...",
        "options": ["a", "b", "c", "d"],
        "correct_answer": 0,
        "explanation": "..."
    }}
]"""

        response = await llm_fn(prompt)

        try:
            data = json.loads(response)
            return [QuizQuestion(**q) for q in data]
        except (json.JSONDecodeError, TypeError):
            return []

    async def brainstorm(
        self,
        task_description: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
        num_variants: int = 4,
    ) -> list[dict[str, str]]:
        """Generate diverse solution prototypes for reactive selection.

        Surfaces unknown knowns — criteria the user can only define when
        they see it. Cheap prototypes before expensive implementation.
        """
        prompt = f"""Brainstorm {num_variants} WILDLY DIFFERENT approaches for this task.

Task: {task_description}

Requirements for each variant:
- Radically different from each other (not minor tweaks)
- Include a one-line pitch, key tradeoff, and cheapest prototype step
- Order from cheapest to most ambitious

Format as JSON array:
[
    {{"name": "...", "pitch": "...", "tradeoff": "...", "prototype_step": "...", "cost": "low|medium|high"}}
]"""

        response = await llm_fn(prompt)
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        return []

    async def distill_reference(
        self,
        reference_path: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
        goal: str = "",
        max_chars: int = 8000,
    ) -> str:
        """Read a reference implementation and distill its semantics.

        Source code is the richest reference — richer than screenshots or
        prose descriptions of desired behavior.
        """
        path = Path(reference_path)
        if path.is_dir():
            chunks = []
            for f in sorted(path.rglob("*")):
                if f.is_file() and f.suffix in (".py", ".rs", ".ts", ".js", ".go", ".md", ".toml"):
                    try:
                        chunks.append(f"--- {f.relative_to(path)} ---\n{f.read_text(errors='replace')[:2000]}")
                    except OSError:
                        continue
                if sum(len(c) for c in chunks) > max_chars:
                    break
            content = "\n".join(chunks)[:max_chars]
        elif path.is_file():
            content = path.read_text(errors="replace")[:max_chars]
        else:
            return f"Reference not found: {reference_path}"

        prompt = f"""Distill the KEY SEMANTICS of this reference implementation.

Goal: {goal or 'understand what behavior to replicate'}

Reference content:
{content}

Extract:
1. Core behavior/semantics worth replicating (be precise: algorithms, state machines, protocols)
2. Key design decisions and their rationale
3. Edge cases handled
4. A one-paragraph "implementation brief" usable as prompt context

Be concise. Output plain text."""

        return await llm_fn(prompt)

    async def generate_plan(
        self,
        task_description: str,
        context: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
    ) -> str:
        """Generate an implementation plan with volatile decisions first.

        Lead with decisions the user is most likely to tweak: data models,
        type interfaces, UX flows. Bury mechanical refactoring at the bottom.
        """
        prompt = f"""Write an implementation plan for this task.

Task: {task_description}

Context:
{context}

Structure (STRICT order):
## 1. Decisions You'll Want to Tweak
Lead with data model changes, new type interfaces, and anything user-facing.
For each: the decision, the alternatives, and the default choice.

## 2. UX / Behavior Flow
Step-by-step user-visible behavior.

## 3. Implementation Steps
Ordered, mechanical. Trust the engineer on these.

## 4. Risks & Edge Cases
What could go wrong, mitigation per item.

Output Markdown."""

        plan = await llm_fn(prompt)
        plan_path = self.work_dir / "implementation-plan.md"
        plan_path.write_text(plan, encoding="utf-8")
        return plan

    async def package_pitch(
        self,
        title: str,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ) -> str:
        """Package spec, plan, and implementation notes into a single doc.

        Accelerates reviewer understanding and buy-in approvals.
        """
        notes = self.get_notes()
        deviations = self.get_notes(deviation_only=True)
        unresolved = self.get_unresolved()

        plan_path = self.work_dir / "implementation-plan.md"
        plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else "(no plan)"

        notes_md = "\n".join(
            f"- **{n.category}** {'(DEVIATION) ' if n.deviation else ''}{n.decision} — {n.reason}"
            for n in notes
        ) or "(no decisions logged)"

        unknowns_md = "\n".join(
            f"- [{u.category.value}] {u.description}" for u in unresolved
        ) or "(all unknowns resolved)"

        pitch = f"""# {title}

## Implementation Plan
{plan_text}

## Decision Log ({len(notes)} decisions, {len(deviations)} deviations)
{notes_md}

## Open Unknowns ({len(unresolved)})
{unknowns_md}

---
Generated by Zilli UnknownsDiscovery · {time.strftime('%Y-%m-%d %H:%M')}
"""
        pitch_path = self.work_dir / "pitch.md"
        pitch_path.write_text(pitch, encoding="utf-8")
        return pitch

    def resolve_unknown(self, unknown_id: str, resolution: str) -> bool:
        """Mark an unknown as resolved."""
        for u in self._unknowns:
            if u.id == unknown_id:
                u.resolved = True
                u.resolution = resolution
                u.resolved_at = time.time()
                self._save()
                return True
        return False

    def get_unresolved(self, category: UnknownCategory | None = None) -> list[UnknownItem]:
        """Get unresolved unknowns, optionally filtered by category."""
        unresolved = [u for u in self._unknowns if not u.resolved]
        if category:
            unresolved = [u for u in unresolved if u.category == category]
        return unresolved

    def summary(self) -> dict[str, Any]:
        """Get summary of unknowns discovery state."""
        by_category = {}
        for u in self._unknowns:
            cat = u.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "resolved": 0}
            by_category[cat]["total"] += 1
            if u.resolved:
                by_category[cat]["resolved"] += 1

        return {
            "total_unknowns": len(self._unknowns),
            "resolved": len([u for u in self._unknowns if u.resolved]),
            "unresolved": len([u for u in self._unknowns if not u.resolved]),
            "by_category": by_category,
            "implementation_notes": len(self._notes),
            "deviations": len([n for n in self._notes if n.deviation]),
        }


__all__ = [
    "UnknownCategory",
    "UnknownItem",
    "BlindSpotReport",
    "ImplementationNote",
    "QuizQuestion",
    "QuizResult",
    "UnknownsDiscovery",
]
