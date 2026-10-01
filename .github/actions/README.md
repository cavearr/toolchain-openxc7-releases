# Release actions (local copies)

The four composite actions in this directory are copies of the
ones in [`fpgawars/apio-workflows`](https://github.com/fpgawars/apio-workflows)
(`.github/actions/<name>/action.yaml`), taken at commit
`803d7c73a7302823ec8106a237b7b7fe641ecbbe` (2026-09-30), verbatim but for the
one change described below:

| Action | Used by | What it does |
|---|---|---|
| `get-release-and-package-tags` | `build-pre-release`, `build-upstream-nightly` (`prepare`) | Today's UTC date as `YYYY-MM-DD` and `YYYYMMDD` |
| `ensure-no-conflicting-release` | `build-pre-release`, `build-upstream-nightly` (`prepare`, `pre-release`) | Fails on a same-tag stable release; deletes a same-tag pre-release unless `just-check` |
| `cleanup-old-prereleases` | `build-pre-release`, `build-upstream-nightly` (`pre-release`) | Keeps the newest 5 pre-releases of ONE release line (a constant of the action), deletes the rest with their tags. **Local change**: the `tag-prefix` input |
| `create-pre-release` | `build-pre-release`, `build-upstream-nightly` (`pre-release`) | Creates the dated pre-release (never latest) with the given body and assets |

**One local change**: `cleanup-old-prereleases` takes a `tag-prefix` input
and counts and deletes only the pre-releases whose tag is
`<tag-prefix>YYYY-MM-DD`. This repository publishes two release lines, the
dated tags and the upstream nightly (`upstream-YYYY-MM-DD`): the original
counts every pre-release together, so five upstream nightlies would delete
the dated pre-releases and the other way round. The default (`""`) is the
dated line; `tests/test_cleanup_prereleases.py` runs the step against a
fake `gh`. A refresh of this action has to carry the change over.

They are copied, not referenced, so that no workflow of this repository
depends on another repository's `main`: the release pipeline builds the
same way whatever happens elsewhere. None of them assumes anything about
the repository that runs it (no organisation name, no asset prefix). A local action is a file of the checked-out
tree: every job that runs one checks the repository out first, and
`scripts/check-workflows.py` enforces that, and the inputs each step passes.

To refresh them, fetch each file again at a newer commit and update the sha
above:

```
gh api repos/fpgawars/apio-workflows/contents/.github/actions/<name>/action.yaml?ref=<sha> \
  --jq .content | base64 -d > .github/actions/<name>/action.yaml
```

License: `fpgawars/apio-workflows` is GPL-3.0, the same license as this
repository (`LICENSE` at the root).
