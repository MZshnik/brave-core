#!/usr/bin/env vpython3
# Copyright (c) 2026 The Brave Authors. All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
"""git_cr mv — move a file or directory in brave-core and repair artefacts.

Performs the filesystem or git rename then updates every downstream artefact
that depends on the old path: C++ include guards, chromium_src shadow-file
includes, cross-tree #include/#import references, // comment references,
BUILD.gn source-list entries, and plaster TOML patch files.
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
from user_validation_error import UserValidationError

# Only .h files receive include-guard processing (spec §1.2 Step 2).
_HEADER_EXTENSIONS: frozenset[str] = frozenset({'.h'})

# C++ extensions for shadow-include updating (spec §1.2 Step 3).
_CPP_EXTENSIONS: frozenset[str] = frozenset(
    {'.h', '.hh', '.cc', '.mm', '.m', '.cpp'})

_FilePair = Tuple[Path, Path]


def cmd_mv(args: List[str]) -> int:
    """Parse mv arguments and perform the file move with all repair steps."""
    parser = argparse.ArgumentParser(
        prog='git cr mv',
        description=
        'Move a file or directory inside brave-core and repair artefacts.',
    )
    parser.add_argument('--mkdir',
                        action='store_true',
                        help='Create destination parent directory if missing')
    parser.add_argument('--no-git',
                        action='store_true',
                        dest='no_git',
                        help='Use filesystem rename instead of git mv')
    parser.add_argument('--verbose',
                        action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('source', help='Source file or directory')
    parser.add_argument('destination', help='Destination path')
    parsed = parser.parse_args(args)

    logging.basicConfig(
        level=logging.DEBUG if parsed.verbose else logging.INFO,
        format='%(message)s',
        handlers=[IncendiaryErrorHandler(markup=True, rich_tracebacks=True)])

    brave_root = Path(repository.BRAVE_CORE_PATH)
    cwd = Path.cwd()
    try:
        cwd.relative_to(brave_root)
    except ValueError:
        raise UserValidationError(
            'git cr mv: must be run from within the brave-core tree '
            f'({brave_root})') from None

    src = (cwd / parsed.source).resolve()
    dest = (cwd / parsed.destination).resolve()

    with terminal.with_status(f'Moving {parsed.source}'):
        file_pairs = _step1_move(src, dest, parsed.mkdir, parsed.no_git)

        _step2_guards(file_pairs)
        _step3_shadow_includes(file_pairs)

        chromium_root = Path(repository.CHROMIUM_SRC_PATH)
        for old_file, new_file in file_pairs:
            old_rel = old_file.relative_to(chromium_root).as_posix()
            new_rel = new_file.relative_to(chromium_root).as_posix()
            update_references(old_rel, new_rel)

        _step5_plaster(file_pairs, parsed.no_git)

    console.log(f'[bold green]✔[/] {parsed.source} → {parsed.destination}')
    return 0


def _step1_move(src: Path, dest: Path, mkdir: bool,
                no_git: bool) -> List[_FilePair]:
    """Validates paths and performs the move.

    Returns a list of (old_abs, new_abs) pairs for every file moved.
    All pairs are collected before the move so old paths are available
    for later artefact repair steps.
    """
    rewrite_path = Path(repository.BRAVE_CORE_PATH) / 'rewrite'

    if not src.exists():
        raise UserValidationError(f'git cr mv: source does not exist: {src}')

    if dest.is_file():
        raise UserValidationError(
            f'git cr mv: destination already exists: {dest}')

    if not dest.parent.exists():
        if not mkdir:
            raise UserValidationError(
                f'git cr mv: destination parent does not exist: {dest.parent}\n'
                'Pass --mkdir to create it automatically.')
        dest.parent.mkdir(parents=True, exist_ok=True)

    if (src.is_relative_to(rewrite_path)
            and not dest.is_relative_to(rewrite_path)):
        raise UserValidationError(
            'git cr mv: cannot move a rewrite/ path to a destination outside '
            f'rewrite/ ({rewrite_path})')

    if src.is_dir():
        file_pairs: List[_FilePair] = [(f, dest / f.relative_to(src))
                                       for f in src.rglob('*') if f.is_file()]
    else:
        file_pairs = [(src, dest)]

    if no_git:
        src.rename(dest)
    else:
        repository.brave.run_git(
            'mv',
            os.path.relpath(src),
            os.path.relpath(dest),
        )

    return file_pairs


def _step2_guards(file_pairs: List[_FilePair]) -> None:
    """Regenerates C++ include guards for every moved .h file."""
    chromium_root = Path(repository.CHROMIUM_SRC_PATH)
    for _old_file, new_file in file_pairs:
        if new_file.suffix not in _HEADER_EXTENSIONS:
            continue
        new_guard = compute_guard(new_file.relative_to(chromium_root))
        content = new_file.read_text(encoding='utf-8')
        old_guard = find_guard(content)
        if old_guard:
            rewrite_guard_in_file(new_file, old_guard, new_guard)
        else:
            insert_guard(new_file, new_guard)


def _step3_shadow_includes(file_pairs: List[_FilePair]) -> None:
    """Updates the upstream angle-bracket include in moved shadow files."""
    chromium_src_path = Path(repository.BRAVE_CORE_PATH) / 'chromium_src'
    for old_file, new_file in file_pairs:
        if not old_file.is_relative_to(chromium_src_path):
            continue
        if new_file.suffix.lower() not in _CPP_EXTENSIONS:
            continue
        old_chromium = old_file.relative_to(chromium_src_path).as_posix()
        new_chromium = new_file.relative_to(chromium_src_path).as_posix()
        update_shadow_include(new_file, old_chromium, new_chromium)


def _step5_plaster(file_pairs: List[_FilePair], no_git: bool) -> None:
    """Deletes stale patch files for any moved rewrite/ TOML files."""
    brave_root = Path(repository.BRAVE_CORE_PATH)
    rewrite_path = brave_root / 'rewrite'
    patches_path = brave_root / 'patches'

    for old_file, _new_file in file_pairs:
        if old_file.suffix != '.toml':
            continue
        if not old_file.is_relative_to(rewrite_path):
            continue
        old_chromium_path = old_file.relative_to(rewrite_path).with_suffix('')
        patch_file = patches_path / patch_name_for(old_chromium_path)
        if not patch_file.exists():
            logging.warning(
                'Expected patch file not found: %s; skipping deletion.',
                patch_file)
            continue
        if no_git:
            patch_file.unlink()
        else:
            repository.brave.run_git('rm',
                                     str(patch_file.relative_to(brave_root)))
