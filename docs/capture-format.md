# Capture File Format

## Entry Structure

Each clipboard capture is appended as a timestamped entry:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT: notd
OWNER: Deze Tingz
TIMESTAMP: 2026-02-08 03:27:20
TYPE: text

<clipboard content here>
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Fields

| Field | Description |
|-------|-------------|
| **PROJECT** | Always `notd` |
| **OWNER** | Configured owner name |
| **TIMESTAMP** | Capture time in `YYYY-MM-DD HH:MM:SS` format |
| **TYPE** | Auto-detected content type: `url`, `command`, `code`, `error`, or `text` |

## Separator

The separator line uses Unicode character `U+2501` (Box Drawings Heavy Horizontal), repeated 26 times.

## File Routing

| Detected Type | Output File |
|---------------|-------------|
| `code` | `notd_raw.{code_file_type}` (default: `.md`) |
| `url`, `command`, `error`, `text` | `notd_raw.{text_file_type}` (default: `.txt`) |

## JSONL Mode

When the configured file type is `jsonl`, entries are written as single-line JSON objects instead:

```json
{"timestamp":"2026-02-08T03:27:20","type":"text","content":"clipboard content here"}
```

Each line is a complete JSON object, one capture per line.
