from pydantic import ValidationError

from asr.models import ASRHealthResponse, ASRResponse


class TestASRResponse:
    def test_minimal(self):
        r = ASRResponse(text="ETC扣费异常")
        assert r.text == "ETC扣费异常"
        assert r.confidence == 1.0
        assert r.duration_ms == 0
        assert r.model == ""
        assert r.language is None

    def test_full(self):
        r = ASRResponse(
            text="ETC扣费异常怎么处理",
            confidence=0.95,
            duration_ms=3200,
            model="FunAudioLLM/Fun-ASR-Nano-2512",
            language="zh",
        )
        assert r.confidence == 0.95
        assert r.duration_ms == 3200

    def test_reject_confidence_above_1(self):
        try:
            ASRResponse(text="test", confidence=1.01)
            assert False
        except ValidationError:
            pass

    def test_reject_confidence_below_0(self):
        try:
            ASRResponse(text="test", confidence=-0.01)
            assert False
        except ValidationError:
            pass

    def test_reject_negative_duration(self):
        try:
            ASRResponse(text="test", duration_ms=-1)
            assert False
        except ValidationError:
            pass


class TestASRHealthResponse:
    def test_not_loaded(self):
        h = ASRHealthResponse(loaded=False)
        assert h.loaded is False
        assert h.model == ""
        assert h.device == ""
        assert h.finetuned is False

    def test_loaded(self):
        h = ASRHealthResponse(
            loaded=True,
            model="FunAudioLLM/Fun-ASR-Nano-2512",
            device="cuda",
            finetuned=False,
        )
        assert h.loaded is True
        assert h.device == "cuda"
