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
