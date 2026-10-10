from app.models.domain import PipelineContext


def test_context_is_explicit():
    ctx = PipelineContext(run_id="r", document_id="d", question="q")
    assert ctx.evidence_ref is None
    assert ctx.current_stage == "created"
