"""Fuzzy log error grouping and deduplication."""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional, Tuple


class ErrorGrouper:
    """Groups similar log errors using fuzzy matching."""
    
    def __init__(self, similarity_threshold=0.85):
        """Initialize with similarity threshold (0.0-1.0)."""
        self.similarity_threshold = similarity_threshold
        self.groups = defaultdict(list)
        self.patterns = []
        
    def normalize(self, text):
        """Remove variable parts from log line."""
        # Order matters: longer patterns first before generic number replacement
        
        # Remove timestamps (ISO 8601 with optional fractional seconds)
        text = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*', '', text)
        
        # Remove UUIDs (before number replacement)
        text = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'UUID', text, flags=re.IGNORECASE
        )
        
        # Remove hex strings (16+ chars)
        text = re.sub(r'\b[0-9a-f]{16,}\b', 'HEX', text, flags=re.IGNORECASE)
        
        # Remove numbers (including those attached to units like 5000ms, port:8080)
        text = re.sub(r'\d+\.?\d*', 'N', text)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_timestamp(self, text: str) -> Optional[datetime]:
        """Extract timestamp from log line if present."""
        # Try ISO 8601 formats
        patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)',
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                ts_str = match.group(1)
                # Try parsing with various formats
                for fmt in [
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%d %H:%M:%S',
                ]:
                    try:
                        # Remove timezone info for naive datetime comparison
                        clean_ts = re.sub(r'[+-]\d{2}:?\d{2}$', '', ts_str)
                        return datetime.strptime(clean_ts, fmt)
                    except ValueError:
                        continue
        return None
    
    def filter_by_time(self, errors: list, since: str) -> list:
        """Filter errors by time range.
        
        Args:
            errors: List of error strings
            since: Time range string (e.g., '1h', '30m', '1d', '2w')
        
        Returns:
            Filtered list of errors
        """
        # Parse time range
        match = re.match(r'^(\d+)([smhdw])$', since.lower())
        if not match:
            raise ValueError(f"Invalid time format: {since}. Use format like '1h', '30m', '1d'")
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        # Convert to timedelta
        unit_map = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
        delta = timedelta(**{unit_map[unit]: amount})
        
        cutoff: datetime = datetime.now() - delta
        
        # Filter errors
        filtered = []
        for error in errors:
            ts = self.extract_timestamp(error)
            if ts is None:
                # If no timestamp, include by default (backward compatibility)
                filtered.append(error)
            elif ts >= cutoff:
                filtered.append(error)
        
        return filtered
    
    def similarity(self, s1, s2):
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def group(self, errors):
        """Group similar errors together."""
        if not errors:
            return {}
        
        for error in errors:
            normalized = self.normalize(error)
            found_group = False
            
            # Check existing patterns
            for i, pattern in enumerate(self.patterns):
                if self.similarity(normalized, pattern) >= self.similarity_threshold:
                    self.groups[i].append(error)
                    found_group = True
                    break
            
            # Create new group if no match
            if not found_group:
                idx = len(self.patterns)
                self.patterns.append(normalized)
                self.groups[idx].append(error)
        
        return dict(self.groups)
    
    def summary(self):
        """Generate summary of grouped errors."""
        result = []
        for idx, pattern in enumerate(self.patterns):
            errors = self.groups[idx]
            result.append({
                'pattern': pattern,
                'count': len(errors),
                'examples': errors[:3]  # Show up to 3 examples
            })
        
        # Sort by count descending
        result.sort(key=lambda x: x['count'], reverse=True)
        return result
