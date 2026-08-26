from utils.config import get_config


class ThresholdJudge:
    def __init__(self):
        cfg = get_config()["threshold"]
        self.mode = cfg.get("mode", "absolute")

        self.high = cfg.get("high", 0.8)
        self.low = cfg.get("low", 0.5)
        self.min = cfg.get("min", 0.2)

        self.gap_high = cfg.get("gap_high", 0.15)
        self.gap_mid = cfg.get("gap_mid", 0.08)
        self.gap_low = cfg.get("gap_low", 0.03)
        self.floor_high = cfg.get("floor_high", 0.5)
        self.floor_mid = cfg.get("floor_mid", 0.3)
        self.floor_low = cfg.get("floor_low", 0.15)

        disp = get_config()["display"]
        self.high_count = disp["high_confidence"]
        self.mid_count = disp["mid_confidence"]
        self.low_count = disp["low_confidence"]

    def update_config(self):
        cfg = get_config()["threshold"]
        self.mode = cfg.get("mode", "absolute")
        self.high = cfg.get("high", 0.8)
        self.low = cfg.get("low", 0.5)
        self.min = cfg.get("min", 0.2)
        self.gap_high = cfg.get("gap_high", 0.15)
        self.gap_mid = cfg.get("gap_mid", 0.08)
        self.gap_low = cfg.get("gap_low", 0.03)
        self.floor_high = cfg.get("floor_high", 0.5)
        self.floor_mid = cfg.get("floor_mid", 0.3)
        self.floor_low = cfg.get("floor_low", 0.15)
        disp = get_config()["display"]
        self.high_count = disp["high_confidence"]
        self.mid_count = disp["mid_confidence"]
        self.low_count = disp["low_confidence"]

    def judge(self, candidates: list[tuple]) -> tuple[str, int]:
        if not candidates:
            return "none", self.low_count

        if self.mode == "gap":
            return self._judge_gap(candidates)
        return self._judge_absolute(candidates)

    def _judge_absolute(self, candidates: list[tuple]) -> tuple[str, int]:
        top_score = candidates[0][1]
        if top_score >= self.high:
            return "high", self.high_count
        elif top_score >= self.low:
            return "mid", self.mid_count
        elif top_score >= self.min:
            return "low", self.low_count
        else:
            return "none", self.low_count

    def _judge_gap(self, candidates: list[tuple]) -> tuple[str, int]:
        top1_score = candidates[0][1]
        if len(candidates) == 1:
            gap = 1.0
        else:
            gap = top1_score - candidates[1][1]

        if gap >= self.gap_high and top1_score >= self.floor_high:
            return "high", self.high_count
        elif gap >= self.gap_mid and top1_score >= self.floor_mid:
            return "mid", self.mid_count
        elif gap >= self.gap_low and top1_score >= self.floor_low:
            return "low", self.low_count
        else:
            return "none", self.low_count

    def filter_candidates(self, candidates: list[tuple]) -> tuple[str, list[tuple]]:
        if not candidates:
            return "none", []

        confidence, display_count = self.judge(candidates)
        return confidence, candidates[:display_count]
