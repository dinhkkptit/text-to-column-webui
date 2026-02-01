# CONTEXT_AI_PROMPT.md

This document defines the **recommended AI context prompt** when using
LLMs (ChatGPT, Claude, etc.) to assist with **text-to-column**
development, TextFSM templates, mappings, or troubleshooting.

Use this as a **system / context prompt** before asking task-specific
questions.

------------------------------------------------------------------------

## 🎯 Purpose

The goal of this prompt is to ensure the AI:

-   Understands the **project structure**
-   Respects **existing parsing logic**
-   Preserves **backward compatibility**
-   Follows the **batch parsing rules**
-   Does NOT invent new formats or break assumptions

------------------------------------------------------------------------

## 🧠 Recommended Context Prompt

Copy & paste the block below into your AI tool **before** asking
questions:

``` text
You are assisting with a project named "text-to-column".

This project:
- Parses network CLI output using TextFSM / ntc-templates
- Uses mapping.json to map command strings to TextFSM templates
- Supports platform aliases via config.json
- Applies longest-prefix command matching
- Outputs CSV or JSON

There are TWO batch output modes:
1) Per-file CSV (DEFAULT, backward compatible)
   - One CSV per input .txt file
   - No forced hostname column

2) Combined CSV (OPTIONAL)
   - Grouped by template
   - Injects a "hostname" column
   - Hostname is derived as the longest text after the command slug in filename
     Example:
       show_lb_vserver_netscaler1_L4_1.txt
       command = show lb vserver
       hostname = netscaler1_L4_1

Web UI details:
- Built with FastAPI + static HTML
- Batch mode is selected via a dropdown (default = Per-file CSV)
- Auto-detect mode tries all templates for a platform and selects the one
  producing the most rows

Strict rules:
- DO NOT remove or change Per-file CSV behavior
- DO NOT invent new filename conventions
- DO NOT expose template internals in the UI
- Changes must remain backward compatible
- Prefer minimal, isolated changes

When generating code:
- Reuse existing functions when possible
- Keep parsing logic in text_to_column/parser.py
- Keep Web logic in webapp/main.py
- Keep UI logic in webapp/static/index.html

Always ask for clarification if assumptions are unclear.
```

------------------------------------------------------------------------

## ✅ When to Use This Prompt

Use this context prompt when asking the AI to:

-   Add new batch features
-   Modify hostname extraction logic
-   Add new output formats
-   Extend Web UI behavior
-   Debug parsing mismatches
-   Generate new TextFSM templates
-   Refactor code while preserving behavior

------------------------------------------------------------------------

## ❌ What This Prompt Prevents

-   Breaking backward compatibility
-   Over-engineering solutions
-   Mixing UI logic with parsing logic
-   Incorrect hostname inference
-   Inconsistent batch behavior

------------------------------------------------------------------------

## 📌 Tip

For best results: 1) Paste this prompt first 2) Then paste **only the
relevant file or snippet** 3) Then ask your question clearly

This keeps AI responses accurate and aligned with project design.

------------------------------------------------------------------------

Maintained for **text-to-column Web UI v4.1**
