from pydantic import ValidationError

from agent.output_schemas import (
    HydeJudgeOutput,
    HydeRewriteOutput,
    StandardizeOutput,
    StructureIngestOutput,
)


class TestStandardizeOutput:
    def test_minimal_fields(self):
        s = StandardizeOutput(need_rewrite=True)
        assert s.need_rewrite is True
        assert s.reason == ""
        assert s.rewritten == ""
        assert s.rewrite_confidence == 1.0

    def test_full_fields(self):
        s = StandardizeOutput(need_rewrite=False, reason="不需要", rewritten="")
        assert s.need_rewrite is False
        assert s.reason == "不需要"

    def test_rewrite_confidence_range(self):
        s = StandardizeOutput(need_rewrite=True, rewritten="测试", rewrite_confidence=0.8)
        assert s.rewrite_confidence == 0.8

    def test_reject_confidence_above_1(self):
        try:
            StandardizeOutput(need_rewrite=True, rewrite_confidence=1.01)
            assert False, "应拒绝>1"
        except ValidationError:
            pass

    def test_reject_confidence_below_0(self):
        try:
            StandardizeOutput(need_rewrite=True, rewrite_confidence=-0.01)
            assert False, "应拒绝<0"
        except ValidationError:
            pass


class TestStructureIngestOutput:
    def test_minimal_fields(self):
        i = StructureIngestOutput(question="Q", answer="A", category_l1="C")
        assert i.category_l2 == ""
        assert i.internal_process == ""
        assert i.feedback_dept == ""
        assert i.category_confidence == 0.5

    def test_full_fields(self):
        i = StructureIngestOutput(
            question="ETC怎么注销",
            answer="拨打客服热线",
            category_l1="账户管理",
            category_l2="注销",
            internal_process="核实身份后注销",
            feedback_dept="客服部",
            category_confidence=0.95,
        )
        assert i.category_confidence == 0.95

    def test_reject_empty_question(self):
        try:
            StructureIngestOutput(question="", answer="A", category_l1="C")
            assert False, "应拒绝空question"
        except ValidationError:
            pass

    def test_reject_empty_answer(self):
        try:
            StructureIngestOutput(question="Q", answer="", category_l1="C")
            assert False, "应拒绝空answer"
        except ValidationError:
            pass

    def test_reject_empty_category_l1(self):
        try:
            StructureIngestOutput(question="Q", answer="A", category_l1="")
            assert False, "应拒绝空category_l1"
        except ValidationError:
            pass

    def test_reject_confidence_above_1(self):
        try:
            StructureIngestOutput(question="Q", answer="A", category_l1="C", category_confidence=1.01)
            assert False, "应拒绝>1"
        except ValidationError:
            pass

    def test_reject_confidence_below_0(self):
        try:
            StructureIngestOutput(question="Q", answer="A", category_l1="C", category_confidence=-0.01)
            assert False, "应拒绝<0"
        except ValidationError:
            pass

    def test_accept_confidence_boundary_0(self):
        i = StructureIngestOutput(question="Q", answer="A", category_l1="C", category_confidence=0.0)
        assert i.category_confidence == 0.0

    def test_accept_confidence_boundary_1(self):
        i = StructureIngestOutput(question="Q", answer="A", category_l1="C", category_confidence=1.0)
        assert i.category_confidence == 1.0


class TestHydeJudgeOutput:
    def test_minimal_fields(self):
        j = HydeJudgeOutput(need_rewrite=True)
        assert j.reason == ""

    def test_full_fields(self):
        j = HydeJudgeOutput(need_rewrite=False, reason="问题已标准")
        assert j.need_rewrite is False
        assert j.reason == "问题已标准"


class TestHydeRewriteOutput:
    def test_default_empty_list(self):
        r = HydeRewriteOutput()
        assert r.questions == []

    def test_with_questions(self):
        r = HydeRewriteOutput(questions=["问法1", "问法2", "问法3"])
        assert len(r.questions) == 3

    def test_default_list_isolated(self):
        r1 = HydeRewriteOutput()
        r2 = HydeRewriteOutput()
        r1.questions.append("test")
        assert r2.questions == []
