import asyncio
from pathlib import Path

from zilli.evolution.diversity import DiversityController
from zilli.evolution.skill_evolution import SkillEvolutionEngine
from zilli.routing.feedback import FeedbackCollector
from zilli.routing.mom_router import MOMRouter
from zilli.routing.ppm import PPMPredictor
from zilli.routing.profile import ModelProfile
from zilli.routing.strategy import StrategySelector

SKILLS_DIR = Path(__file__).parent.parent / "examples" / "skills"


def _make_router() -> MOMRouter:
    return MOMRouter(
        ppm=PPMPredictor(),
        profile=ModelProfile(exploration_factor=0.0),
        strategy=StrategySelector(),
        feedback=FeedbackCollector(batch_size=10000),
    )


class TestHarnessRealSkillLibrary:
    def test_harness_evolve_real_skill(self):
        engine = SkillEvolutionEngine(
            mode="harness",
            mom_router=_make_router(),
            diversity_controller=DiversityController(),
        )
        skill = str(SKILLS_DIR / "text_summarizer.py")
        trajectories = [
            {"error": "IndexError: list index out of range", "reward": 0.2},
        ]
        pr = engine.evolve(skill, trajectories)
        assert isinstance(pr, str)
        assert len(pr) > 0

    def test_harness_evolve_multiple_skills(self):
        engine = SkillEvolutionEngine(
            mode="harness",
            mom_router=_make_router(),
            diversity_controller=DiversityController(),
        )
        for skill_file in ["text_summarizer.py", "data_validator.py"]:
            pr = engine.evolve(str(SKILLS_DIR / skill_file), [])
            assert isinstance(pr, str)

    def test_harness_feedback_recorded(self):
        router = _make_router()
        engine = SkillEvolutionEngine(
            mode="harness",
            mom_router=router,
            diversity_controller=DiversityController(),
        )
        engine.evolve(str(SKILLS_DIR / "data_validator.py"), [])
        stats = router.stats()
        assert stats["profile"] is not None

    def test_evolve_mode_on_real_library(self):
        engine = SkillEvolutionEngine(
            mode="evolve",
            diversity_controller=DiversityController(),
        )
        pr = engine.evolve(str(SKILLS_DIR / "text_summarizer.py"), [
            {"error": "ValueError: empty input", "reward": 0.1},
            {"error": "TypeError: unsupported type", "reward": 0.3},
        ])
        assert isinstance(pr, str)

    def test_concurrent_evolve_real_library(self):
        engine = SkillEvolutionEngine(
            mode="evolve",
            diversity_controller=DiversityController(),
        )
        skills = [str(SKILLS_DIR / "text_summarizer.py"),
                  str(SKILLS_DIR / "data_validator.py")]
        results = asyncio.run(engine.evolve_concurrent(skills, []))
        assert len(results) == 2
