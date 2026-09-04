"""Tests for CLI."""

import json
import subprocess
import sys
from pathlib import Path


SAMPLE_LOG = """2024-01-15T10:30:45Z INFO Application started
2024-01-15T10:30:46Z ERROR Connection timeout after 5000ms
2024-01-15T10:30:47Z WARNING Retrying connection
2024-01-15T10:30:48Z ERROR Connection timeout after 3000ms
2024-01-15T10:30:49Z INFO Request processed
2024-01-15T10:30:50Z ERROR Database connection refused
2024-01-15T10:30:51Z ERROR Connection timeout after 8000ms
"""


def test_cli_with_stdin(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "error_group.cli"],
        input=SAMPLE_LOG,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent / "src"),
    )
    assert result.returncode == 0
    assert "pattern" in result.stdout.lower() or "error" in result.stdout.lower()


def test_cli_json_output(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text(SAMPLE_LOG)
    
    result = subprocess.run(
        [sys.executable, "-m", "error_group.cli", str(log_file), "--json"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent / "src"),
    )
    assert result.returncode == 0
    
    data = json.loads(result.stdout)
    assert "total_errors" in data
    assert "unique_patterns" in data
    assert data["total_errors"] >= 4


def test_cli_no_errors(tmp_path):
    log_file = tmp_path / "clean.log"
    log_file.write_text("INFO Everything is fine\nINFO Still good\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "error_group.cli", str(log_file)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent / "src"),
    )
    assert result.returncode == 0
    assert "no errors" in result.stderr.lower()
