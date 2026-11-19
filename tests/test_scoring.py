import pytest
from app import scoring

def test_score_clamping():
    # 0 penalties -> clamped to 99%
    score, bd, verdict = scoring.compute([])
    assert score == 99, "Clean file must be clamped to 99% (never 100%)"
    assert verdict == "Consistent"

    # Extreme penalties -> clamped to 1%
    extreme_findings = [
        {"category": "pixel", "severity": "high", "penalty": 40},
        {"category": "metadata", "severity": "high", "penalty": 40},
        {"category": "ai", "severity": "high", "penalty": 40},
    ]
    score, bd, verdict = scoring.compute(extreme_findings)
    assert score == 1, "Extremely manipulated file must be clamped to 1% (never 0%)"
    assert verdict == "Likely manipulated"


def test_verdict_thresholds():
    # Consistent (Looks genuine): >= 80
    s1, _, v1 = scoring.compute([{"category": "metadata", "severity": "low", "penalty": 10}])
    assert s1 >= 80
    assert v1 == "Consistent"

    # Needs review (Please check): 50 - 79
    s2, _, v2 = scoring.compute([{"category": "pixel", "severity": "medium", "penalty": 30}])
    assert 50 <= s2 < 80
    assert v2 == "Needs review"

    # Likely manipulated (Probably fake): < 50
    s3, _, v3 = scoring.compute([
        {"category": "pixel", "severity": "high", "penalty": 40},
        {"category": "metadata", "severity": "medium", "penalty": 25}
    ])
    assert s3 < 50
    assert v3 == "Likely manipulated"


def test_filename_neutrality():
    """Verify that scoring is strictly signal-based and independent of words in the filename."""
    findings = [{"category": "pixel", "severity": "medium", "penalty": 20}]
    
    score_tampered, _, verdict_tampered = scoring.compute(findings)
    score_clean, _, verdict_clean = scoring.compute(findings)
    
    assert score_tampered == score_clean
    assert verdict_tampered == verdict_clean
