#!/usr/bin/env vpython3
# Copyright (c) 2026 The Brave Authors. All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for git_cr_follow_renames.py."""

import logging
import unittest
from pathlib import Path

import repository
from git_cr_follow_renames import _get_chromium_renames, cmd_follow_renames
from test.fake_chromium_src import FakeChromiumSrc


class _Base(unittest.TestCase):
    """Shared fixture: a fresh fake brave-core + chromium repo per test."""

    def setUp(self) -> None:
        self._repo = FakeChromiumSrc()
        self._repo.setup()
        self.addCleanup(self._repo.cleanup)
        (self._repo.brave / 'chromium_src').mkdir(exist_ok=True)
        (self._repo.brave / 'rewrite').mkdir(exist_ok=True)

    @property
    def _brave(self) -> Path:
        return self._repo.brave

    @property
    def _chromium(self) -> Path:
        return self._repo.chromium

    def _chromium_commit(self, rel: str, content: str) -> str:
        """Write, stage, and commit a file in chromium. Returns HEAD hash."""
        self._repo.write_and_stage_file(rel, content, self._chromium)
        return self._repo.commit(f'Add {rel}', self._chromium)

    def _chromium_rename(self, old_rel: str, new_rel: str) -> str:
        """Rename a file in chromium via git mv + commit. Returns HEAD hash."""
        new_path = self._chromium / new_rel
        new_path.parent.mkdir(parents=True, exist_ok=True)
        self._repo._run_git_command(['mv', old_rel, new_rel], self._chromium)
        return self._repo.commit(f'Rename {old_rel} -> {new_rel}',
                                 self._chromium)

    def _chromium_head(self) -> str:
        """Returns HEAD hash of the chromium repo."""
        return self._repo._run_git_command(['rev-parse', 'HEAD'],
                                           self._chromium)

    def _brave_commit(self, rel: str, content: str) -> Path:
        """Write, stage, and commit a file in brave. Returns absolute Path."""
        self._repo.write_and_stage_file(rel, content, self._brave)
        self._repo.commit(f'Add {rel}', self._brave)
        return self._brave / rel

    def _brave_write(self, rel: str, content: str) -> Path:
        """Write a file in brave without staging (for --no-git tests)."""
        path = self._brave / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path


# ---------------------------------------------------------------------------
# Rename parsing tests
# ---------------------------------------------------------------------------


class ParseTest(_Base):
    """_get_chromium_renames correctly parses git log output."""

    def test_rename_parsed(self) -> None:
        """A single rename commit yields one (old, new) pair."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// header\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        renames = _get_chromium_renames(f'{before}..HEAD')

        self.assertEqual(renames, [('A/foo.h', 'B/foo.h')])

    def test_empty_range_returns_empty_list(self) -> None:
        """A range with no renames yields an empty list."""
        before = self._chromium_head()
        # No changes in chromium.
        renames = _get_chromium_renames(f'{before}..HEAD')
        self.assertEqual(renames, [])

    def test_non_rename_commit_ignored(self) -> None:
        """A range with only modifications (no renames) yields an empty list."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// v1\n')
        self._repo.write_and_stage_file('A/foo.h', '// v2\n', self._chromium)
        self._repo.commit('Modify A/foo.h', self._chromium)

        renames = _get_chromium_renames(f'{before}..HEAD')
        self.assertEqual(renames, [])


# ---------------------------------------------------------------------------
# chromium_src/ shadow-file repair tests
# ---------------------------------------------------------------------------


