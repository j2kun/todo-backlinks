#!/usr/bin/env -S python3 -B

# NOTE: If you are using an alpine docker image
# such as pyaction-lite, the -S option above won't
# work. The above line works fine on other linux distributions
# such as debian, etc, so the above line will work fine
# if you use pyaction:4.0.0 or higher as your base docker image.

import os
import pathlib

import git
import github

# Supported regex patterns

# TODO(#2): Support more regex patterns

# Issue number assuming current repository
ISSUE_NUMBER_RE = r'TODO[(]\#([0-9]+)[)]: ?(.+)'


def main(gh_repo, local_repo):
    affected_issues = []

    try:
        result = local_repo.git.grep(ISSUE_NUMBER_RE)
        print(result)
    except git.exc.GitCommandError as e:
        # Status 1 includes the possibility that no matches were found, so we
        # can proceed.
        if e.status not in [0, 1]:
            raise e



    # issues = gh_repo.get_issues()
    # if issues:
    #     for issue in issues:
    #         print('-'*25)
    #         print(f'#{issue.number}: {issue.title}')
    #         print(f'{issue.body}')
    #         for comment in issue.get_comments():
    #             print(comment)

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

    gh.close()

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            print("{0}={1}".format("affected-issues",
                  ','.join(affected_issues)), file=f)
