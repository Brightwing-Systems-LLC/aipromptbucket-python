# AI Prompt Bucket — Python SDK

Python SDK for [AI Prompt Bucket](https://aipromptbucket.com), a managed prompt registry for teams.

## Installation

```bash
pip install aipromptbucket
```

Or with uv:

```bash
uv add aipromptbucket
```

## Configuration

Set environment variables or pass directly to the client:

```bash
export AIPROMPTBUCKET_API_KEY="sk-api01-your-key-here"
export AIPROMPTBUCKET_URL="https://aipromptbucket.com"  # optional, this is the default
```

## Quick Start

```python
from aipromptbucket import Client

client = Client()

# List all prompts
result = client.list_prompts()
if result.ok:
    for prompt in result.data:
        print(f"{prompt.slug}: {prompt.name}")

# Get a specific prompt
result = client.get_prompt("my-prompt")
if result.ok:
    print(result.data.name)

# Render a prompt with variables
result = client.render("my-prompt", variables={"name": "World"})
if result.ok:
    print(result.data.rendered_text)

# Create a new prompt
result = client.create_prompt(
    name="Greeting Prompt",
    slug="greeting-prompt",
    template_text="Hello, {{ name }}! You are a {{ role }}.",
    template_format="jinja2",
    tags=["greetings"],
)

# Create a new version
result = client.create_version(
    "greeting-prompt",
    template_text="Hi {{ name }}! Your role is {{ role }}.",
    change_note="Simplified greeting",
)

# Promote a version to a label
result = client.promote("greeting-prompt", version=2, label="production")
```

## CLI Scanner

The package includes a CLI tool to scan your codebase for hardcoded prompts:

```bash
# Preview what the scanner finds
apb scan ./src --team my-team --dry-run

# Import all found prompts
apb scan ./src --team my-team --auto

# Interactive import
apb scan ./src --team my-team
```

### Scanner Flags

| Flag | Description |
|---|---|
| `<path>` | Directory to scan (required) |
| `--team <slug>` | Team slug to import into (required) |
| `--dry-run` | Show findings without importing |
| `--auto` | Import all without confirmation |
| `--min-length N` | Minimum string length (default: 100) |

## API Reference

All methods return `APIResponse[T]` with fields:
- `ok: bool` — whether the request succeeded
- `status_code: int` — HTTP status code
- `data: T | None` — response data (when `ok` is True)
- `error: str | None` — error message (when `ok` is False)

### Prompts

| Method | Description |
|---|---|
| `list_prompts(tag?, search?)` | List all prompts |
| `get_prompt(slug)` | Get prompt details |
| `create_prompt(...)` | Create a new prompt |
| `update_prompt(slug, ...)` | Update prompt metadata |
| `delete_prompt(slug)` | Delete a prompt |

### Versions

| Method | Description |
|---|---|
| `list_versions(slug)` | List all versions |
| `get_version(slug, version_number)` | Get specific version |
| `create_version(slug, ...)` | Create a new version |

### Rendering

| Method | Description |
|---|---|
| `render(slug, label?, variables?)` | Render a prompt template |

### Labels

| Method | Description |
|---|---|
| `list_labels()` | List team labels |
| `create_label(name, ...)` | Create a team label |
| `delete_label(name)` | Delete a team label |
| `list_prompt_labels(slug)` | List labels for a prompt |
| `assign_label(slug, label, version)` | Assign label to version |
| `label_impact(slug)` | Analyze change impact |

### Promote / Rollback

| Method | Description |
|---|---|
| `promote(slug, version, label)` | Assign label to a version |
| `rollback(slug, label)` | Rollback label to previous version |

### Snapshots

| Method | Description |
|---|---|
| `list_snapshots()` | List snapshots |
| `create_snapshot(name, ...)` | Create a snapshot |
| `restore_snapshot(snapshot_id)` | Restore a snapshot |

### Health & Analysis

| Method | Description |
|---|---|
| `get_health(slug)` | Get prompt health score |
| `refresh_health(slug)` | Recompute health score |
| `list_analysis(limit?)` | List analysis results |
| `run_analysis()` | Run new analysis |

### System

| Method | Description |
|---|---|
| `health_check()` | Check API health |

## Using the Scanner Programmatically

```python
from aipromptbucket import Scanner

scanner = Scanner(min_length=100)
findings = scanner.scan("./src")

for finding in findings:
    print(f"{finding.file}:{finding.line} — {finding.detected_format}")
    print(f"  Variables: {finding.variables}")
```

## License

MIT — Bright Wing Solutions LLC