class ShadowFileTest(_Base):
    """_repair_chromium_src moves and patches the brave shadow file."""

    def test_shadow_h_file_moved_guard_updated(self) -> None:
        """chromium_src/.h file moves and its include guard is rewritten."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('chromium_src/A/foo.h',
                           ('#ifndef BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#define BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#endif  // BRAVE_CHROMIUM_SRC_A_FOO_H_\n'))
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames([f'{before}..HEAD'])

        new_path = self._brave / 'chromium_src' / 'B' / 'foo.h'
        self.assertTrue(new_path.exists())
        self.assertFalse(
            (self._brave / 'chromium_src' / 'A' / 'foo.h').exists())
        content = new_path.read_text(encoding='utf-8')
        self.assertIn('BRAVE_CHROMIUM_SRC_B_FOO_H_', content)
        self.assertNotIn('BRAVE_CHROMIUM_SRC_A_FOO_H_', content)

    def test_shadow_include_line_updated(self) -> None:
        """#include <A/foo.h> in the shadow file becomes #include <B/foo.h>."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('chromium_src/A/foo.h',
                           ('#ifndef BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#define BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#include <A/foo.h>\n'
                            '#endif  // BRAVE_CHROMIUM_SRC_A_FOO_H_\n'))
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames([f'{before}..HEAD'])

        content = (self._brave / 'chromium_src' / 'B' /
                   'foo.h').read_text(encoding='utf-8')
        self.assertIn('#include <B/foo.h>', content)
        self.assertNotIn('#include <A/foo.h>', content)

    def test_shadow_cc_moved_no_guard(self) -> None:
        """A .cc shadow file moves but no include guard is inserted."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.cc', '// impl\n')
        original = '// implementation\nvoid foo() {}\n'
        self._brave_commit('chromium_src/A/foo.cc', original)
        self._chromium_rename('A/foo.cc', 'B/foo.cc')

        cmd_follow_renames([f'{before}..HEAD'])

        new_path = self._brave / 'chromium_src' / 'B' / 'foo.cc'
        self.assertTrue(new_path.exists())
        content = new_path.read_text(encoding='utf-8')
        self.assertNotIn('#ifndef', content)

    def test_no_shadow_file_is_noop(self) -> None:
        """Chromium rename with no matching shadow file does not raise."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')
        # No brave chromium_src/A/foo.h created.

        cmd_follow_renames([f'{before}..HEAD'])  # Must not raise.

        self.assertFalse(
            (self._brave / 'chromium_src' / 'B' / 'foo.h').exists())


# ---------------------------------------------------------------------------
# rewrite/ TOML and patch-file repair tests
# ---------------------------------------------------------------------------


class TomlTest(_Base):
    """_repair_rewrite_toml moves the TOML and deletes the patch."""

    def test_toml_moved_patch_deleted(self) -> None:
        """rewrite/A/foo.h.toml moves to rewrite/B/foo.h.toml; patch deleted."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('rewrite/A/foo.h.toml', '[substitution]\n')
        self._brave_commit('patches/A-foo.h.patch', 'diff\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames([f'{before}..HEAD'])

        self.assertTrue(
            (self._brave / 'rewrite' / 'B' / 'foo.h.toml').exists())
        self.assertFalse(
            (self._brave / 'rewrite' / 'A' / 'foo.h.toml').exists())
        self.assertFalse((self._brave / 'patches' / 'A-foo.h.patch').exists())

    def test_missing_patch_warns_no_error(self) -> None:
        """TOML exists but patch is absent: warning logged, TOML still moves."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('rewrite/A/foo.h.toml', '[substitution]\n')
        # No patches/A-foo.h.patch.
        self._chromium_rename('A/foo.h', 'B/foo.h')

        with self.assertLogs(level=logging.WARNING):
            cmd_follow_renames([f'{before}..HEAD'])

        self.assertTrue(
            (self._brave / 'rewrite' / 'B' / 'foo.h.toml').exists())

    def test_no_toml_is_noop(self) -> None:
        """A Chromium rename with no TOML in rewrite/ does not raise."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames([f'{before}..HEAD'])  # Must not raise.


# ---------------------------------------------------------------------------
# Cross-brave-core reference update tests
# ---------------------------------------------------------------------------


class ReferencesTest(_Base):
    """update_references is called for every rename regardless of artefacts."""

    def test_include_updated_even_without_shadow_file(self) -> None:
        """Brave #include of a Chromium path updates with no shadow file."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('other/user.cc', '#include "A/foo.h"\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames([f'{before}..HEAD'])

        content = (self._brave / 'other' /
                   'user.cc').read_text(encoding='utf-8')
        self.assertIn('#include "B/foo.h"', content)
        self.assertNotIn('#include "A/foo.h"', content)


