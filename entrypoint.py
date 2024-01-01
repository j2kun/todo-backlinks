#!/usr/bin/env -S python3 -B

import os
import pathlib
from dataclasses import dataclass
from typing import Optional

import git
import github

BOT_SIGNATURE = (
    "This comment was autogenerated by "
    "[todo-backlinks](https://github.com/j2kun/todo-backlinks)"
)
GITHUB_SERVER_URL = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower()[0] == "t"
WARN_SENTINEL = "[!NOTE]"

# Supported regex patterns; these need to be in whatever flavor of regex is
# supported by git grep.

# Issue number assuming issues are in the current repository
ISSUE_NUMBER_RE = r"TODO(#[0-9]\+): \?.\+"


@dataclass
class Todo:
    filepath: str
    line: int
    issue_number: int
    message: str

    def __repr__(self):
        return f"Todo({repr(self.filepath)}, {repr(self.line)}, {repr(self.issue_number)}, {repr(self.message)})"


@dataclass
class Update:
    todos: list[Todo]
    comment: Optional[github.IssueComment.IssueComment]
    new_comment_body: str
    delete_comment: bool = False


def single_todo_comment(todo: Todo) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    blob_base = f"{GITHUB_SERVER_URL}/{repo}/blob/{base_ref}"
    link_url = f"{blob_base}/{todo.filepath}#L{todo.line}"
    return f"[{todo.filepath}:{todo.line}]({link_url}): {todo.message}"


def make_comment(todos: list[Todo], warn_closed: bool = False) -> str:
    prefix = (
        (
            "> [!NOTE]\n"
            + "> Re-commenting because this issue was closed with unresolved TODOs.\n\n"
        )
        if warn_closed
        else ""
    )
    return (
        prefix
        + f"This issue has {len(todos)} outstanding TODOs:\n\n"
        + "\n".join(" - " + single_todo_comment(t) for t in todos)
        + "\n\n"
        + BOT_SIGNATURE
    )


def comment_up_to_date(
    comment: github.IssueComment.IssueComment,
    todos: list[Todo],
) -> bool:
    expected_comment = make_comment(todos, warn_closed=WARN_SENTINEL in comment.body)
    return comment.body == expected_comment


def try_find_comment(issue):
    for comment in issue.get_comments():
        if BOT_SIGNATURE in comment.body:
            return comment
    return None


def populate_todos_from_source(local_repo):
    try:
        results = local_repo.git.grep("-n", ISSUE_NUMBER_RE)
    except git.exc.GitCommandError as e:
        # Status 1 includes the possibility that no matches were found, so we
        # can proceed.
        if e.status not in [0, 1]:
            raise e
        results = ""

    todos: dict[int, list[Todo]] = dict()
    if results:
        for result in results.strip().split("\n"):
            split = result.split(":")
            assert len(split) == 4, split
            filepath, line, todo, message = split
            issue_number = int(todo.split(")")[0].split("(")[1][1:])
            if issue_number not in todos:
                todos[issue_number] = []
            todos[issue_number].append(
                Todo(
                    filepath=filepath,
                    line=line,
                    issue_number=issue_number,
                    message=message.strip(),
                )
            )

    for issue_number in todos:
        todos[issue_number].sort(key=lambda t: t.filepath + ":" + t.line)

    return todos


def get_issue_and_bot_comment(gh_repo, issue_number):
    try:
        issue = gh_repo.get_issue(issue_number)
    except:
        issue = None

    if not issue:
        print(f"Unable to find issue linked by TODO: {issue_number}")
        return None, None

    print(f"Checking #{issue.number}: {issue.title}")
    comment = try_find_comment(issue)
    return issue, comment


