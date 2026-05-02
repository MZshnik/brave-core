#!/usr/bin/env vpython3
# Copyright (c) 2026 The Brave Authors. All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
"""git_cr follow-renames — repair brave-core artefacts after upstream renames.

For each file rename found in the Chromium git log for the given revision range,
updates every brave-core artefact that references the old path: chromium_src/
shadow files (move + shadow include + include guard), rewrite/ TOML files
(move + patch deletion), and all cross-brave-core #include/#import/comment/
BUILD.gn references.

Usage
-----
  git cr follow-renames [--no-git] [--verbose] <rev-range>

  # All renames between two Chromium version tags (typical version bump):
  git cr follow-renames 130.0.6723.58..131.0.6778.85

  # All renames in the last N commits of the Chromium repo:
  git cr follow-renames HEAD~5..HEAD

  # Renames introduced by a single upstream commit:
  git cr follow-renames abc123^..abc123
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import List, Tuple

from incendiary_error_handler import IncendiaryErrorHandler
from terminal import console, terminal
import repository
from source_rewrite import (
    compute_guard,
    find_guard,
    insert_guard,
    patch_name_for,
    rewrite_guard_in_file,
    update_references,
    update_shadow_include,
)

# C++ extensions for shadow-include and guard processing.
_CPP_EXTENSIONS: frozenset[str] = frozenset(
    {'.h', '.hh', '.cc', '.mm', '.m', '.cpp'})

_RenamePair = Tuple[str, str]


def cmd_follow_renames(args: List[str]) -> int:
    """Parse follow-renames arguments and process all upstream renames."""
    parser = argparse.ArgumentParser(
        prog='git cr follow-renames',
        description=('Repair brave-core artefacts after upstream Chromium '
                     'file renames.'),
    )
    parser.add_argument('--no-git',
                        action='store_true',
                        dest='no_git',
                        help='Use filesystem ops instead of git mv/rm')
    parser.add_argument('--verbose',
                        action='store_true',
                        help='Enable verbose logging')
    parser.add_argument(
        'rev_range',
        help='Git revision range in the Chromium repo, e.g. old_tag..new_tag')
    parsed = parser.parse_args(args)

    logging.basicConfig(
        level=logging.DEBUG if parsed.verbose else logging.INFO,
        format='%(message)s',
        handlers=[IncendiaryErrorHandler(markup=True, rich_tracebacks=True)])

    renames = _get_chromium_renames(parsed.rev_range)

    with terminal.with_status('Following renames...'):
        for old_chromium, new_chromium in renames:
            _repair_chromium_src(old_chromium, new_chromium, parsed.no_git)
            _repair_rewrite_toml(old_chromium, new_chromium, parsed.no_git)
            update_references(old_chromium, new_chromium)

    console.log(f'[bold green]✔[/] {len(renames)} rename(s) processed')
    return 0


def _get_chromium_renames(rev_range: str) -> List[_RenamePair]:
    """Returns (old_path, new_path) pairs from the Chromium git log.

    Runs git log --diff-filter=R --name-status in the Chromium repository.
    Output lines look like: "R100<TAB>old/path.h<TAB>new/path.h"
    Blank lines (between commits) and non-rename lines are ignored.
    """
    raw = repository.chromium.run_git('log', '--diff-filter=R',
                                      '--name-status', '--format=', rev_range)
    renames: List[_RenamePair] = []
    for line in raw.splitlines():
        parts = line.split('\t')
        if len(parts) == 3 and parts[0].startswith('R'):
            renames.append((parts[1], parts[2]))
    return renames


def _repair_chromium_src(old_chromium: str, new_chromium: str,
                         no_git: bool) -> None:
    """Moves and repairs the chromium_src/ shadow file for one rename.

    If no shadow file exists at chromium_src/old_chromium, this is a no-op.
    For moved files: updates the shadow #include line (C++ files) and
    regenerates the include guard (.h files only).
    """
    brave_root = Path(repository.BRAVE_CORE_PATH)
    old_shadow = brave_root / 'chromium_src' / old_chromium
    if not old_shadow.exists():
        return

    new_shadow = brave_root / 'chromium_src' / new_chromium
    new_shadow.parent.mkdir(parents=True, exist_ok=True)

    if no_git:
        old_shadow.rename(new_shadow)
    else:
        repository.brave.run_git('mv', os.path.relpath(old_shadow),
                                 os.path.relpath(new_shadow))

    if new_shadow.suffix.lower() in _CPP_EXTENSIONS:
        update_shadow_include(new_shadow, old_chromium, new_chromium)

    if new_shadow.suffix == '.h':
        chromium_root = Path(repository.CHROMIUM_SRC_PATH)
        new_guard = compute_guard(new_shadow.relative_to(chromium_root))
        content = new_shadow.read_text(encoding='utf-8')
        old_guard = find_guard(content)
        if old_guard:
            rewrite_guard_in_file(new_shadow, old_guard, new_guard)
        else:
            insert_guard(new_shadow, new_guard)


def _repair_rewrite_toml(old_chromium: str, new_chromium: str,
                         no_git: bool) -> None:
    """Moves the rewrite/ TOML and deletes the corresponding patch file.

    TOML path convention: chromium path A/foo.h lives at rewrite/A/foo.h.toml.
    If no TOML exists, this is a no-op. Missing patch files log a warning
    instead of raising.
    """
    brave_root = Path(repository.BRAVE_CORE_PATH)
    old_p = Path(old_chromium)
    old_toml = brave_root / 'rewrite' / old_p.parent / (old_p.name + '.toml')
    if not old_toml.exists():
        return

    new_p = Path(new_chromium)
    new_toml = brave_root / 'rewrite' / new_p.parent / (new_p.name + '.toml')
    new_toml.parent.mkdir(parents=True, exist_ok=True)

    if no_git:
        old_toml.rename(new_toml)
    else:
        repository.brave.run_git('mv', os.path.relpath(old_toml),
                                 os.path.relpath(new_toml))

    patch_file = brave_root / 'patches' / patch_name_for(old_p)
    if not patch_file.exists():
        logging.warning(
            'Expected patch file not found: %s; skipping deletion.',
            patch_file)
        return
    if no_git:
        patch_file.unlink()
    else:
        repository.brave.run_git('rm', str(patch_file.relative_to(brave_root)))
