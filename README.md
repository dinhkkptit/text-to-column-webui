# text-to-column (Web UI)

A **TextFSM / ntc-templates based parser** that converts network CLI
output into structured **CSV / JSON**, supporting:

-   CLI batch parsing (original behavior)
-   Web UI for interactive parsing
-   Auto-detect command/template
-   Batch upload with **Per-file CSV (default)** or **Combined CSV
    (optional)**
-   Docker one-command deployment

------------------------------------------------------------------------

## ✨ Features

### Core

-   Uses **TextFSM**
-   Mapping-driven command → template resolution
-   Longest-prefix command matching
-   Platform alias support (`ios` → `cisco_ios`, etc.)

### Web UI

-   Platform dropdown
-   Command dropdown
-   Auto-detect mode
-   Paste CLI output → parse → table / JSON
-   Upload `.txt` files for batch parsing
-   Download CSV or ZIP results

### Batch Modes

-   **Per-file CSV** (default, backward compatible)
-   **Combined CSV** (grouped by template, hostname injected)

------------------------------------------------------------------------

## 📂 Repository Structure

    .
    ├─ text_to_column/
    │  ├─ parser.py
    │  └─ config.py
    ├─ webapp/
    │  ├─ main.py
    │  └─ static/index.html
    ├─ templates/
    ├─ files/
    ├─ mapping.json
    ├─ config.json
    ├─ parse_to_csv.py
    ├─ requirements.txt
    └─ Dockerfile

------------------------------------------------------------------------

## ⚙️ Configuration

### mapping.json

``` json
{
  "cisco_ios": {
    "show ip interface brief": "cisco_ios_show_ip_interface_brief.textfsm"
  }
}
```

### config.json

``` json
{
  "platform_aliases": {
    "ios": "cisco_ios"
  }
}
```

------------------------------------------------------------------------

## 🚀 Run Locally

``` bash
pip install -r requirements.txt
uvicorn webapp.main:app --reload
```

Open: http://127.0.0.1:8000

------------------------------------------------------------------------

## 🐳 Run with Docker

``` bash
docker build -t text-to-column .
docker run --rm -p 8000:8000 -v "$(pwd)":/app text-to-column
```

------------------------------------------------------------------------

## 📦 Batch Parse

### Per-file CSV (Default)

Upload:

    r1.txt
    r2.txt

Output ZIP:

    r1.csv
    r2.csv
    summary.json

------------------------------------------------------------------------

### Combined CSV (Optional)

Upload:

    show_ip_interface_brief_r1.txt
    show_ip_interface_brief_r2.txt

Output ZIP:

    cisco_ios_show_ip_interface_brief.csv
    summary.json

CSV example:

``` csv
hostname,interface,ip_address,status,protocol
r1,Gi0/0,10.0.0.1,up,up
r2,Gi0/0,10.0.0.2,up,up
```

------------------------------------------------------------------------

## 🏷️ Hostname Extraction (Combined Mode)

**Rule:** longest text after command slug

Example:

    show_lb_vserver_netscaler1_L4_1.txt

→ hostname = `netscaler1_L4_1`

------------------------------------------------------------------------

## 🤖 Auto-detect Mode

-   Tries all templates for selected platform
-   Picks the template with the most parsed rows

------------------------------------------------------------------------

## 🧾 CLI Usage (Original)

``` bash
python parse_to_csv.py
```

Fully backward compatible.

------------------------------------------------------------------------

## ✅ Status

-   Stable
-   Backward compatible
-   Production-ready
