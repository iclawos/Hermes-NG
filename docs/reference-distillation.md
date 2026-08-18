# Reference: Distillation Pipeline API

## DistillationScheduler

Primary class for distillation cycles.

```
zilli.training.distillation.DistillationScheduler
```

### Constructor

```python
DistillationScheduler(
    lambda_bc: float = 1.0,       # behavior cloning weight
    lambda_rl: float = 0.5,       # RL loss weight
    lambda_reg: float = 0.1,      # regularization weight
    kl_beta: float = 0.1,         # KL penalty coefficient
    reward_gamma: float = 0.2,    # reward-shaping coefficient (注意：非 gamma)
    embedding_delta: float = 0.5,
    lora_threshold: int = 1000,
    distill_interval_hours: int = 24,
    full_sft_interval_days: int = 7,
    log_dir: str = "",
    lora_callback: Callable | None = None,
    full_sft_callback: Callable | None = None,
)
```

> 注意：构造参数是 `reward_gamma`，文档旧版本写 `gamma` / `device`，均为错误。
> 设备由 `zilli.infra.device_utils.set_device()` / `get_device()` 全局管理，
> 不通过构造参数传入。

### Key methods

| Method | Returns | Description |
|--------|---------|-------------|
| `add_batch(samples)` | None | Queue samples for next cycle |
| `run_cycle()` | `DistillationCycle \| None` | Execute one distillation step（空缓冲返回 None） |
| `compute_loss_torch(samples)` | `dict[str, float] \| None` | GPU 加速 loss（无 GPU 或 ImportError 时返回 None，不回退 CPU） |
| `save_checkpoint(path="")` | `str` | 序列化缓冲 + 状态，返回写入路径 |
| `load_checkpoint(path)` | `DistillationScheduler` | **类方法**，返回恢复后的新实例（不存在的路径抛 FileNotFoundError） |

> `compute_loss()`（无 torch 后缀）**不存在**；CPU 路径对应 `run_cycle()` 内部实现。

### DistillationCycle

```python
@dataclass
class DistillationCycle:
    cycle_id: int
    start_time: float
    end_time: float | None = None
    samples: int = 0
    bc_loss: float = 0.0
    rl_loss: float = 0.0
    reg_loss: float = 0.0
    total_loss: float = 0.0
    kl_divergence: float = 0.0
    avg_executor_reward: float = 0.0
    avg_planner_reward: float = 0.0
    lora_triggered: bool = False
    metrics: dict = {}
```

> 类型名为 `DistillationCycle`，**不是** `DistillationCycleResult`。

## Distillation DSL

Declarative experiment framework.

```
zilli.distillation.dsl
```

### ExperimentParams

```python
@dataclass
ExperimentParams(
    name: str,
    lambda_bc: float = 1.0,
    lambda_rl: float = 0.5,
    lambda_reg: float = 0.1,
    kl_beta: float = 0.1,
    reward_gamma: float = 0.2,
)
```

> 字段是 `reward_gamma`，不是 `gamma`。

### Single run

```python
run_experiment(
    params: ExperimentParams,
    samples: list[DistillationSample],
    log_dir: str = "",
) -> ExperimentResult
```

### AB test

```python
ABTestGroup(name: str)
    .add(params: ExperimentParams) -> Self

run_ab_test(
    group: ABTestGroup,
    samples: list[DistillationSample],
    log_dir: str = "",
) -> ABIteration

compare(results: list[ExperimentResult]) -> dict
```

> `compare()` 返回 **dict**（含统计摘要），不是 str。

### Multi-round

```python
ExperimentLineage(name: str)
    .add_round(name: str, variants: list[ExperimentParams]) -> Self

run_multi_round(
    lineage: ExperimentLineage,
    samples: list[DistillationSample],
    log_dir: str = "",
) -> ExperimentLineage

lineage_report(lineage: ExperimentLineage) -> str
```

> `add_round` 第二个参数是 `variants`（list），不是 `params` + `auto_baseline`。
> `run_multi_round()` 返回 `ExperimentLineage`（`ExperimentLineageResult` 类型不存在）。
> 最佳配置自动作为下一轮 baseline（`auto_baseline`，默认 True）。
> `lineage_report()` 接收 lineage 实例而非 result。

## Device utilities

```
zilli.infra.device_utils
```

| Function | Returns | Description |
|----------|---------|-------------|
| `detect_device(prefer="auto")` | str | Detect available device |
| `get_device(device=None)` | str | Get cached device (lazy init, 可强制指定) |
| `set_device(device)` | None | Explicitly set global device |
| `is_cuda_available()` | bool | CUDA 可用性 |
| `is_mps_available()` | bool | MPS 可用性 |
| `is_gpu_available()` | bool | GPU 可用性（CUDA 或 MPS） |
| `get_device_count()` | int | 可用设备数 |
| `to_device(tensor, device=None)` | tensor | 将张量搬到目标设备 |

> 注意：无 `validate_device` 公开函数；内部校验为 `_validate_device`。

Device strings: `"cpu"`, `"cuda"`, `"mps"`.

## Benchmark

```
zilli.evaluation.distillation_benchmark
```

```python
tracker = BenchmarkTracker(log_dir: str = "./arena_logs")
tracker.record_before(scheduler, model_name="executor") -> BenchmarkEntry
tracker.record_after(cycle, model_name="executor") -> BenchmarkEntry
tracker.record_ab_result(variant_name, loss, kl, ...) -> None
```

> 无 `.record(name, before, after, metadata)` 方法；实际为
> `record_before` / `record_after` / `record_ab_result` 三方法。

Writes to `arena_logs/benchmark_entries.jsonl` and `arena_logs/distill_benchmarks.jsonl`.

## CLI

```
zilli distill [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--samples` | `100` | Number of samples to generate |
| `--log-dir` | `""` | Output directory |
| `--checkpoint` | None | Checkpoint path (save/load) |
| `--config` | None | YAML config file |
| `--ab-test` | None | AB test config YAML |
| `--device` | `"auto"` | Inference device (cpu/cuda/auto) |

> `--samples` 默认 100（文档旧版写 50）；`--device` 默认 `"auto"`。