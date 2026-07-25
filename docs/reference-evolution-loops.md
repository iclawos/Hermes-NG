# Reference: Evolution & Loops API

## SkillEvolutionEngine

```
zilli.evolution.SkillEvolutionEngine(reflection_model, cost_controller, diversity_controller, mode, mom_router)
```

Modes: `evolve` (4-strategy), `harness` (MOM-routed reflection).

| Method | Returns | Description |
|--------|---------|-------------|
| `evolve(skill_file, trajectory_data)` | str (PR diff) | Single-strategy evolution |
| `evolve_multi_strategy(skill_file, trajectory_data)` | list[str] | All 4 strategies gated by diversity |
| `evolve_concurrent(skill_files, trajectory_data)` | list[str] | Async concurrent evolution |
| `evolve_multi_strategy_concurrent(...)` | list[str] | Concurrent multi-strategy |

Strategies: `prompt_optimization`, `error_handling`, `boundary_refinement`, `tool_addiction`.

## DiversityController

```
zilli.evolution.DiversityController(population_size, novelty_threshold, parent_temperature, use_ngram)
```

6-dim weighted Jaccard fingerprint + character n-gram + fitness sharing + temperature parent selection.

| Method | Returns | Description |
|--------|---------|-------------|
| `add_entry(entry_id, source, threshold)` | bool | False = rejected as too similar |
| `diversity_metrics()` | dict | population_size, pairwise_similarity, unique_functions, generation |
| `select_parent()` | str | Temperature-weighted parent choice |

## LoopRunner

```
zilli.loops.LoopRunner(process_fn, verifier, trigger, max_retries, correction_fn, name)
```

Generic Retry → Verify → Correct loop.

| Method | Returns | Description |
|--------|---------|-------------|
| `run(input_data)` | LoopResult | Cycles until verify passes or retries exhausted |
| `run_forever(input_data)` | None | Trigger-driven continuous mode |

## MetaLoopRunner

```
zilli.loops.MetaLoopRunner(inner_runner, meta_verifier, max_meta_iterations, improvement_threshold, mode, harness_orchestrator)
```

Modes: `param_tune` (numeric tuning) / `harness_evolve` (Self-Harness: WeaknessMiner → bounded edits → held-in/out validation).

## Verifiers

| Class | Verify by |
|-------|-----------|
| `TestSuiteVerifier(command, timeout, cwd)` | subprocess exit code |
| `PredicateVerifier(predicate)` | boolean function |
| `ExternalModelVerifier(model)` | LLM PASS/FAIL judgment |
| `SkillVerifier(skill_path, model)` | skill rules file |
| `CompositeVerifier(verifiers, require_all)` | aggregation |

## Triggers

`FixedIntervalTrigger(seconds)` / `EventTrigger()` / `DynamicIntervalTrigger(fn)`

## UnknownsDiscovery (Fable)

```
zilli.loops.UnknownsDiscovery(work_dir)
```

| Method | Description |
|--------|-------------|
| `blind_spot_pass(task, context, llm_fn)` | Unknown unknowns scan |
| `generate_interview_questions(task, unknowns, llm_fn)` | Clarifying questions |
| `brainstorm(task, llm_fn, num_variants)` | Diverse prototypes |
| `distill_reference(path, llm_fn, goal)` | Reference → implementation brief |
| `generate_plan(task, context, llm_fn)` | Volatile-decisions-first plan |
| `package_pitch(title)` | Bundle plan + notes + unknowns |
| `log_decision(category, decision, reason, deviation)` | Implementation notes |
| `resolve_unknown(id, resolution)` | Close unknown |
| `summary()` | Category counts |

## HarnessOrchestrator

```
zilli.loops.HarnessOrchestrator(...)
```

Self-Harness cycle: `run_cycle(traces)` → `HarnessCandidate` (accepted if held-in improvement ≥5% and no held-out regression).

## EvolveToTrainPipeline

```
zilli.pipeline.EvolveToTrainPipeline(config, evolution_engine, trainer)
```

Full loop: EVOLVE → TRAIN → DEPLOY (ChampionChallenger) → MONITOR. `run_cycle()` returns stage records; `summary()` reports champion.
