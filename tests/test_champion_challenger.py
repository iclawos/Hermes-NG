"""ChampionChallenger 竞技场覆盖补测。

覆盖 run_match/_evaluate_match/_should_deploy/_promote/rollback 的
边界与失败分支。
"""

import time

import pytest

from zilli.training.champion_challenger import (
    ArenaStatus,
    ChampionChallenger,
)


def _make_arena(**kw):
    return ChampionChallenger(**{**{"log_dir": ""}, **kw})


class TestRunMatchEdges:
    def test_run_match_no_champion(self):
        arena = _make_arena()
        assert arena.run_match("x", lambda n: [1.0]) is None

    def test_run_match_unregistered_challenger(self):
        arena = _make_arena()
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        assert arena.run_match("ghost", lambda n: [1.0]) is None

    def test_run_match_empty_scores(self):
        arena = _make_arena()
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("challenger", "v2", ArenaStatus.CHALLENGER)
        match = arena.run_match("challenger", lambda n: [])
        assert match is not None
        assert match.num_tasks == 0
        assert match.champion_score == 0.0

    def test_run_match_declares_champion_winner(self):
        # 挑战者明显更差 → 冠军获胜
        arena = _make_arena(min_win_gap=0.01, significance_level=0.5)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("challenger", "v2", ArenaStatus.CHALLENGER)
        match = arena.run_match(
            "challenger",
            lambda n: [0.5] * 12 if n == "champ" else [0.05] * 12,
        )
        assert match.winner == "champ"
        assert match.num_tasks == 12


class TestBootstrapAndStd:
    def test_bootstrap_empty_returns_one(self):
        arena = _make_arena()
        assert arena._bootstrap_p([], [1.0]) == 1.0

    def test_std_single_value_is_zero(self):
        arena = _make_arena()
        assert arena._std([0.5], 0.5) == 0.0

    def test_std_variance(self):
        arena = _make_arena()
        assert arena._std([1.0, 3.0, 5.0], 3.0) == pytest.approx(2.0)


class TestShouldDeploy:
    def test_not_significant(self):
        arena = _make_arena()
        from zilli.training.champion_challenger import ArenaMatch

        m = ArenaMatch("m1", time.time(), "c", "x", 1.0, 1.0, significant=False,
                       winner="x")
        assert arena._should_deploy(m) is False

    def test_winner_not_challenger(self):
        arena = _make_arena()
        from zilli.training.champion_challenger import ArenaMatch

        m = ArenaMatch("m1", time.time(), "c", "x", 1.0, 1.0, significant=True,
                       winner="c")
        assert arena._should_deploy(m) is False

    def test_below_warmup_rounds(self):
        arena = _make_arena(warmup_rounds=3)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("x", "v2")
        from zilli.training.champion_challenger import ArenaMatch

        # 只有 1 场匹配记录，不足 3 轮
        m = ArenaMatch("m1", time.time(), "champ", "x", 0.5, 0.9,
                       significant=True, winner="x")
        arena._matches.append(m)
        assert arena._should_deploy(m) is False

    def test_low_recent_win_rate(self):
        arena = _make_arena(warmup_rounds=1)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("x", "v2")
        from zilli.training.champion_challenger import ArenaMatch

        for i in range(3):
            arena._matches.append(ArenaMatch(
                f"m{i}", time.time(), "champ", "x", 0.5, 0.9,
                significant=True, winner="x" if i == 0 else "champ"))
        m = ArenaMatch("m3", time.time(), "champ", "x", 0.5, 0.9,
                       significant=True, winner="x")
        arena._matches.append(m)
        assert arena._should_deploy(m) is False

    def test_deploy_condition_met(self):
        arena = _make_arena(warmup_rounds=1)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("x", "v2")
        from zilli.training.champion_challenger import ArenaMatch

        for i in range(3):
            arena._matches.append(ArenaMatch(
                f"m{i}", time.time(), "champ", "x", 0.5, 0.9,
                significant=True, winner="x"))
        m = ArenaMatch("m3", time.time(), "champ", "x", 0.5, 0.9,
                       significant=True, winner="x")
        arena._matches.append(m)
        assert arena._should_deploy(m) is True


class TestPromoteAndRollback:
    def test_promote_with_failing_callback(self):
        def bad(name):
            raise RuntimeError("deploy failed")

        arena = _make_arena(deploy_callback=bad)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("x", "v2")
        arena._champion = "champ"
        from zilli.training.champion_challenger import ArenaMatch

        m = ArenaMatch("m1", time.time(), "champ", "x", 0.5, 0.9,
                       significant=True, winner="x")
        arena._matches.append(m)
        arena._should_deploy = lambda m: True  # 直接放行部署
        arena._promote_challenger("x")
        assert arena.get_champion() == "champ"  # 回调失败 → 中止提升

    def test_promote_missing_model(self):
        arena = _make_arena()
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena._promote_challenger("ghost")
        assert arena.get_champion() == "champ"

    def test_promote_success(self):
        arena = _make_arena(deploy_callback=lambda n: None)
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        arena.register_model("x", "v2")
        arena._promote_challenger("x")
        assert arena.get_champion() == "x"
        assert arena._models["champ"].status == ArenaStatus.RETIRED
        assert arena.stats()["deployments"] == 1

    def test_rollback_no_matches(self):
        arena = _make_arena()
        assert arena.rollback() is None

    def test_rollback_no_retired(self):
        arena = _make_arena()
        arena.register_model("champ", "v1", ArenaStatus.CHAMPION)
        assert arena.rollback() is None

    def test_rollback_success(self):
        arena = _make_arena(rollback_callback=lambda n: None)
        arena.register_model("v1", "1.0", ArenaStatus.CHAMPION)
        arena.register_model("v2", "2.0")
        # v1 先退役，v2 上位
        arena._models["v1"].status = ArenaStatus.RETIRED
        arena._models["v1"].retired_at = time.time() - 10
        arena._champion = "v2"
        arena._matches.append(1)  # 任意记录确保非空
        assert arena.rollback() == "v1"
        assert arena.get_champion() == "v1"
        assert arena.stats()["rollbacks"] == 1

    def test_rollback_callback_failure_swallowed(self):
        def bad(name):
            raise RuntimeError("rollback failed")

        arena = _make_arena(rollback_callback=bad)
        arena.register_model("v1", "1.0", ArenaStatus.CHAMPION)
        arena.register_model("v2", "2.0")
        arena._models["v1"].status = ArenaStatus.RETIRED
        arena._models["v1"].retired_at = time.time() - 10
        arena._champion = "v2"
        arena._matches.append(1)
        assert arena.rollback() == "v1"


class TestLeaderboard:
    def test_leaderboard_empty(self):
        arena = _make_arena()
        assert arena.leaderboard() == []

    def test_leaderboard_sorted(self):
        arena = _make_arena()
        arena.register_model("a", "1", ArenaStatus.CHAMPION)
        arena.register_model("b", "2")
        arena.add_score("a", 0.3)
        arena.add_score("b", 0.9)
        lb = arena.leaderboard()
        assert lb[0]["name"] == "b"
        assert lb[0]["win_rate"] == 0.0

    def test_stats_fields(self):
        arena = _make_arena()
        arena.register_model("a", "1", ArenaStatus.CHAMPION)
        s = arena.stats()
        assert s["current_champion"] == "a"
        assert s["min_win_gap"] == 0.05
