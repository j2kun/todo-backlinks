import os


def test_affected_issues():
    affected_issues = set(
        int(x) for x in os.environ.get("AFFECTED_ISSUES", "").split(",")
    )
    assert affected_issues == set([2, 4])
