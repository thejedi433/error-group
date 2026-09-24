"""Tests for time filtering functionality."""

from datetime import datetime, timedelta
import pytest

from error_group.grouper import ErrorGrouper


class TestExtractTimestamp:
    def test_extracts_iso8601_zulu(self):
        g = ErrorGrouper()
        line = "2024-01-15T10:30:45Z ERROR Connection timeout"
        ts = g.extract_timestamp(line)
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert ts.hour == 10
        assert ts.minute == 30
        assert ts.second == 45

    def test_extracts_iso8601_fractional(self):
        g = ErrorGrouper()
        line = "2024-01-15T10:30:45.123Z ERROR Connection timeout"
        ts = g.extract_timestamp(line)
        assert ts is not None
        assert ts.microsecond == 123000

    def test_extracts_iso8601_with_timezone(self):
        g = ErrorGrouper()
        line = "2024-01-15T10:30:45+02:00 ERROR Connection timeout"
        ts = g.extract_timestamp(line)
        assert ts is not None
        # Timezone is stripped, returns naive datetime
        assert ts.year == 2024

    def test_extracts_space_separated(self):
        g = ErrorGrouper()
        line = "2024-01-15 10:30:45 ERROR Connection timeout"
        ts = g.extract_timestamp(line)
        assert ts is not None
        assert ts.year == 2024

    def test_returns_none_for_no_timestamp(self):
        g = ErrorGrouper()
        line = "ERROR Connection timeout without timestamp"
        ts = g.extract_timestamp(line)
        assert ts is None

    def test_returns_none_for_invalid_date(self):
        g = ErrorGrouper()
        line = "2024-13-45T99:99:99Z ERROR Invalid date"
        ts = g.extract_timestamp(line)
        assert ts is None


class TestFilterByTime:
    def test_filters_recent_errors(self):
        g = ErrorGrouper()
        now = datetime.now()
        
        errors = [
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Recent error 1",
            f"{(now - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Recent error 2",
            f"{(now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Old error",
            f"{(now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Very old error",
        ]
        
        filtered = g.filter_by_time(errors, "1h")
        assert len(filtered) == 2
        assert "Recent error 1" in filtered[0]
        assert "Recent error 2" in filtered[1]

    def test_includes_errors_without_timestamp(self):
        g = ErrorGrouper()
        
        errors = [
            "ERROR No timestamp here",
            f"{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR With timestamp",
        ]
        
        filtered = g.filter_by_time(errors, "1h")
        assert len(filtered) == 2

    def test_minutes_filter(self):
        g = ErrorGrouper()
        now = datetime.now()
        
        errors = [
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Just now",
            f"{(now - timedelta(minutes=15)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR 15 min ago",
            f"{(now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR 1 hour ago",
        ]
        
        filtered = g.filter_by_time(errors, "30m")
        assert len(filtered) == 2

    def test_days_filter(self):
        g = ErrorGrouper()
        now = datetime.now()
        
        errors = [
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Today",
            f"{(now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR Yesterday",
            f"{(now - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR 3 days ago",
        ]
        
        filtered = g.filter_by_time(errors, "2d")
        assert len(filtered) == 2

    def test_weeks_filter(self):
        g = ErrorGrouper()
        now = datetime.now()
        
        errors = [
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR This week",
            f"{(now - timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR 5 days ago",
            f"{(now - timedelta(weeks=2)).strftime('%Y-%m-%dT%H:%M:%SZ')} ERROR 2 weeks ago",
        ]
        
        filtered = g.filter_by_time(errors, "1w")
        assert len(filtered) == 2

    def test_invalid_format_raises_error(self):
        g = ErrorGrouper()
        with pytest.raises(ValueError, match="Invalid time format"):
            g.filter_by_time(["ERROR test"], "invalid")

    def test_empty_errors_list(self):
        g = ErrorGrouper()
        filtered = g.filter_by_time([], "1h")
        assert filtered == []

    def test_all_errors_filtered_out(self):
        g = ErrorGrouper()
        old_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        errors = [
            f"{old_date} ERROR Old error 1",
            f"{old_date} ERROR Old error 2",
        ]
        
        filtered = g.filter_by_time(errors, "1h")
        assert filtered == []
