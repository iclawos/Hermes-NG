import argparse
import json
import sys
from pathlib import Path

from zilli.evolution import SkillEvolutionEngine
from zilli.evolution.diversity import DiversityController


def _load_trajectories(input_dir: Path) -> list:
    trajectories = []
    for f in sorted(input_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    trajectories.extend(data)
                else:
                    trajectories.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: skipping {f}: {e}", file=sys.stderr)
    return trajectories


def _collect_skill_files(skills_dir: Path) -> list[Path]:
    files = []
    for pattern in ("*.py", "*.md"):
        for f in sorted(skills_dir.glob(pattern)):
            if not f.is_file():
                continue
            name = f.name
            if name == "__init__.py" or name.startswith("_"):
                continue
            files.append(f)
    return files


def _print_summary(summary: dict) -> None:
    d = summary["diversity"]
    print("=== Evolution Summary ===")
    print(f"  Skills processed:    {summary['total_skills']}")
    print(f"  PRs accepted:        {summary['accepted']}")
    print(f"  Rejected (diversity): {summary['rejected']}")
    print(f"  Population size:     {d['population_size']}")
    print(f"  Pairwise sim:        {d['pairwise_similarity']:.3f}")
    print(f"  Unique functions:    {d['unique_functions']}")
    print(f"  Generation:          {d['generation']}")
    print(f"  Total rejected:      {d['rejected_count']}")
    print(f"  Mode:                {summary['config']['mode']}")
    print(f"  Multi-strategy:      {summary['config']['multi_strategy']}")
    print("========================")


def _write_json_report(path: str, summary: dict) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, PermissionError) as e:
        print(f"Error writing report: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Zilli-Evolve: Self-improving skill evolution engine",
    )
    parser.add_argument(
        "--input", type=str, required=True,
        help="Trajectory data directory (JSON files)",
    )
    parser.add_argument(
        "--target-skills", type=str, required=True,
        help="Target skill directory (.py and .md files)",
    )
    parser.add_argument(
        "--reflection-model", type=str, default="claude-opus-4.6",
    )
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument(
        "--multi-strategy", action="store_true",
        help="Run all evolution strategies with diversity gating",
    )
    parser.add_argument(
        "--mode", choices=["evolve", "harness", "auto"], default="evolve",
        help="Evolution strategy selection mode",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="",
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--diversity-threshold", type=float, default=0.5,
        help="Diversity novelty threshold (0.0=accept all, 1.0=must be completely novel)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print generated PR diffs",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print final summary",
    )
    args = parser.parse_args()

    diversity = DiversityController(
        population_size=50,
        novelty_threshold=args.diversity_threshold,
    )
    engine = SkillEvolutionEngine(
        reflection_model=args.reflection_model,
        diversity_controller=diversity,
        mode=args.mode,
    )
    engine.max_iterations = args.max_iterations

    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"Error: input dir not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    skills_dir = Path(args.target_skills)
    if not skills_dir.exists():
        print(f"Error: skills dir not found: {args.target_skills}", file=sys.stderr)
        sys.exit(1)

    trajectory_data = _load_trajectories(input_dir)
    if not args.quiet:
        print(f"Loaded {len(trajectory_data)} trajectory records from {args.input}")

    skill_files = _collect_skill_files(skills_dir)
    if not skill_files:
        print(f"No skill files found in {args.target_skills}", file=sys.stderr)
        sys.exit(1)

    results = []
    total_accepted = 0
    total_rejected = 0

    for skill_file in skill_files:
        if not args.quiet:
            print(f"  Evolving: {skill_file.name} ...", end=" ", flush=True)

        if args.multi_strategy:
            prs = engine.evolve_multi_strategy(
                str(skill_file), trajectory_data=trajectory_data,
            )
            accepted = [p for p in prs if not p.startswith("# Diversity rejected")]
            rejected = [p for p in prs if p.startswith("# Diversity rejected")]
            total_accepted += len(accepted)
            total_rejected += len(rejected)

            if not args.quiet:
                print(f"{len(accepted)} PRs" + (f", {len(rejected)} rejected" if rejected else ""))
            if args.verbose:
                for pr in prs:
                    print(pr)
                    print("---")
        else:
            pr = engine.evolve(str(skill_file), trajectory_data=trajectory_data)
            is_rejected = "# Diversity rejected" in pr
            if is_rejected:
                total_rejected += 1
            else:
                total_accepted += 1

            if not args.quiet:
                print("rejected" if is_rejected else "accepted")
            if args.verbose:
                print(pr)
                print("---")

        results.append({
            "file": skill_file.name,
            "path": str(skill_file),
            "multi": args.multi_strategy,
        })

    metrics = engine.diversity.diversity_metrics()
    summary = {
        "total_skills": len(skill_files),
        "accepted": total_accepted,
        "rejected": total_rejected,
        "diversity": {
            "population_size": metrics["population_size"],
            "pairwise_similarity": metrics["pairwise_similarity"],
            "unique_functions": metrics["unique_functions"],
            "generation": metrics["generation"],
            "rejected_count": metrics["rejected_count"],
        },
        "config": {
            "multi_strategy": args.multi_strategy,
            "mode": args.mode,
            "diversity_threshold": args.diversity_threshold,
            "max_iterations": args.max_iterations,
        },
        "results": results,
    }

    if args.output:
        _write_json_report(args.output, summary)
        if not args.quiet:
            print(f"\nReport written to {args.output}")
    elif not args.quiet:
        print()
        _print_summary(summary)
    elif args.quiet:
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
