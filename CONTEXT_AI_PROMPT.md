# Context for AI Assistants – text-to-column

You are working with the repository **text-to-column**.

This project parses raw network device CLI output into structured data
(JSON / CSV) using **TextFSM** templates (ntc-templates style).

## High-level goals

- Convert unstructured CLI text into tabular data
- Support Cisco IOS, Juniper JunOS, and other network platforms
- Allow both:
  - CLI-based parsing (batch folder mode)
  - Web UI parsing (paste text / upload files)
- Be deterministic and template-driven (NO regex guessing without templates)

## Core technologies

- Python 3
- TextFSM (google/textfsm)
- ntc-templates-style templates
- FastAPI (Web API)
- CSV + JSON outputs
- Docker for deployment

## Repository structure (important)

- `mapping.json`
  - Maps **platform → command → TextFSM template**
- `config.json`
  - Defines platform aliases (e.g. ios → cisco_ios)
- `templates/`
  - Contains `.textfsm` templates
- `text_to_column/parser.py`
  - Core parsing logic
  - Must remain reusable by CLI and Web UI
- `parse_to_csv.py`
  - CLI wrapper (batch mode)
- `webapp/`
  - FastAPI backend
  - Static Web UI

## Parsing rules (do NOT break these)

1. Parsing MUST use TextFSM templates
2. Command resolution:
   - Exact match preferred
   - Longest-prefix match allowed
3. Platform resolution:
   - Folder/platform name may be aliased via `config.json`
4. Headers:
   - Always lowercase
   - Underscore-separated
5. Output rows:
   - List of dictionaries (header → value)
6. Never silently swallow parse errors
   - Always return a useful error message

## Auto-detect behavior

When auto-detect is enabled:
- Try all templates for the selected platform
- Select the template that produces:
  - The highest row count
  - Non-empty structured output
- If no template matches, return a clear error

## Batch parsing rules

- Accept multiple `.txt` files
- Each file parsed independently
- Output:
  - Per-file CSV
  - `summary.json` describing success/failure

## What AI should help with

- Adding new templates
- Improving error handling
- Enhancing Web UI features
- Writing tests
- Optimizing performance safely

## What AI should NOT do

- Do NOT invent parsing logic without TextFSM templates
- Do NOT hardcode vendor-specific assumptions
- Do NOT break existing CLI behavior when adding Web features

End of context.
