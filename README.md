# TODO backlinks 

Link from GitHub issue #123 to source lines containing `TODO(#123): msg`.

For example, if `source_file.py` contains this on line 126:

```python
# TODO(#4): remove comments which no longer have TODOs
```

Then issue #4 will get a new comment

```markdown
This issue has 1 outstanding TODOs:

 - [source_file.py:126](https://github.com/j2kun/todo-backlinks/blob/main/entrypoint.py#L126) :  remove comments which no longer have TODOs

This comment was autogenerated by [todo-backlinks](https://github.com/j2kun/todo-backlinks)
```

The comment will be updated in sync with the code changes, including listing
multiple TODOs and deleting the comment when the TODOs are gone. Only works
on files in the repository's main branch.
