import unittest
import os


class TestIntegration(unittest.TestCase):
    def test_sometestcase(self):
        affected_issues = [
            int(x) for x in os.environ.get("AFFECTED_ISSUES", "").split(",")
        ]
        assert affected_issues == [2, 4]
