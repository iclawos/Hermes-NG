# Reference: Routing API

## RouteClassifier

```
zilli.routing.RouteClassifier
```

Classifies requests into `FAST_LANE` (direct execution) or `FULL_ROUTE` (Plan→Execute→Review).

| Method | Returns | Description |
|--------|---------|-------------|
| `classify(request)` | RouteDecision | Regex + optional LLM classification |

## LocalHybridRouter

```
zilli.routing.LocalHybridRouter(registry, classifier, config, cache, planner_budget, mom_router)
```

Three-stage hybrid router with sanitization, caching, and budget control.

| Method | Returns | Description |
|--------|---------|-------------|
| `run(request, industry, force_full_route)` | RouteResult | Full routing pipeline |
| `plan(request, industry)` | str | Planner stage |
| `execute(plan, request, industry)` | str | Executor stage |
| `review(plan, draft, request, industry)` | str | Reviewer stage |

`RouteResult` fields: `final_text`, `route_type`, `decision`, `planner_result`, `executor_result`, `reviewer_result`, `total_duration_ms`, `error`.

## MOMRouter (GPS-MOM)

```
zilli.routing.mom_router.MOMRouter(ppm, profile, strategy, feedback, budget_provider, train_every)
```

Four-step predictive routing: PPM → Strategy → Profile → Selection.

| Method | Returns | Description |
|--------|---------|-------------|
| `route(text, context)` | RouteDecision | Predictive model selection |
| `record_feedback(...)` | None | Record outcome (auto-triggers PPM training every `train_every` records) |
| `train_ppm_from_feedback(records)` | dict | Manual production training |
| `update_profile_from_feedback(model_id, success, score)` | None | ELO + capability update |
| `stats()` | dict | ppm + profile + training counters |

## PPMPredictor

```
zilli.routing.PPMPredictor(cache_size, timeout_ms, learning_rate, classifier)
```

Classifier chain: trained model (`ZILLI_PPM_MODEL` / `./models/ppm_model*.{joblib,onnx}`) → RegexClassifier (auto-uses Rust hotpath when `zilli_hotpath` installed).

| Method | Returns | Description |
|--------|---------|-------------|
| `predict(text, context)` | PPMPrediction | difficulty + family + confidence (LRU cached) |
| `train(records)` | dict | Online weight update from prediction-vs-actual |
| `reset_training()` | None | Restore factory weights |
| `stats()` | dict | cache + weights + classifier name |

## ModelProfile

```
zilli.routing.ModelProfile(exploration_factor)
```

| Method | Description |
|--------|-------------|
| `register(entry)` / `unregister(model_id)` | Model lifecycle |
| `update_success_rate(model_id, success)` | Bayesian EMA update |
| `update_capability(model_id, scores)` | 5-dim capability vector EMA |
| `filter(task_family, max_cost, min_success_rate)` | Candidate filtering |
| `select_best(task_family, candidates)` | Softmax Thompson selection |

## FeedbackCollector

```
zilli.routing.FeedbackCollector(persist_path, batch_size, flush_interval_seconds)
```

Async queue + JSONL batch persistence. Early flush when queue reaches `batch_size`.

## StrategySelector

```
zilli.routing.StrategySelector
```

Three tiers: `ECONOMY` / `STANDARD` / `ENHANCED`, selected by difficulty + budget status.

## DynamicSOTAScheduler

```
zilli.adaptive.DynamicSOTAScheduler(monthly_budget_usd, cost_per_call, max_sota_ratio)
```

Thompson Sampling threshold bandit + budget tiers + **hard cap**: `should_call_sota()` returns False when SOTA ratio ≥ `max_sota_ratio` (default 5%).
