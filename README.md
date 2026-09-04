# error-group

Fuzzy log error grouping and deduplication CLI tool.

## What it does

Reads log files (or stdin), extracts error/warning lines, and groups similar errors using fuzzy matching. Instead of seeing the same error repeated 100 times with different numbers, you see one pattern with a count.

## Installation

```bash
pip install .
```

## Usage

```bash
# Analyze a log file
error-group app.log

# Analyze multiple files
error-group *.log

# Pipe from stdin
cat app.log | error-group

# JSON output
error-group app.log --json

# Adjust similarity threshold (0.0-1.0)
error-group app.log --threshold 0.9
```

## Example output

```
Found 7 errors grouped into 2 patterns:

[5x] ERROR Connection timeout after Nms
    Example 1: ERROR Connection timeout after 5000ms
    Example 2: ERROR Connection timeout after 3000ms
    Example 3: ERROR Connection timeout after 8000ms

[2x] ERROR Database connection refused
    Example 1: ERROR Database connection refused
    Example 2: ERROR Database connection refused on retry
```

## Why this tool?

- **Solves alert fatigue** — Groups similar errors so you see patterns, not duplicates
- **Lightweight** — No infrastructure, runs standalone
- **Pipeline-friendly** — Works with stdin/stdout, easy to compose with other tools