def populate_updates_from_todos(gh_repo, todos, affected_issues):
    """Insert Updates into affected_issues using discovered TODOs in the codebase."""
    for issue_number, todo_list in todos.items():
        issue, comment = get_issue_and_bot_comment(gh_repo, issue_number)
        if not issue:
            continue
        if not comment:
            print(f"Found #{issue.number} has no comment referring to this TODO")
            affected_issues[issue_number] = Update(
                todos=todo_list, comment=None, new_comment_body=make_comment(todo_list)
            )
            continue

        if not comment_up_to_date(comment, todo_list):
            print(f"Found #{issue.number} with stale comment {comment.body}")
            affected_issues[issue_number] = Update(
                todos=todo_list,
                comment=comment,
                new_comment_body=make_comment(todo_list),
            )


def populate_updates_from_needed_deletions(gh_repo, todos, affected_issues):
    """Insert Updates into affected_issues for issues that need their comment deleted."""
    for issue in gh_repo.get_issues(state="open"):
        if issue.number in affected_issues or issue.number in todos:
            continue
        for comment in issue.get_comments():
            if BOT_SIGNATURE in comment.body:
                print(f"Found #{issue.number} with comment to delete: {comment.body}")
                affected_issues[issue.number] = Update(
                    todos=[],
                    comment=comment,
                    new_comment_body="",
                    delete_comment=True,
                )


def populate_updates_for_prematurely_closed_issues(gh_repo, todos, affected_issues):
    """Insert Updates into affected_issues for issues that were closed before
    their TODOs were removed."""
    for issue_number, todo_list in todos.items():
        if issue_number in affected_issues:
            continue

        issue, comment = get_issue_and_bot_comment(gh_repo, issue_number)
        if not issue:
            continue
        if comment and issue.state == "closed" and WARN_SENTINEL not in comment.body:
            print(f"Found closed #{issue.number} with one or more outstanding TODOs")
            # We want to delete and re-create the comment to ensure
            # notifications fire. Could consider automatically re-opening the
            # issue, but the most likely scenario is the TODO is stale and it
            # should be deleted without reopening the issue.
            affected_issues[issue_number] = Update(
                todos=todo_list,
                comment=comment,
                new_comment_body=make_comment(todo_list, warn_closed=True),
                delete_comment=True,
            )
            continue


def main(gh_repo, local_repo) -> dict[int, Update]:
    affected_issues: dict[int, Update] = dict()

    todos = populate_todos_from_source(local_repo)
    populate_updates_from_todos(gh_repo, todos, affected_issues)
    populate_updates_from_needed_deletions(gh_repo, todos, affected_issues)
    populate_updates_for_prematurely_closed_issues(gh_repo, todos, affected_issues)

    return affected_issues


if __name__ == "__main__":
    auth = github.Auth.Token(os.environ.get("GITHUB_TOKEN"))
    gh = github.Github(auth=auth)
    gh_repo = gh.get_repo(os.environ.get("GITHUB_REPOSITORY"))

    assert gh_repo, "Could not find github repo, quitting"

    local_repo = git.Repo(pathlib.Path(__file__).parent.resolve())
    assert not local_repo.bare, "Found bare repo, quitting"
    # assert not local_repo.is_dirty(), "Found dirty repo, quitting"

    affected_issues = main(gh_repo, local_repo)

    print("Affected issues: ")
    for issue_number, update in affected_issues.items():
        print(f"updating #{issue_number}")
        if DRY_RUN:
            continue

        if update.delete_comment:
            update.comment.delete()
            if update.new_comment_body:
                issue = gh_repo.get_issue(issue_number)
                issue.create_comment(update.new_comment_body)
        elif update.comment and update.new_comment_body:
            update.comment.edit(update.new_comment_body)
        elif update.new_comment_body:
            issue = gh_repo.get_issue(issue_number)
            issue.create_comment(update.new_comment_body)
        else:
            print(f"Found #{issue_number} with a non-actionable update: {update}")

    gh.close()

    issue_list = ",".join([str(x) for x in affected_issues.keys()])
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            print(
                "{0}={1}".format("affected-issues", issue_list),
                file=f,
            )
