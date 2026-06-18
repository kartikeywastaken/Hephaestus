# -*- coding: utf-8 -*-
"""
Pipeline refactor regression tests.
"""

from src.pipeline.stage_defs import PIPELINE_STAGES, STAGE_OUTPUTS
from src.pipeline.checks import strip_c_comments

def test_stage_defs():
    # Verify order of pipeline stages
    assert PIPELINE_STAGES == [
        "extract",
        "analyze_cfg",
        "recover_semantics",
        "refine_semantics",
        "recover_layouts",
        "finalize_semantics",
        "reconstruct_source",
    ]
    
    # Verify stage outputs mappings exist
    for stage in PIPELINE_STAGES:
        assert stage in STAGE_OUTPUTS
        assert isinstance(STAGE_OUTPUTS[stage], list)
        assert len(STAGE_OUTPUTS[stage]) > 0

def test_manifest_schema():
    from src.pipeline.manifest import start_manifest
    m = start_manifest("./t", "artifacts")
    assert m["schema_version"] == "pipeline-1.0"

def test_comment_stripping():
    code_with_comments = """
    int main() {
        // inline comment
        /* block comment
           on multiple lines */
        return 0;
    }
    """
    clean_code = strip_c_comments(code_with_comments)
    assert "// inline comment" not in clean_code
    assert "block comment" not in clean_code
    assert "return 0;" in clean_code
