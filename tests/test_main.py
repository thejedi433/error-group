"""Tests for __main__ module entry point."""

import subprocess
import sys
from unittest.mock import patch
from error_group.__main__ import main as main_from_module
from error_group.cli import main as main_from_cli


class TestMainEntryPoint:
    def test_main_is_imported_from_cli(self):
        """Verify __main__ imports main from cli module."""
        assert main_from_module is main_from_cli

    def test_can_call_main_directly(self):
        """Verify main can be called."""
        with patch('sys.argv', ['error_group', '--help']):
            try:
                main_from_module()
            except SystemExit as e:
                assert e.code == 0

    def test_python_m_error_group_works(self):
        """Verify `python -m error_group` runs successfully."""
        result = subprocess.run(
            [sys.executable, '-m', 'error_group', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Fuzzy log error grouping' in result.stdout

    def test_python_m_error_group_with_stdin(self):
        """Verify `python -m error_group` processes input."""
        log_input = "2024-01-15T10:30:45Z ERROR Connection timeout\nINFO ok\n"
        result = subprocess.run(
            [sys.executable, '-m', 'error_group'],
            input=log_input,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Connection timeout' in result.stdout
