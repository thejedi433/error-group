"""Error grouping CLI."""

import argparse
import json
import re
import sys
from pathlib import Path
from .grouper import ErrorGrouper


def extract_errors(lines):
    """Extract error/warning lines from log input."""
    error_pattern = re.compile(r'\b(ERROR|CRITICAL|FATAL|WARN|WARNING)\b', re.IGNORECASE)
    return [line for line in lines if error_pattern.search(line)]


def read_input(files):
    """Read from files or stdin."""
    lines = []
    if files:
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    lines.extend(f.readlines())
            except FileNotFoundError:
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("Reading from stdin (Ctrl+D to end)...", file=sys.stderr)
        lines = sys.stdin.readlines()
    return lines


def format_text_summary(summary):
    """Format summary as human-readable text."""
    output = []
    total = sum(g['count'] for g in summary)
    
    output.append(f"Found {total} error(s) grouped into {len(summary)} pattern(s):\n")
    
    for i, group in enumerate(summary, 1):
        output.append(f"[{group['count']}x] {group['pattern']}")
        for j, example in enumerate(group['examples'], 1):
            output.append(f"    Example {j}: {example.strip()}")
        output.append("")
    
    return "\n".join(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fuzzy log error grouping and deduplication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  error-group app.log
  error-group *.log
  cat app.log | error-group
  error-group app.log --json
  error-group app.log --threshold 0.9
        """
    )
    
    parser.add_argument('files', nargs='*', help='Log files to analyze (reads stdin if omitted)')
    parser.add_argument('--threshold', type=float, default=0.85,
                       help='Similarity threshold for grouping (0.0-1.0, default: 0.85)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Read input
    lines = read_input(args.files)
    
    # Extract errors
    errors = extract_errors(lines)
    
    if not errors:
        print("No errors found in input.", file=sys.stderr)
        sys.exit(0)
    
    # Group errors
    grouper = ErrorGrouper(similarity_threshold=args.threshold)
    grouper.group(errors)
    
    # Generate summary
    summary = grouper.summary()
    
    # Output results
    if args.json:
        output = {
            'total_errors': sum(g['count'] for g in summary),
            'unique_patterns': len(summary),
            'groups': summary
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_text_summary(summary))


if __name__ == '__main__':
    main()