# ---------------------------------------------------------------------------
# Multiple renames in a single range
# ---------------------------------------------------------------------------


class MultipleRenamesTest(_Base):
    """All renames in a rev range are processed in order."""

    def test_two_renames_both_processed(self) -> None:
        """Two separate rename commits in the range are both fully repaired."""
        before = self._chromium_head()

        # First rename: A/foo.h → B/foo.h
        self._chromium_commit('A/foo.h', '// foo\n')
        self._brave_commit('chromium_src/A/foo.h',
                           ('#ifndef BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#define BRAVE_CHROMIUM_SRC_A_FOO_H_\n'
                            '#endif  // BRAVE_CHROMIUM_SRC_A_FOO_H_\n'))
        self._chromium_rename('A/foo.h', 'B/foo.h')

        # Second rename: C/bar.h → D/bar.h
        self._chromium_commit('C/bar.h', '// bar\n')
        self._brave_commit('rewrite/C/bar.h.toml', '[substitution]\n')
        self._brave_commit('patches/C-bar.h.patch', 'diff\n')
        self._chromium_rename('C/bar.h', 'D/bar.h')

        cmd_follow_renames([f'{before}..HEAD'])

        # First rename: shadow file moved.
        self.assertTrue(
            (self._brave / 'chromium_src' / 'B' / 'foo.h').exists())
        self.assertFalse(
            (self._brave / 'chromium_src' / 'A' / 'foo.h').exists())

        # Second rename: TOML moved, patch deleted.
        self.assertTrue(
            (self._brave / 'rewrite' / 'D' / 'bar.h.toml').exists())
        self.assertFalse((self._brave / 'patches' / 'C-bar.h.patch').exists())


# ---------------------------------------------------------------------------
# --no-git flag tests
# ---------------------------------------------------------------------------


class NoGitTest(_Base):
    """--no-git uses Path.rename/unlink instead of git mv/rm."""

    def test_no_git_shadow_uses_rename(self) -> None:
        """--no-git: shadow file moved via Path.rename, not staged in git."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        self._brave_commit('chromium_src/A/foo.h', '// shadow\n')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        cmd_follow_renames(['--no-git', f'{before}..HEAD'])

        self.assertTrue(
            (self._brave / 'chromium_src' / 'B' / 'foo.h').exists())
        self.assertFalse(
            (self._brave / 'chromium_src' / 'A' / 'foo.h').exists())
        # Nothing should be staged.
        staged = repository.brave.run_git('diff', '--cached', '--name-only')
        self.assertEqual(staged, '')

    def test_no_git_toml_patch_uses_unlink(self) -> None:
        """--no-git: patch deleted with Path.unlink, no git rm."""
        before = self._chromium_head()
        self._chromium_commit('A/foo.h', '// src\n')
        # Stage + commit the TOML but only write (don't commit) the patch
        # so that git rm would fail on it.
        self._brave_commit('rewrite/A/foo.h.toml', '[substitution]\n')
        patch_file = self._brave / 'patches' / 'A-foo.h.patch'
        patch_file.write_text('dummy\n', encoding='utf-8')
        self._chromium_rename('A/foo.h', 'B/foo.h')

        (self._brave / 'rewrite' / 'B').mkdir(parents=True, exist_ok=True)
        cmd_follow_renames(['--no-git', f'{before}..HEAD'])

        self.assertFalse(patch_file.exists())


if __name__ == '__main__':
    unittest.main()
