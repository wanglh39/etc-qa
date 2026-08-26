from unittest.mock import patch

from rag.threshold import ThresholdJudge


def _make_config(mode="absolute"):
    return {
        "threshold": {
            "mode": mode,
            "high": 0.8,
            "low": 0.5,
            "min": 0.2,
            "gap_high": 0.15,
            "gap_mid": 0.08,
            "gap_low": 0.03,
            "floor_high": 0.5,
            "floor_mid": 0.3,
            "floor_low": 0.15,
        },
        "display": {"high_confidence": 3, "mid_confidence": 5, "low_confidence": 10},
    }


class TestAbsoluteMode:
    def setup_method(self):
        self._patcher = patch("rag.threshold.get_config")
        mock_cfg = self._patcher.start()
        mock_cfg.return_value = _make_config("absolute")
        self.judge = ThresholdJudge()

    def teardown_method(self):
        self._patcher.stop()

    def test_high_confidence(self):
        confidence, count = self.judge.judge([(1, 0.9), (2, 0.8)])
        assert confidence == "high"
        assert count == 3

    def test_mid_confidence(self):
        confidence, count = self.judge.judge([(1, 0.6), (2, 0.5)])
        assert confidence == "mid"
        assert count == 5

    def test_low_confidence(self):
        confidence, count = self.judge.judge([(1, 0.3), (2, 0.2)])
        assert confidence == "low"
        assert count == 10

    def test_none_confidence(self):
        confidence, count = self.judge.judge([(1, 0.1), (2, 0.05)])
        assert confidence == "none"
        assert count == 10

    def test_boundary_high(self):
        confidence, _ = self.judge.judge([(1, 0.8), (2, 0.7)])
        assert confidence == "high"

    def test_boundary_low(self):
        confidence, _ = self.judge.judge([(1, 0.5), (2, 0.4)])
        assert confidence == "mid"

    def test_boundary_min(self):
        confidence, _ = self.judge.judge([(1, 0.2), (2, 0.1)])
        assert confidence == "low"

    def test_filter_empty_candidates(self):
        confidence, filtered = self.judge.filter_candidates([])
        assert confidence == "none"
        assert filtered == []

    def test_filter_high_confidence_truncates(self):
        candidates = [(i, 0.9) for i in range(10)]
        confidence, filtered = self.judge.filter_candidates(candidates)
        assert confidence == "high"
        assert len(filtered) == 3

    def test_filter_none_returns_candidates(self):
        candidates = [(1, 0.1)]
        confidence, filtered = self.judge.filter_candidates(candidates)
        assert confidence == "none"
        assert len(filtered) == 1


class TestGapMode:
    def setup_method(self):
        self._patcher = patch("rag.threshold.get_config")
        mock_cfg = self._patcher.start()
        mock_cfg.return_value = _make_config("gap")
        self.judge = ThresholdJudge()

    def teardown_method(self):
        self._patcher.stop()

    def test_high_gap_and_high_floor(self):
        confidence, count = self.judge.judge([(1, 0.9), (2, 0.6)])
        assert confidence == "high"
        assert count == 3

    def test_mid_gap(self):
        confidence, count = self.judge.judge([(1, 0.6), (2, 0.5)])
        assert confidence == "mid"
        assert count == 5

    def test_low_gap(self):
        confidence, count = self.judge.judge([(1, 0.4), (2, 0.36)])
        assert confidence == "low"
        assert count == 10

    def test_none_small_gap(self):
        confidence, count = self.judge.judge([(1, 0.5), (2, 0.49)])
        assert confidence == "none"
        assert count == 10

    def test_single_candidate_high(self):
        confidence, count = self.judge.judge([(1, 0.9)])
        assert confidence == "high"
        assert count == 3

    def test_single_candidate_low_floor(self):
        confidence, count = self.judge.judge([(1, 0.1)])
        assert confidence == "none"
        assert count == 10

    def test_large_gap_but_low_floor(self):
        confidence, count = self.judge.judge([(1, 0.2), (2, 0.0)])
        assert confidence == "low"
        assert count == 10

    def test_filter_empty(self):
        confidence, filtered = self.judge.filter_candidates([])
        assert confidence == "none"
        assert filtered == []

    def test_filter_high_truncates(self):
        candidates = [(0, 0.9), (1, 0.6)] + [(i, 0.3) for i in range(2, 12)]
        confidence, filtered = self.judge.filter_candidates(candidates)
        assert confidence == "high"
        assert len(filtered) == 3
