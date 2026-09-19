"""Unit tests for groundspec.packs.sdk.safety -- the pack-directory
security scan. See docs/threat-model.md's pack-extensibility section for
what this is and is not meant to catch.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from groundspec.packs.sdk.errors import UnsafePackContentError
from groundspec.packs.sdk.safety import MAX_FILE_BYTES, scan_pack_directory


def test_clean_directory_passes(tmp_path: Path):
    (tmp_path / "pack.toml").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# hi\n", encoding="utf-8")
    report = scan_pack_directory(tmp_path)
    assert report.file_count == 2


@pytest.mark.parametrize("suffix", [".py", ".sh", ".exe", ".js", ".ps1", ".dll"])
def test_forbidden_extensions_are_rejected(tmp_path: Path, suffix: str):
    (tmp_path / f"evil{suffix}").write_bytes(b"not actually code, just an extension")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_disallowed_but_non_executable_extension_is_still_rejected(tmp_path: Path):
    (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_shebang_disguised_as_toml_is_rejected(tmp_path: Path):
    (tmp_path / "sneaky.toml").write_bytes(b"#!/bin/sh\necho hi\n")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_elf_magic_disguised_as_md_is_rejected(tmp_path: Path):
    (tmp_path / "sneaky.md").write_bytes(b"\x7fELF" + b"\x00" * 20)
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_zip_magic_disguised_as_json_is_rejected(tmp_path: Path):
    (tmp_path / "sneaky.json").write_bytes(b"PK\x03\x04" + b"\x00" * 20)
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_oversized_file_is_rejected(tmp_path: Path):
    (tmp_path / "huge.md").write_bytes(b"a" * (MAX_FILE_BYTES + 1))
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_control_character_in_filename_is_rejected(tmp_path: Path):
    # Built at runtime (a vertical-tab control character) rather than as a
    # literal escape in this file's own source, so this test file itself
    # never contains a raw control byte.
    bad_name = "weird" + chr(0x0B) + "file.md"
    try:
        (tmp_path / bad_name).write_text("x", encoding="utf-8")
    except (OSError, ValueError):
        pytest.skip("filesystem refuses this control character in filenames before groundspec even sees it")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="symlink creation needs elevated privileges on Windows")
def test_symlink_is_rejected(tmp_path: Path):
    target = tmp_path / "real.md"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(target)
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_deeply_nested_directory_is_rejected(tmp_path: Path):
    deep = tmp_path
    for i in range(12):
        deep = deep / f"d{i}"
    deep.mkdir(parents=True)
    (deep / "buried.md").write_text("x", encoding="utf-8")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)


def test_too_many_files_is_rejected(tmp_path: Path):
    for i in range(210):
        (tmp_path / f"f{i}.md").write_text("x", encoding="utf-8")
    with pytest.raises(UnsafePackContentError):
        scan_pack_directory(tmp_path)
