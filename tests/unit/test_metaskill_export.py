import hashlib
import os
import sys
from pathlib import Path

import pytest

from groundspec.metaskill.export import (
    DestinationExists,
    UnsafeDestination,
    UnsafeRelativePath,
    export_file_set,
)

FILES = {"SKILL.md": "hello", "references/a.md": "world"}


def test_basic_export_writes_all_files(tmp_path: Path):
    dest = tmp_path / "out"
    result = export_file_set(FILES, dest)
    assert (dest / "SKILL.md").read_text() == "hello"
    assert (dest / "references" / "a.md").read_text() == "world"
    assert result.destination == dest
    assert {f.relative_path for f in result.files} == set(FILES)


def test_manifest_hashes_are_correct(tmp_path: Path):
    result = export_file_set(FILES, tmp_path / "out")
    by_path = {f.relative_path: f for f in result.files}
    expected = hashlib.sha256(b"hello").hexdigest()
    assert by_path["SKILL.md"].sha256 == expected
    assert by_path["SKILL.md"].size == len(b"hello")


def test_refuses_to_overwrite_without_force(tmp_path: Path):
    dest = tmp_path / "out"
    export_file_set(FILES, dest)
    with pytest.raises(DestinationExists):
        export_file_set(FILES, dest)
    # original content untouched
    assert (dest / "SKILL.md").read_text() == "hello"


def test_force_overwrites(tmp_path: Path):
    dest = tmp_path / "out"
    export_file_set(FILES, dest)
    export_file_set({"SKILL.md": "updated"}, dest, force=True)
    assert (dest / "SKILL.md").read_text() == "updated"
    assert not (dest / "references").exists()  # old files not merged, replaced wholesale


def test_repeated_export_is_deterministic(tmp_path: Path):
    r1 = export_file_set(FILES, tmp_path / "out1")
    r2 = export_file_set(FILES, tmp_path / "out2")
    assert sorted(f.sha256 for f in r1.files) == sorted(f.sha256 for f in r2.files)
    assert sorted(f.relative_path for f in r1.files) == sorted(f.relative_path for f in r2.files)


@pytest.mark.parametrize(
    "bad_path",
    ["../escape.md", "/absolute.md", "a/../../b.md", "a/../../../b.md", ""],
)
def test_unsafe_relative_paths_rejected(tmp_path: Path, bad_path: str):
    with pytest.raises(UnsafeRelativePath):
        export_file_set({bad_path: "x"}, tmp_path / "out")


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs elevated privileges on Windows")
def test_refuses_to_write_through_symlinked_destination(tmp_path: Path):
    real_target = tmp_path / "real"
    real_target.mkdir()
    symlink_dest = tmp_path / "link"
    os.symlink(real_target, symlink_dest, target_is_directory=True)
    with pytest.raises(UnsafeDestination):
        export_file_set(FILES, symlink_dest, force=True)


def test_no_partial_write_left_behind_on_unsafe_path_failure(tmp_path: Path):
    dest = tmp_path / "out"
    with pytest.raises(UnsafeRelativePath):
        export_file_set({"SKILL.md": "ok", "../escape.md": "bad"}, dest)
    assert not dest.exists()


def test_no_stray_temp_directories_left_behind(tmp_path: Path):
    dest = tmp_path / "out"
    export_file_set(FILES, dest)
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".out.tmp-")]
    assert leftovers == []


def test_handles_non_ascii_unicode_content_correctly(tmp_path: Path):
    content = {"SKILL.md": "café éèê 中文 \U0001f600 emoji, and mixed scripts."}
    dest = tmp_path / "out"
    result = export_file_set(content, dest)
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == content["SKILL.md"]
    assert result.files[0].size == len(content["SKILL.md"].encode("utf-8"))


def test_control_characters_in_content_are_written_verbatim_not_executed(tmp_path: Path):
    # Content is authored by groundspec itself (canonical Skill text), never
    # untrusted input, so this only needs to prove control bytes round-trip
    # safely through the filesystem -- not that they're stripped.
    content = {"SKILL.md": "line one\x07\x1b[31mfake ansi\x1b[0m\nline two"}
    dest = tmp_path / "out"
    export_file_set(content, dest)
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == content["SKILL.md"]
