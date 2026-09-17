import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def test_report_json_contract_unchanged():
    result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py"), "report"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data == [
        {"sku": "A100", "name": "Widget", "qty": 42},
        {"sku": "B200", "name": "Gadget", "qty": 7},
    ]


def test_report_json_format_explicit_matches_default():
    result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py"), "report", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    default_result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py"), "report"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == default_result.stdout


def test_report_csv_export():
    result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py"), "report", "--format", "csv"],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.splitlines()
    assert lines == [
        "sku,name,qty",
        "A100,Widget,42",
        "B200,Gadget,7",
    ]


def test_report_invalid_format_rejected():
    result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py"), "report", "--format", "xml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
