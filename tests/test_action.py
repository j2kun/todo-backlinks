import os
from dataclasses import dataclass

from entrypoint import BOT_SIGNATURE, Todo, Update, main


class FakeLocalRepo:
    def __init__(self):
        self.matches = []

    def add_match(self, match: str):
        self.matches.append(match)

    @property
    def git(self):
        class FakeGit:
            def __init__(self):
                pass

            def grep(self2, flag, regex):
                return "\n".join(self.matches)

        return FakeGit()


@dataclass
class FakeComment:
    body: str


@dataclass
class FakeIssue:
    number: int
    title: str
    comments: list[FakeComment]

    def get_comments(self):
        return self.comments


class FakeGitHubRepo:
    def __init__(self):
        os.environ["GITHUB_REPOSITORY"] = "j2kun/todo-backlinks"
        os.environ["GITHUB_BASE_REF"] = "main"
        self.issues: dict[int, FakeIssue] = dict()

    def add_issue(self, issue: FakeIssue):
        self.issues[issue.number] = issue

    def get_issue(self, number):
        return self.issues.get(number)

    def get_issues(self, state):
        return self.issues.values()


def test_issue_with_no_comment():
    gh_repo = FakeGitHubRepo()
    gh_repo.add_issue(
        FakeIssue(
            number=1,
            title="test issue",
            comments=[
                FakeComment("This is my test issue"),
            ],
        )
    )

    local_repo = FakeLocalRepo()
    local_repo.add_match("myfile.py:123: TODO(#1): fix it")

    actual = main(gh_repo, local_repo)
    expected = {
        1: Update(
            todos=[
                Todo(
                    filepath="myfile.py",
                    line="123",
                    issue_number=1,
                    message="fix it",
                )
            ],
            comment=None,
            new_comment_body=(
                "This issue has 1 outstanding TODOs:\n\n"
                " - [myfile.py:123]"
                "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
                ": fix it\n\n" + BOT_SIGNATURE
            ),
        ),
    }

    assert len(expected) == len(actual)
    assert expected[1] == actual[1]


def test_issue_with_no_comment_multiple_todos():
    gh_repo = FakeGitHubRepo()
    gh_repo.add_issue(
        FakeIssue(
            number=1,
            title="test issue",
            comments=[
                FakeComment("This is my test issue"),
            ],
        )
    )

    local_repo = FakeLocalRepo()
    local_repo.add_match("myfile.py:123: TODO(#1): fix it")
    local_repo.add_match("foo/bar.py:5: TODO(#1): just do it")

    actual = main(gh_repo, local_repo)
    expected = {
        1: Update(
            todos=[
                Todo(
                    filepath="myfile.py",
                    line="123",
                    issue_number=1,
                    message="fix it",
                ),
                Todo(
                    filepath="foo/bar.py",
                    line="5",
                    issue_number=1,
                    message="just do it",
                ),
            ],
            comment=None,
            new_comment_body=(
                "This issue has 2 outstanding TODOs:\n\n"
                " - [myfile.py:123]"
                "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
                ": fix it\n" + " - [foo/bar.py:5]"
                "(https://github.com/j2kun/todo-backlinks/blob/main/foo/bar.py#L5)"
                ": just do it\n\n" + BOT_SIGNATURE
            ),
        ),
    }

    assert len(expected) == len(actual)
    assert expected[1] == actual[1]


def test_issue_with_existing_comment_unchanged():
    bot_comment = (
        "This issue has 1 outstanding TODOs:\n\n"
        " - [myfile.py:123]"
        "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
        ": fix it\n\n" + BOT_SIGNATURE
    )
    issue_comment = FakeComment(bot_comment)
    gh_repo = FakeGitHubRepo()
    gh_repo.add_issue(
        FakeIssue(
            number=1,
            title="test issue",
            comments=[
                FakeComment("This is my test issue"),
                issue_comment,
            ],
        )
    )

    local_repo = FakeLocalRepo()
    local_repo.add_match("myfile.py:123: TODO(#1): fix it")

    actual = main(gh_repo, local_repo)
    assert len(actual) == 0


def test_issue_with_existing_comment_changed():
    bot_comment = (
        "This issue has 1 outstanding TODOs:\n\n"
        " - [myfile.py:456]"
        "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
        ": fix it\n\n" + BOT_SIGNATURE
    )
    issue_comment = FakeComment(bot_comment)
    gh_repo = FakeGitHubRepo()
    gh_repo.add_issue(
        FakeIssue(
            number=1,
            title="test issue",
            comments=[
                FakeComment("This is my test issue"),
                issue_comment,
            ],
        )
    )

    local_repo = FakeLocalRepo()
    local_repo.add_match("myfile.py:123: TODO(#1): fix it")

    actual = main(gh_repo, local_repo)
    expected = {
        1: Update(
            todos=[
                Todo(
                    filepath="myfile.py",
                    line="123",
                    issue_number=1,
                    message="fix it",
                )
            ],
            comment=issue_comment,
            new_comment_body=(
                "This issue has 1 outstanding TODOs:\n\n"
                " - [myfile.py:123]"
                "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
                ": fix it\n\n" + BOT_SIGNATURE
            ),
        ),
    }

    assert len(expected) == len(actual)
    assert expected[1] == actual[1]


def test_issue_with_existing_comment_deleted():
    bot_comment = (
        "This issue has 1 outstanding TODOs:\n\n"
        " - [myfile.py:123]"
        "(https://github.com/j2kun/todo-backlinks/blob/main/myfile.py#L123)"
        ": fix it\n\n" + BOT_SIGNATURE
    )
    issue_comment = FakeComment(bot_comment)
    gh_repo = FakeGitHubRepo()
    gh_repo.add_issue(
        FakeIssue(
            number=1,
            title="test issue",
            comments=[
                FakeComment("This is my test issue"),
                issue_comment,
            ],
        )
    )

    local_repo = FakeLocalRepo()
    # no matches

    actual = main(gh_repo, local_repo)
    assert len(actual) == 1
    assert actual[1].delete_comment


def tests_nonexistent_issue():
    gh_repo = FakeGitHubRepo()
    local_repo = FakeLocalRepo()
    local_repo.add_match("myfile.py:123: TODO(#1): fix it")

    actual = main(gh_repo, local_repo)
    assert len(actual) == 0
