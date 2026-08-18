import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional

from zilli.evolution.diversity import DiversityController

logger = logging.getLogger(__name__)


class SkillEvolutionEngine:
    def __init__(self, reflection_model: Optional[str] = None,
                 cost_controller=None,
                 diversity_controller: Optional[DiversityController] = None,
                 mode: str = "evolve",
                 mom_router: Optional[Any] = None):
        self.reflection_model = reflection_model or os.environ.get("ZILLI_REFLECTION_MODEL")
        self.cost_controller = cost_controller
        self.diversity = diversity_controller or DiversityController()
        self.mode = mode
        self.mom_router = mom_router
        self.max_iterations = 10
        self.evolution_strategies = [
            "prompt_optimization",
            "error_handling",
            "boundary_refinement",
            "tool_addiction",
        ]
        self._cost_log: List[Dict] = []

    def _check_budget(self) -> bool:
        if not self.cost_controller:
            return True
        return self.cost_controller.should_use_planner("evolution", {"max_prob": 0.6})

    def _record_planner(self, success: bool = True):
        if self.cost_controller:
            self.cost_controller.record_planner_call("evolution", success)
            self._cost_log.append({"event": "planner_call", "success": success})
            if len(self._cost_log) > 100:
                self._cost_log = self._cost_log[-100:]

    def _record_executor(self, success: bool = True):
        if self.cost_controller:
            self.cost_controller.record_executor_call("evolution", success)
            self._cost_log.append({"event": "executor_call", "success": success})
            if len(self._cost_log) > 100:
                self._cost_log = self._cost_log[-100:]

    def _wrap_with_cost(self, skill_file: str, trajectory_data: List[Dict],
                         strategy: str) -> tuple[str, Dict]:
        module = self._wrap_as_dspy_module(skill_file)
        if strategy and not self._check_budget():
            self._record_executor()
            return self._generate_pr(module, skill_file, "executor_only"), module
        reflections = self._reflect_on_trajectories(trajectory_data)
        optimized = self._apply_evolution(module, reflections, strategy)
        pr = self._generate_pr(optimized, skill_file, strategy)
        if strategy != "executor_only":
            self._record_planner()
        return pr, optimized

    def evolve(self, skill_file: str, trajectory_data: List[Dict]) -> str:
        module = self._wrap_as_dspy_module(skill_file)
        if not self._check_budget():
            self._record_executor()
            return self._generate_pr(module, skill_file, "executor_only")

        if self.mode == "harness" and self.mom_router:
            route_text = f"{skill_file} evolution"
            try:
                asyncio.get_running_loop()
                logger.warning(
                    "evolve() called from async context; skipping sync MOM route "
                    "(use async evolve methods for MOM routing)"
                )
            except RuntimeError:
                try:
                    decision = asyncio.run(self.mom_router.route(route_text))
                    self.reflection_model = decision.model_id
                except Exception:
                    pass

        reflections = self._reflect_on_trajectories(trajectory_data)
        strategy = self._select_strategy(module, reflections)
        optimized = self._apply_evolution(module, reflections, strategy)

        source = optimized.get("improved_source") or module.get("source", "")
        entry_id = f"{skill_file}::{self.diversity.diversity_metrics()['generation']}"
        if source and not self.diversity.add_entry(entry_id, source, 0.5):
            logger.info("Rejected %s — too similar to existing population", skill_file)
            self._record_executor()
            return self._generate_pr(module, skill_file, "diversity_rejected")

        pr = self._generate_pr(optimized, skill_file, strategy)
        self._record_planner()
        self.diversity.log_diversity()

        if self.mode == "harness" and self.mom_router:
            try:
                self.mom_router.record_feedback(
                    request_id=f"evolve::{skill_file}",
                    ppm_difficulty=0.5,
                    ppm_family="coding",
                    selected_model=self.reflection_model or "default",
                    strategy_tier="standard",
                    actual_latency_ms=0,
                    actual_cost=0,
                    success=("diversity_rejected" not in pr),
                    score=0.7 if "diversity_rejected" not in pr else 0.3,
                )
            except Exception:
                pass

        return pr

    def evolve_multi_strategy(self, skill_file: str, trajectory_data: List[Dict]) -> List[str]:
        prs = []
        for strategy in self.evolution_strategies:
            pr, optimized = self._wrap_with_cost(skill_file, trajectory_data, strategy)
            improved = optimized.get("improved_source") or optimized.get("source", "")
            if improved:
                entry_id = f"{skill_file}::{strategy}::{self.diversity.diversity_metrics()['generation']}"
                if not self.diversity.add_entry(entry_id, improved, 0.3):
                    prs.append(f"# Diversity rejected: {strategy}")
                    continue
            prs.append(pr)
        self.diversity.next_generation()
        self.diversity.log_diversity()
        return prs

    async def evolve_async(self, skill_file: str, trajectory_data: List[Dict]) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.evolve, skill_file, trajectory_data,
        )

    async def evolve_concurrent(
        self,
        skill_files: List[str],
        trajectory_data: List[Dict],
        max_concurrency: int = 4,
    ) -> Dict[str, str]:
        sem = asyncio.Semaphore(max_concurrency)
        results: Dict[str, str] = {}

        async def _evolve_one(sf: str) -> tuple[str, str]:
            async with sem:
                pr = await self.evolve_async(sf, trajectory_data)
                return sf, pr

        tasks = [_evolve_one(sf) for sf in skill_files]
        for coro in asyncio.as_completed(tasks):
            sf, pr = await coro
            results[sf] = pr
        return results

    async def evolve_multi_strategy_async(
        self,
        skill_file: str,
        trajectory_data: List[Dict],
    ) -> List[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.evolve_multi_strategy, skill_file, trajectory_data,
        )

    async def evolve_multi_strategy_concurrent(
        self,
        skill_files: List[str],
        trajectory_data: List[Dict],
        max_concurrency: int = 4,
    ) -> Dict[str, List[str]]:
        sem = asyncio.Semaphore(max_concurrency)
        results: Dict[str, List[str]] = {}

        async def _evolve_one(sf: str) -> tuple[str, List[str]]:
            async with sem:
                prs = await self.evolve_multi_strategy_async(sf, trajectory_data)
                return sf, prs

        tasks = [_evolve_one(sf) for sf in skill_files]
        for coro in asyncio.as_completed(tasks):
            sf, prs = await coro
            results[sf] = prs
        return results

    def _wrap_as_dspy_module(self, skill_file: str) -> Dict:
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                source = f.read()
        except (FileNotFoundError, IOError, UnicodeDecodeError):
            source = ""
        functions = re.findall(r"def\s+(\w+)\s*\(.*?\):", source, re.DOTALL)
        classes = re.findall(r"class\s+(\w+)\s*[\(:]", source)
        imports = re.findall(r"^(?:from|import)\s+(\S+)", source, re.MULTILINE)
        docstrings = re.findall(r'"""(.*?)"""', source, re.DOTALL)[:3]
        return {
            "file": skill_file,
            "source": source,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "docstrings": docstrings,
            "lines": len(source.split("\n")) if source else 0,
            "signature": "input -> output",
            "status": "wrapped",
        }

    def _reflect_on_trajectories(self, trajectories: List[Dict]) -> List[str]:
        reflections = []
        for traj in trajectories:
            for step in traj:
                if isinstance(step, dict):
                    obs = step.get("observation", {})
                    if isinstance(obs, dict):
                        err = obs.get("error", "")
                        if err:
                            reflections.append(f"Error: {err}")
                            break
        return reflections[:10]

    def _route_reflection(self, reflections: list[str]) -> str:
        if self.mode == "harness" and self.mom_router and reflections:
            text = " ".join(reflections)
            try:
                asyncio.get_running_loop()
                logger.warning(
                    "_route_reflection() called from async context; "
                    "using cached reflection model"
                )
            except RuntimeError:
                try:
                    decision = asyncio.run(self.mom_router.route(text))
                    return decision.model_id or self.reflection_model or "default"
                except Exception:
                    pass
        return self.reflection_model or "default"

    def _select_strategy(self, module: Dict, reflections: List[str]) -> str:
        if not module.get("source"):
            return "tool_addiction"
        if reflections:
            return "error_handling"
        if len(module.get("functions", [])) > 3:
            return "boundary_refinement"
        return "prompt_optimization"

    def _apply_evolution(self, module: Dict, reflections: List[str],
                          strategy: str) -> Dict:
        optimized = dict(module)
        optimized["reflections"] = reflections
        optimized["strategy"] = strategy
        optimized["iterations"] = min(len(reflections) + 1, self.max_iterations)

        source = module.get("source", "")
        if not source:
            return self._evolve_empty(optimized, strategy)

        if strategy == "prompt_optimization":
            return self._evolve_prompt(optimized, source)
        if strategy == "error_handling":
            return self._evolve_error(optimized, source)
        if strategy == "boundary_refinement":
            return self._evolve_boundary(optimized, source)

        return self._evolve_empty(optimized, strategy)

    def _evolve_prompt(self, optimized: Dict, source: str) -> Dict:
        optimized["prompt_optimized"] = True
        lines = source.split("\n")
        improved = []
        in_docstring = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = line[:len(line) - len(line.lstrip())]
            if stripped.startswith('"""'):
                improved.append(line)
                if not stripped.endswith('"""') or len(stripped) == 3:
                    in_docstring = not in_docstring
                continue
            if in_docstring:
                improved.append(line)
                if stripped.endswith('"""'):
                    in_docstring = False
                continue
            if stripped.startswith("def ") and i > 1:
                improved.append(line)
                improved.append(f"{indent}    # TODO: add docstring and type hints")
            else:
                improved.append(line)
        optimized["improved_source"] = "\n".join(improved)
        return optimized

    def _evolve_error(self, optimized: Dict, source: str) -> Dict:
        optimized["error_handling_added"] = True
        lines = source.split("\n")
        improved = []
        i = 0
        while i < len(lines):
            line = lines[i]
            improved.append(line)
            stripped = line.strip()
            if stripped.startswith("def ") and "error" not in stripped.lower():
                body_start = i + 1
                while body_start < len(lines) and (
                    not lines[body_start].strip()
                    or lines[body_start].strip().startswith(('"""', "'''", "#"))
                ):
                    body_start += 1
                if body_start < len(lines):
                    body_indent = lines[body_start][:len(lines[body_start]) - len(lines[body_start].lstrip())]
                    if not any(e in lines[min(body_start, len(lines)-1)] for e in ("try:", "except", "raise")):
                        improved.append(f"{body_indent}try:")
                        last_j = body_start - 1
                        for j in range(body_start, min(body_start + 5, len(lines))):
                            if lines[j].strip() and not lines[j].strip().startswith(("def ", "class ", "@", "#")):
                                improved.append(f"{body_indent}    {lines[j].lstrip()}")
                                last_j = j
                            else:
                                break
                        improved.append(f"{body_indent}except Exception:")
                        improved.append(f"{body_indent}    pass")
                        i = last_j
            i += 1
        optimized["improved_source"] = "\n".join(improved)
        return optimized

    def _evolve_boundary(self, optimized: Dict, source: str) -> Dict:
        optimized["boundary_refined"] = True
        lines = source.split("\n")
        improved = []
        for i, line in enumerate(lines):
            improved.append(line)
            stripped = line.strip()
            indent = line[:len(line) - len(line.lstrip())]
            if stripped.startswith("def ") and "def " in source:
                params = stripped[len("def "):]
                fn_name = params.split("(")[0].strip() if "(" in params else ""
                if fn_name:
                    improved.append(f"{indent}    # Guard: validate inputs for {fn_name}")
                    if "None" in source:
                        improved.append(f"{indent}    # Guard: check for None inputs")
                    if "int" in source or "float" in source:
                        improved.append(f"{indent}    # Guard: validate numeric bounds")
        optimized["improved_source"] = "\n".join(improved)
        if optimized.get("functions"):
            optimized["boundary_info"] = (
                f"Functions: {', '.join(optimized['functions'][:5])}"
            )
        return optimized

    def _evolve_empty(self, optimized: Dict, strategy: str) -> Dict:
        if strategy == "tool_addiction":
            optimized["tool_addicted"] = True
            fn_name = "evolved_skill"
            optimized["improved_source"] = (
                f"def {fn_name}(input: str) -> str:\n"
                f'    """Auto-evolved by Zilli."""\n'
                f"    return f\"Processed: {{input}}\"\n"
            )
            optimized["functions"] = [fn_name]
        return optimized

    def _generate_pr(self, optimized: Dict, skill_file: str,
                      strategy: str = "auto") -> str:
        strategy_label = strategy.replace("_", " ").title()
        diff_lines = [
            f"--- a/{skill_file}",
            f"+++ b/{skill_file}",
            "@@ -1,3 +1,5 @@",
            " # Auto-evolved by Zilli SkillEvolutionEngine",
            f" # Strategy: {strategy_label}",
            f" # Model: {self.reflection_model}",
            f" # Iterations: {optimized.get('iterations', 1)}",
            f" # Functions: {len(optimized.get('functions', []))}",
        ]
        if strategy == "diversity_rejected":
            diff_lines.insert(3, "# Diversity rejected")
        if optimized.get("improved_source"):
            diff_lines.append(f"+# Evolved source ({len(optimized['improved_source'].split(chr(10)))} lines)")
        if optimized.get("reflections"):
            for ref in optimized["reflections"][:3]:
                diff_lines.append(f"+# Reflection: {ref}")
        diff_lines.append("")
        if optimized.get("improved_source"):
            diff_lines.append(optimized["improved_source"])
        return "\n".join(diff_lines)


__all__ = ["SkillEvolutionEngine"]
