from zilli.routing.strategy import StrategySelector, StrategyTier


class TestStrategySelector:
    def setup_method(self):
        self.selector = StrategySelector(
            economy_threshold=0.2,
            enhanced_threshold=0.7,
        )

    def test_economy_low_difficulty(self):
        config = self.selector.select(difficulty=0.1, budget_status=0.5)
        assert config.tier == StrategyTier.ECONOMY

    def test_economy_high_budget(self):
        config = self.selector.select(difficulty=0.5, budget_status=0.9)
        assert config.tier == StrategyTier.ECONOMY

    def test_standard_mid_difficulty(self):
        config = self.selector.select(difficulty=0.5, budget_status=0.5)
        assert config.tier == StrategyTier.STANDARD

    def test_enhanced_high_difficulty(self):
        config = self.selector.select(difficulty=0.8, budget_status=0.3)
        assert config.tier == StrategyTier.ENHANCED

    def test_enhanced_needs_low_budget(self):
        config = self.selector.select(difficulty=0.8, budget_status=0.7)
        assert config.tier != StrategyTier.ENHANCED

    def test_get_config_returns_known(self):
        econ = self.selector.get_config(StrategyTier.ECONOMY)
        assert econ.sota_call_ratio == 0.01

    def test_tiers_list(self):
        tiers = self.selector.tiers
        assert StrategyTier.ECONOMY in tiers
        assert StrategyTier.STANDARD in tiers
        assert StrategyTier.ENHANCED in tiers

    def test_enhanced_sota_ratio(self):
        config = self.selector.get_config(StrategyTier.ENHANCED)
        assert config.sota_call_ratio == 0.2
