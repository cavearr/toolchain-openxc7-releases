"""The two release lines and their tags.

The main line publishes one release per day under the bare date
(``2026-10-01``): the tag a consumer names, the one that can be promoted
to stable and latest. The upstream nightly builds the HEAD of every
openXC7 repository and publishes under ``upstream-<date>``: a tag that is
not a date, so nothing that resolves a dated release can take it by
mistake. Both lines name their assets by the date alone
(openxc7-toolchain-<platform>-<YYYYMMDD>.tgz), so the date is what a tag
resolves to, whatever its line.

Each line keeps its own newest pre-releases (cleanup-old-prereleases,
with the prefix of the line).
"""

import re

# line -> tag prefix
LINES = {"main": "", "upstream": "upstream-"}

_TAG = re.compile(r"(?P<prefix>[a-z]+-)?(?P<date>\d{4}-\d{2}-\d{2})")


def split_tag(tag: str) -> tuple[str, str]:
    """(line, YYYY-MM-DD) of a release tag; ValueError for any other tag."""
    match = _TAG.fullmatch(tag or "")
    if match:
        prefix = match.group("prefix") or ""
        for line, line_prefix in LINES.items():
            if prefix == line_prefix:
                return line, match.group("date")
    raise ValueError(f"{tag!r} is not a release tag "
                     f"(YYYY-MM-DD, or upstream-YYYY-MM-DD)")


def package_date(tag: str) -> str:
    """The YYYYMMDD the assets of *tag* carry."""
    return split_tag(tag)[1].replace("-", "")
