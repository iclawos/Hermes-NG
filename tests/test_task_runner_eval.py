from zilli.tasks import TaskRunner


def _action(tool="write"):
    return {"tool_name": tool, "args": {}}


class TestTaskRunnerEvaluate:
    def test_no_criteria_zero(self):
        runner = TaskRunner({"id": "t", "eval_criteria": []})
        assert runner.evaluate({}) == 0.0

    def test_task_completed_criterion(self):
        runner = TaskRunner({"id": "t", "eval_criteria": [{"type": "task_completed"}]})
        assert runner.evaluate({"task_completed": True}) == 1.0
        assert runner.evaluate({"task_completed": False}) == 0.0

    def test_multiple_criteria_partial(self):
        runner = TaskRunner({"id": "t", "eval_criteria": [
            {"type": "task_completed"},
            {"type": "memory_recall"},
        ]})
        assert runner.evaluate({"task_completed": True, "memory_recalled": False}) == 0.5

    def test_all_criteria_types(self):
        criteria = [
            {"type": "task_completed"}, {"type": "memory_recall"},
            {"type": "skill_created"}, {"type": "error_detected_in_round_1"},
            {"type": "corrected_in_round_2"}, {"type": "auto_truncate_on_loop"},
            {"type": "reflection_generated"},
        ]
        runner = TaskRunner({"id": "t", "eval_criteria": criteria})
        full = {
            "task_completed": True, "memory_recalled": True,
            "skill_created": True, "error_detected": True,
            "corrected": True, "truncated": True, "reflection_done": True,
        }
        assert runner.evaluate(full) == 1.0

    def test_test_passed_with_min_rate(self):
        runner = TaskRunner({"id": "t", "eval_criteria": [
            {"type": "test_passed", "min_pass_rate": 80},
        ]})
        assert runner.evaluate({"tests_passed": 90}) == 1.0
        assert runner.evaluate({"tests_passed": 50}) == 0.0

    def test_fallback_criteria_key(self):
        runner = TaskRunner({"id": "t", "eval_criteria": [{"type": "custom_thing"}]})
        assert runner.evaluate({"custom_thing_ok": True}) == 1.0


class TestTrajectoryTemplate:
    def test_no_template_perfect(self):
        runner = TaskRunner({"id": "t"})
        assert runner.evaluate_trajectory_template() == 1.0

    def test_full_match(self):
        runner = TaskRunner({"id": "t", "trajectory_template": [
            {"tool": "write", "reward_weight": 1.0},
            {"tool": "read", "reward_weight": 1.0},
        ]})
        runner.record_action(_action("write"), {})
        runner.record_action(_action("read"), {})
        assert runner.evaluate_trajectory_template() == 1.0

    def test_weighted_partial(self):
        runner = TaskRunner({"id": "t", "trajectory_template": [
            {"tool": "write", "reward_weight": 3.0},
            {"tool": "read", "reward_weight": 1.0},
        ]})
        runner.record_action(_action("write"), {})
        runner.record_action(_action("bash"), {})
        assert runner.evaluate_trajectory_template() == 0.75

    def test_missing_steps_score_zero(self):
        runner = TaskRunner({"id": "t", "trajectory_template": [
            {"tool": "write", "reward_weight": 1.0},
        ]})
        assert runner.evaluate_trajectory_template() == 0.0


class TestRewardRules:
    def test_no_rules_zero(self):
        runner = TaskRunner({"id": "t"})
        assert runner.evaluate_reward_rules({}) == 0.0

    def test_task_completion(self):
        runner = TaskRunner({"id": "t", "reward_rules": [
            {"type": "task_completion", "weight": 2.0},
        ]})
        assert runner.evaluate_reward_rules({"task_completed": True}) == 2.0

    def test_format_ratio(self):
        runner = TaskRunner({"id": "t", "reward_rules": [
            {"type": "format", "weight": 1.0},
        ]})
        runner.record_action(_action("write"), {})
        runner.record_action({"no_tool": True}, {})
        assert runner.evaluate_reward_rules({}) == 0.5

    def test_safety(self):
        runner = TaskRunner({"id": "t", "reward_rules": [
            {"type": "safety", "weight": 1.0},
        ]})
        assert runner.evaluate_reward_rules({"forbidden_action_executed": False}) == 1.0
        assert runner.evaluate_reward_rules({"forbidden_action_executed": True}) == 0.0

    def test_efficiency(self):
        runner = TaskRunner({"id": "t", "max_steps": 10, "reward_rules": [
            {"type": "efficiency", "weight": 1.0},
        ]})
        for _ in range(5):
            runner.record_action(_action("write"), {})
            runner.record_action(_action("read"), {})
        assert runner.step_count == 10
        assert runner.evaluate_reward_rules({}) == 0.0

    def test_tool_accuracy_penalty(self):
        runner = TaskRunner({"id": "t", "reward_rules": [
            {"type": "tool_accuracy", "weight": 1.0},
        ]})
        runner.record_action(_action("write"), {"success": False})
        runner.record_action(_action("read"), {"success": False})
        assert runner.evaluate_reward_rules({}) == -1.0

    def test_truncate_on_repeated_tool(self):
        runner = TaskRunner({"id": "t", "max_steps": 20})
        for _ in range(5):
            runner.record_action(_action("write"), {})
        assert runner.should_truncate() is True

    def test_truncate_at_max_steps(self):
        runner = TaskRunner({"id": "t", "max_steps": 2})
        runner.record_action(_action("a"), {})
        runner.record_action(_action("b"), {})
        assert runner.should_truncate() is True
