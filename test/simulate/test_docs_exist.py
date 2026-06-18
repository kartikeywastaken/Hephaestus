# -*- coding: utf-8 -*-
"""
Tests for documentation files existence and minimal content requirements.
"""

from pathlib import Path

def test_docs_exist():
    workspace = Path(__file__).parent.parent.parent
    
    docs_to_check = [
        "README.md",
        "run.md",
        "docs/architecture.md",
        "docs/phases.md",
        "docs/artifact_schema.md",
        "docs/conservative_policy.md",
        "docs/source_reconstruction.md",
        "docs/pipeline_runner.md",
        "docs/stress_testing.md",
        "docs/refactor_notes.md",
        "docs/development_workflow.md",
    ]
    
    for doc in docs_to_check:
        doc_path = workspace / doc
        assert doc_path.is_file(), f"Missing required document: {doc}"

def test_docs_contents():
    workspace = Path(__file__).parent.parent.parent
    
    # README mentions run-all and stress-test
    readme_content = (workspace / "README.md").read_text(encoding="utf-8")
    assert "run-all" in readme_content
    assert "stress-test" in readme_content
    
    # conservative_policy.md contains "Missing evidence is acceptable"
    policy_content = (workspace / "docs/conservative_policy.md").read_text(encoding="utf-8")
    assert "Missing evidence is acceptable" in policy_content
    
    # phases.md mentions Phase 5.8 and Phase 5.9
    phases_content = (workspace / "docs/phases.md").read_text(encoding="utf-8")
    assert "Phase 5.8" in phases_content
    assert "Phase 5.9" in phases_content
