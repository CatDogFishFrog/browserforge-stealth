"""
Tests for browserforge-stealth CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from browserforge_stealth.cli import main


def test_cli_generate_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["generate", "--os", "windows", "--locale", "uk-UA", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["locale"] == "uk-UA"
    assert data["os"] == "windows"
    assert "navigator" in data["raw_data"]


def test_cli_generate_file_and_inspect(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "test_fp.json"
    code = main(["generate", "--os", "windows", "--output", str(out_file)])
    assert code == 0
    assert out_file.exists()

    # Inspect command
    code = main(["inspect", str(out_file)])
    assert code == 0
    captured = capsys.readouterr()
    assert "BrowserForge Fingerprint Summary" in captured.out
    assert "OS:       windows" in captured.out
