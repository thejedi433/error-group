"""Tests for CLI functions."""

import json
from pathlib import Path
from unittest.mock import patch
import sys

from error_group.cli import extract_errors, format_text_summary, main, read_input


SAMPLE_LOG = """2024-01-15T10:30:45Z INFO Application started
2024-01-15T10:30:46Z ERROR Connection timeout after 5000ms
2024-01-15T10:30:47Z WARNING Retrying connection
2024-01-15T10:30:48Z ERROR Connection timeout after 3000ms
2024-01-15T10:30:49Z INFO Request processed
2024-01-15T10:30:50Z ERROR Database connection refused
2024-01-15T10:30:51Z ERROR Connection timeout after 8000ms
"""


class TestExtractErrors:
    def test_extracts_error_lines(self):
        lines = SAMPLE_LOG.split('\n')
        errors = extract_errors(lines)
        # 3 ERROR connection timeout + 1 WARNING + 1 ERROR database
        assert len(errors) == 5
        assert all('ERROR' in line or 'WARNING' in line for line in errors)

    def test_extracts_warning_lines(self):
        lines = ["INFO ok", "WARNING something", "ERROR bad"]
        errors = extract_errors(lines)
        assert len(errors) == 2

    def test_no_errors_returns_empty(self):
        lines = ["INFO ok", "DEBUG trace"]
        errors = extract_errors(lines)
        assert errors == []


class TestFormatTextSummary:
    def test_formats_summary_text(self):
        summary = [
            {'pattern': 'Connection timeout after N ms', 'count': 3, 'examples': ['ERROR Connection timeout after 5000ms']},
            {'pattern': 'Database connection refused', 'count': 1, 'examples': ['ERROR Database connection refused']},
        ]
        text = format_text_summary(summary)
        assert 'Found 4 error(s)' in text
        assert '2 pattern(s)' in text
        assert '[3x]' in text
        assert '[1x]' in text

    def test_includes_examples(self):
        summary = [
            {'pattern': 'test', 'count': 1, 'examples': ['Example line 1', 'Example line 2']},
        ]
        text = format_text_summary(summary)
        assert 'Example 1: Example line 1' in text
        assert 'Example 2: Example line 2' in text


class TestReadInput:
    def test_reads_from_file(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("line1\nline2\n")
        lines = read_input([str(log_file)])
        assert len(lines) == 2
        assert 'line1\n' in lines

    def test_reads_multiple_files(self, tmp_path):
        file1 = tmp_path / "test1.log"
        file2 = tmp_path / "test2.log"
        file1.write_text("line1\n")
        file2.write_text("line2\n")
        lines = read_input([str(file1), str(file2)])
        assert len(lines) == 2

    def test_file_not_found_exits(self, tmp_path, capsys):
        nonexistent = tmp_path / "missing.log"
        try:
            read_input([str(nonexistent)])
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1
        captured = capsys.readouterr()
        assert 'Error: File not found' in captured.err

    def test_reads_from_stdin_interactive(self, capsys):
        """Test reading from stdin when isatty() returns True (interactive mode)"""
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            mock_stdin.readlines.return_value = ["ERROR test\n"]
            
            lines = read_input(None)
            
            captured = capsys.readouterr()
            assert 'Reading from stdin' in captured.err
            assert lines == ["ERROR test\n"]


class TestMain:
    def test_main_with_stdin(self, capsys):
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.readlines.return_value = SAMPLE_LOG.split('\n')
            mock_stdin.__iter__.return_value = iter(SAMPLE_LOG.split('\n'))
            
            # Patch sys.argv
            with patch('sys.argv', ['error-group']):
                main()
        
        captured = capsys.readouterr()
        assert 'pattern' in captured.out.lower() or 'error' in captured.out.lower()

    def test_main_with_file(self, tmp_path, capsys):
        log_file = tmp_path / "test.log"
        log_file.write_text(SAMPLE_LOG)
        
        with patch('sys.argv', ['error-group', str(log_file)]):
            main()
        
        captured = capsys.readouterr()
        assert 'error' in captured.out.lower()

    def test_main_json_output(self, tmp_path, capsys):
        log_file = tmp_path / "test.log"
        log_file.write_text(SAMPLE_LOG)
        
        with patch('sys.argv', ['error-group', str(log_file), '--json']):
            main()
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert 'total_errors' in data
        assert 'unique_patterns' in data
        assert data['total_errors'] >= 4

    def test_main_no_errors(self, tmp_path, capsys):
        log_file = tmp_path / "clean.log"
        log_file.write_text("INFO Everything is fine\nINFO Still good\n")
        
        with patch('sys.argv', ['error-group', str(log_file)]):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
        
        captured = capsys.readouterr()
        assert 'no errors' in captured.err.lower()

    def test_main_custom_threshold(self, tmp_path, capsys):
        log_file = tmp_path / "test.log"
        log_file.write_text(SAMPLE_LOG)
        
        with patch('sys.argv', ['error-group', str(log_file), '--threshold', '0.9']):
            main()
        
        captured = capsys.readouterr()
        assert 'error' in captured.out.lower()
