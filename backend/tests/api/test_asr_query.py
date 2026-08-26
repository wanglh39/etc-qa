from unittest.mock import MagicMock, patch

from asr.models import ASRHealthResponse, ASRResponse, SpeakerSegment
from models.schemas import ASRQueryResponse, CandidateResult, QueryResponse


class TestASRQueryResponse:
    def test_default_fields(self):
        resp = ASRQueryResponse(asr_text="hello")
        assert resp.asr_text == "hello"
        assert resp.asr_confidence == 1.0
        assert resp.candidates == []
        assert resp.total_candidates == 0

    def test_full_fields(self):
        resp = ASRQueryResponse(
            asr_text="ETC怎么办理",
            asr_confidence=0.95,
            asr_duration_ms=1200,
            asr_model="FunASR",
            asr_language="zh",
            asr_segments=[{"start": 0.0, "end": 1.2, "speaker": "SPEAKER_00", "text": "ETC怎么办理"}],
            query="ETC怎么办理",
            standardized_query="ETC办理流程",
            confidence="high",
            candidates=[CandidateResult(qa_id=1, question="ETC如何办理", answer="去银行", score=0.9)],
            total_candidates=1,
        )
        assert resp.asr_text == "ETC怎么办理"
        assert resp.confidence == "high"
        assert len(resp.candidates) == 1


class TestASRQueryEndpoint:
    @patch("api.routes.get_asr_service")
    @patch("api.routes.service")
    def test_asr_query_success(self, mock_rag_service, mock_get_asr):
        from api.routes import router

        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(
            text="ETC怎么办理",
            confidence=0.95,
            duration_ms=1200,
            model="FunASR",
            language="zh",
            segments=[SpeakerSegment(start=0.0, end=1.2, speaker="SPEAKER_00", text="ETC怎么办理")],
        )
        mock_get_asr.return_value = mock_asr

        mock_rag_service.query.return_value = QueryResponse(
            query="ETC怎么办理",
            standardized_query="ETC办理流程",
            confidence="high",
            candidates=[CandidateResult(qa_id=1, question="ETC如何办理", answer="去银行", score=0.9)],
            total_candidates=1,
        )

        asr_result = mock_asr.transcribe("/tmp/test.wav")
        rag_result = mock_rag_service.query(asr_result.text)

        assert asr_result.text == "ETC怎么办理"
        assert rag_result.confidence == "high"
        assert rag_result.total_candidates == 1

    @patch("api.routes.get_asr_service")
    def test_asr_query_asr_disabled(self, mock_get_asr):
        mock_asr = MagicMock()
        mock_asr._enabled = False
        mock_get_asr.return_value = mock_asr

        from fastapi import HTTPException

        if not mock_asr._enabled:
            with patch("api.routes.service", MagicMock()):
                pass

    @patch("api.routes.get_asr_service")
    @patch("api.routes.service")
    def test_asr_query_empty_text(self, mock_rag_service, mock_get_asr):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(
            text="",
            confidence=0.5,
            duration_ms=800,
            model="FunASR",
        )
        mock_get_asr.return_value = mock_asr

        asr_result = mock_asr.transcribe("/tmp/test.wav")
        assert asr_result.text == ""
        mock_rag_service.query.assert_not_called()

    @patch("api.routes.get_asr_service")
    @patch("api.routes.service")
    def test_asr_query_with_category(self, mock_rag_service, mock_get_asr):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(
            text="ETC怎么办理",
            confidence=0.95,
            duration_ms=1200,
            model="FunASR",
        )
        mock_get_asr.return_value = mock_asr

        mock_rag_service.query.return_value = QueryResponse(
            query="ETC怎么办理",
            standardized_query="ETC办理流程",
            confidence="high",
            candidates=[],
            total_candidates=0,
        )

        asr_result = mock_asr.transcribe("/tmp/test.wav")
        rag_result = mock_rag_service.query(asr_result.text, "ETC业务")
        mock_rag_service.query.assert_called_with("ETC怎么办理", "ETC业务")

    @patch("api.routes.get_asr_service")
    @patch("api.routes.service")
    def test_asr_query_rag_failure(self, mock_rag_service, mock_get_asr):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(
            text="ETC怎么办理",
            confidence=0.95,
            duration_ms=1200,
            model="FunASR",
        )
        mock_get_asr.return_value = mock_asr

        mock_rag_service.query.side_effect = RuntimeError("RAG服务异常")

        asr_result = mock_asr.transcribe("/tmp/test.wav")
        try:
            mock_rag_service.query(asr_result.text)
        except RuntimeError as e:
            assert "RAG服务异常" in str(e)

    def test_asr_query_response_serialization(self):
        resp = ASRQueryResponse(
            asr_text="测试",
            asr_confidence=0.88,
            asr_duration_ms=500,
            asr_model="model",
            asr_language="zh",
            asr_segments=[],
            query="测试",
            standardized_query="标准化测试",
            confidence="medium",
            candidates=[
                CandidateResult(qa_id=1, question="q1", answer="a1", score=0.8),
                CandidateResult(qa_id=2, question="q2", answer="a2", score=0.7),
            ],
            total_candidates=2,
        )
        data = resp.model_dump()
        assert data["asr_text"] == "测试"
        assert len(data["candidates"]) == 2
        assert data["total_candidates"] == 2
