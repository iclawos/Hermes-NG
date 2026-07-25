from zilli.data.trajectory_cleaner import TrajectoryCleaner


def _step(tool="write", success=True, error="", content="x"):
    obs = {"success": success}
    if error:
        obs["error"] = error
    return {
        "action": {"tool_name": tool, "content": content},
        "observation": obs,
    }


class TestClean:
    def test_clean_trajectory_unchanged(self):
        c = TrajectoryCleaner()
        traj = [_step("write"), _step("read")]
        steps, warnings = c.clean(traj)
        assert len(steps) == 2

    def test_contaminated_removed(self):
        c = TrajectoryCleaner()
        traj = [_step("write"), _step("read", success=False, error="contaminated data"), _step("bash")]
        steps, warnings = c.clean(traj)
        assert all("contaminated" not in str(s.get("observation", {}).get("error", "")) for s in steps)

    def test_dedup_consecutive_same_tool(self):
        c = TrajectoryCleaner()
        traj = [_step("write", content="a")] * 3 + [_step("read")]
        steps, warnings = c.clean(traj)
        assert len(steps) <= 3


class TestValidate:
    def test_empty_invalid(self):
        c = TrajectoryCleaner()
        result = c.validate([])
        assert result["valid"] is False
        assert result["score"] == 0.0

    def test_short_trajectory_issue(self):
        c = TrajectoryCleaner()
        result = c.validate([_step("write")])
        assert any("too short" in i for i in result["issues"])

    def test_good_trajectory_valid(self):
        c = TrajectoryCleaner()
        traj = [_step(t) for t in ["write", "read", "bash"] * 3]
        result = c.validate(traj)
        assert result["score"] >= 0.3
        assert result["tool_diversity"] == 1.0

    def test_contamination_halves_score(self):
        c = TrajectoryCleaner()
        clean_traj = [_step(t) for t in ["write", "read", "bash"] * 3]
        dirty = [_step(t) for t in ["write", "read", "bash"] * 3]
        dirty[1]["observation"]["error"] = "contaminated payload"
        clean_score = c.validate(clean_traj)["score"]
        dirty_result = c.validate(dirty)
        assert dirty_result["score"] < clean_score
        assert any("contamination" in i for i in dirty_result["issues"])

    def test_high_error_rate_issue(self):
        c = TrajectoryCleaner()
        traj = [_step("write", success=False) for _ in range(8)] + [_step("read"), _step("bash")]
        result = c.validate(traj)
        assert any("error rate" in i for i in result["issues"])

    def test_error_count(self):
        c = TrajectoryCleaner()
        traj = [_step("write", success=False), _step("read")]
        result = c.validate(traj)
        assert result["error_count"] == 1


class TestFindAnomalies:
    def test_empty(self):
        c = TrajectoryCleaner()
        assert c.find_anomalies([]) == []

    def test_uniform_lengths_no_anomaly(self):
        c = TrajectoryCleaner()
        trajs = [[_step()] * 5, [_step()] * 5, [_step()] * 5]
        assert c.find_anomalies(trajs) == []

    def test_outlier_detected(self):
        c = TrajectoryCleaner()
        trajs = [[_step()] * 5 for _ in range(5)] + [[_step()] * 50]
        anomalies = c.find_anomalies(trajs)
        assert 5 in anomalies


class TestBatchClean:
    def test_batch_processes_all(self):
        c = TrajectoryCleaner()
        trajs = [[_step("write"), _step("read")], [_step("bash"), _step("write")]]
        cleaned, warnings = c.batch_clean(trajs)
        assert len(cleaned) == 2
