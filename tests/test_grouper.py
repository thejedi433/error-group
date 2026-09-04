"""Tests for ErrorGrouper."""

from error_group.grouper import ErrorGrouper


class TestNormalize:
    def test_removes_iso_timestamp(self):
        g = ErrorGrouper()
        result = g.normalize("2024-01-15T10:30:45.123Z Connection timeout after 5000ms")
        assert "2024" not in result
        assert "5000" not in result

    def test_removes_numbers(self):
        g = ErrorGrouper()
        result = g.normalize("Connection timeout after 5000ms on port 8080")
        assert "5000" not in result
        assert "8080" not in result
        assert "N" in result  # Numbers replaced with N

    def test_removes_uuids(self):
        g = ErrorGrouper()
        result = g.normalize("Request failed for 123e4567-e89b-12d3-a456-426614174000")
        assert "123e4567" not in result

    def test_collapses_whitespace(self):
        g = ErrorGrouper()
        result = g.normalize("Error:   too   many    spaces")
        assert result == "Error: too many spaces"


class TestSimilarity:
    def test_identical_strings(self):
        g = ErrorGrouper()
        assert g.similarity("same text", "same text") == 1.0

    def test_similar_strings(self):
        g = ErrorGrouper()
        ratio = g.similarity(
            "Connection timeout after N ms",
            "Connection timeout after N ms"
        )
        assert ratio == 1.0

    def test_different_strings(self):
        g = ErrorGrouper()
        ratio = g.similarity("completely different", "unrelated text here")
        assert ratio < 0.85


class TestGroup:
    def test_groups_similar_errors(self):
        g = ErrorGrouper(similarity_threshold=0.8)
        errors = [
            "ERROR Connection timeout after 5000ms on port 8080",
            "ERROR Connection timeout after 3000ms on port 8080",
            "ERROR Connection timeout after 10000ms on port 9090",
        ]
        groups = g.group(errors)
        summary = g.summary()
        
        assert len(summary) == 1
        assert summary[0]['count'] == 3

    def test_keeps_different_errors_separate(self):
        g = ErrorGrouper(similarity_threshold=0.8)
        errors = [
            "ERROR Connection timeout",
            "ERROR Database connection refused",
            "ERROR File not found",
        ]
        groups = g.group(errors)
        summary = g.summary()
        
        assert len(summary) == 3

    def test_empty_errors(self):
        g = ErrorGrouper()
        groups = g.group([])
        assert groups == {}

    def test_single_error(self):
        g = ErrorGrouper()
        errors = ["ERROR Something went wrong"]
        groups = g.group(errors)
        summary = g.summary()
        
        assert len(summary) == 1
        assert summary[0]['count'] == 1


class TestSummary:
    def test_summary_sorted_by_count(self):
        g = ErrorGrouper(similarity_threshold=0.5)
        errors = [
            "ERROR AAA",
            "ERROR BBB",
            "ERROR CCC",
            "ERROR AAA",  # duplicate of first
            "ERROR AAA",  # another duplicate
            "ERROR AAA",  # yet another
        ]
        g.group(errors)
        summary = g.summary()
        
        # First group should have highest count
        assert summary[0]['count'] >= summary[-1]['count']

    def test_summary_includes_examples(self):
        g = ErrorGrouper()
        errors = [
            "ERROR Connection timeout 1",
            "ERROR Connection timeout 2",
            "ERROR Connection timeout 3",
            "ERROR Connection timeout 4",
        ]
        g.group(errors)
        summary = g.summary()
        
        assert len(summary[0]['examples']) >= 1
