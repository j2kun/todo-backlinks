import os


def test_affected_issues():
    affected_issues = set(
        int(x) for x in os.environ.get("AFFECTED_ISSUES", "").split(",")
    )
    # TODO(#2): update a stale comment
    # Issue #4 is in the impacted list because it has a comment that should be deleted.
    # TODO(#5): Ping a closed issue
    # TODO(#8): Don't update a proper comment
    assert affected_issues == set([2, 4, 5, 8])
