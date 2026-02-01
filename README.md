# text-to-column

A **TextFSM / ntc-templates–based parser** that converts raw network device
CLI output into structured **JSON or CSV**, with both **CLI** and **Web UI**
interfaces.

---

## ✨ Features

- ✅ TextFSM-based parsing (deterministic, template-driven)
- ✅ Compatible with **ntc-templates** style
- ✅ CLI batch parsing (folder mode)
- ✅ Web UI (paste output, upload files)
- ✅ Auto-detect command/template
- ✅ CSV + JSON output
- ✅ Batch upload → ZIP result
- ✅ Docker support (one-command deployment)

---

## 📁 Repository Structure

```text
text-to-column/
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── README.md
├── CONTEXT_AI_PROMPT.md
│
├── config.json
├── mapping.json
│
├── templates/
│   └── *.textfsm
│
├── text_to_column/
│   └── parser.py
│
├── parse_to_csv.py
│
└── webapp/
    ├── main.py
    └── static/
        └── index.html
```

---

## 🔧 Configuration

### `mapping.json`

Maps **platform + command → TextFSM template**.

```json
{
  "cisco_ios": {
    "show ip interface brief": "cisco_ios_show_ip_interface_brief.textfsm"
  }
}
```

---

### `config.json`

Defines **platform aliases**, allowing flexible input names.

```json
{
  "platform_aliases": {
    "ios": "cisco_ios",
    "cisco": "cisco_ios"
  }
}
```

---

## 🧠 How Parsing Works

1. Resolve platform (apply alias if needed)
2. Resolve command:
   - Exact match preferred
   - Longest-prefix match supported
3. Load the corresponding TextFSM template
4. Parse raw CLI output
5. Produce structured data:
   - JSON (API / UI)
   - CSV (downloadable)

---

## 🖥️ Web UI Usage

### Run locally

```bash
pip install -r requirements.txt
uvicorn webapp.main:app --reload
```

Open in browser:

```
http://127.0.0.1:8000
```

### Web UI capabilities

- Select platform
- Select command **or enable auto-detect**
- Paste raw CLI output
- Upload multiple `.txt` files
- Download CSV or ZIP

---

## 🔁 CLI Usage (Batch Mode)

```bash
python parse_to_csv.py   --platform ios   --input files/ios   --output out/
```

- Each `.txt` file → one CSV
- Errors are reported per file

---

## 🧪 API Overview

### Parse single output

**POST** `/api/parse`

```json
{
  "platform": "ios",
  "command": "show ip interface brief",
  "text": "raw cli output",
  "output": "json",
  "autodetect": false
}
```

---

### Auto-detect command/template

**POST** `/api/autodetect`

```json
{
  "platform": "ios",
  "text": "raw cli output"
}
```

---

### Batch parse

**POST** `/api/batch_parse`

- `multipart/form-data`
- Upload one or more `.txt` files
- Returns ZIP (CSV files + summary.json)

---

## 🐳 Docker Deployment

### Build image

```bash
docker build -t text-to-column .
```

### Run container

```bash
docker run -p 8000:8000 text-to-column
```

---

## 🧩 Adding a New Command

1. Create a `.textfsm` template
2. Place it in `templates/`
3. Register it in `mapping.json`
4. (Optional) Add example CLI output

---

## 🛡️ Design Principles

- Deterministic parsing (no AI guessing)
- Explicit TextFSM templates
- Safe failure modes
- Shared core logic (CLI + Web UI)

---

## 📌 Roadmap

- Unit tests
- Combined CSV output for batch mode
- Template scoring UI
- ntc-templates auto-sync
- Authentication for Web UI

---

## 📜 License

MIT (or your preferred license)
