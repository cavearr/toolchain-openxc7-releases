"""The two release lines and the date their tags resolve to."""

import unittest

from pack.release_tags import package_date, split_tag


class ReleaseTagTests(unittest.TestCase):

    def test_a_date_is_the_main_line(self):
        self.assertEqual(split_tag("2026-10-01"), ("main", "2026-10-01"))

    def test_the_upstream_prefix_is_the_upstream_line(self):
        self.assertEqual(split_tag("upstream-2026-10-01"), ("upstream", "2026-10-01"))

    def test_both_lines_name_their_assets_by_the_date(self):
        self.assertEqual(package_date("2026-10-01"), "20261001")
        self.assertEqual(package_date("upstream-2026-10-01"), "20261001")

    def test_anything_else_is_refused(self):
        for tag in ("nightly-2026-10-01", "upstream2026-10-01", "2026-10-1",
                    "upstream-", "v1.0.0", "", None):
            with self.assertRaises(ValueError, msg=tag):
                split_tag(tag)


if __name__ == "__main__":
    unittest.main()
