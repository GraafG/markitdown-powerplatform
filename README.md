# 📄➡️📝 Power Platform MarkItDown Function

> Turn **PDF** and **Word** files into clean **Markdown** from
> Power Automate, Power Apps, or any HTTP client.

A small, self-hostable **Azure Function** (Python) that wraps Microsoft's
[markitdown](https://github.com/microsoft/markitdown) library. You send it a document, it sends
back readable text. That's it.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Why would I want this?

In **Power Automate / Power Apps**, when you grab a file from SharePoint or OneDrive with
*"Get file content"*, you get the raw **binary blob** — not the text inside it. There is
**no built-in, free action that reliably turns a PDF *or* a Word file into clean text** that
you can feed to a flow, a prompt, or a search index:

| Format | Built into Power Automate? | Reality |
|--------|---------------------------|---------|
| **DOCX** | ❌ Not for text | The native **Word Online (Business)** connector has **no text/Markdown extraction action** — its only conversion is *Word → PDF* (`Convert Word Document to PDF`), which gives you another **binary blob**, not text. |
| **PDF** | ❌ No | No built-in free option. You need **AI Builder** (premium, consumes credits) or a **third‑party premium connector** (Encodian, Muhimbi, PDF.co…). |

> **We checked.** SharePoint **Get file content** returns the file bytes, not readable text. Word
> Online can convert DOCX→PDF, but that still gives you another binary blob. There is genuinely no
> native action that returns the text inside a Word or PDF file. The demo flow in
> [`flows/sharepoint-folder-demo.json`](flows/sharepoint-folder-demo.json) shows the practical
> workaround using visible SharePoint connector actions: **Get files (properties only)** reads a
> SharePoint document library/folder, **Get file content** downloads each supported file, and the
> function converts only `.pdf`/`.docx` to Markdown.

This project gives you **one endpoint that handles both PDF and DOCX**, returns **structured
Markdown** (so tables, headings and lists survive), runs on **your own Azure subscription**
(your data stays in your tenant), and costs essentially just Azure compute.

**Use it when you want to:**

- Extract text from PDFs/Word docs inside a flow without buying a premium PDF connector
- Get *Markdown* (not messy plain text) to feed into AI prompts, search, or storage
- Keep document processing inside your own Azure tenant for privacy/compliance

---

## How it works

```
┌──────────────┐   file bytes    ┌─────────────────────┐   Markdown    ┌──────────────┐
│ Power Automate│ ─────────────▶ │  Azure Function      │ ───────────▶ │ Your flow /  │
│  / Power Apps │   (base64)      │  /api/convert        │              │ app / prompt │
└──────────────┘                 │  (markitdown)        │              └──────────────┘
                                  └─────────────────────┘
```

---

## About markitdown (and why Markdown)

This function is a thin, Power-Platform-friendly wrapper around
**[microsoft/markitdown](https://github.com/microsoft/markitdown)** — a lightweight, open-source
Python utility from Microsoft for converting many file types into Markdown, specifically for
feeding **LLMs and text-analysis pipelines**.

**Why markitdown?**

- **It preserves structure.** Unlike a raw "dump the text" extractor, markitdown keeps
  headings, lists, tables, and links as Markdown — so the meaning survives, not just the words.
- **Markdown is what LLMs "speak".** Models like GPT-4o are trained on huge amounts of
  Markdown, understand it natively, and it's very **token-efficient** — cheaper prompts.
- **It's one library for many formats** (see the matrix below), so you don't wire up a
  different tool per file type.
- **It runs locally/offline** for the common office formats — no per-document cloud charge for
  the conversion itself, and your document bytes never leave your Azure tenant.

**How markitdown is configured.** markitdown activates file formats through **optional
dependency "extras"** at install time. You only pull in what you need, e.g.:

```bash
pip install "markitdown[pdf, docx, pptx]"   # only these formats
pip install "markitdown[all]"               # everything
```

This project installs just `markitdown[docx,pdf]` (see [`src/requirements.txt`](src/requirements.txt))
because PDF + Word cover the Power Platform use case while keeping the deployment small.

### Configuring which formats *this function* accepts

Two layers control what gets converted:

1. **What's installed** — the extras in `requirements.txt` (`markitdown[docx,pdf]`).
2. **What the function allow-lists** — the `SUPPORTED_EXTENSIONS` set in
   [`src/function_app.py`](src/function_app.py):

   ```python
   SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
   ```

   The allow-list is a deliberate safety boundary: even if a dependency *could* parse another
   type, the endpoint rejects anything not explicitly listed (returns `415`). **To add a
   format**, install its extra *and* add the extension here. For example, to add PowerPoint and
   Excel:

   ```text
   # requirements.txt
   markitdown[docx,pdf,pptx,xlsx]
   ```
   ```python
   # function_app.py
   SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}
   ```

### Format support matrix (on an Azure Function)

markitdown supports many formats, but **not all of them are a good fit for a serverless Azure
Function**. The Linux Consumption / Flex Consumption host runs your Python with **no system
binaries** (no `ffmpeg`, no LibreOffice) and is meant for short, in-process work. The table
below maps markitdown's formats to how well they work here.

| Format | markitdown extra | Works on Azure Function? | Notes |
|--------|------------------|--------------------------|-------|
| **PDF** (text-based) | `[pdf]` | ✅ Yes | Pure-Python (`pdfminer.six`). **Enabled here.** Scanned/image PDFs need OCR — see below. |
| **Word `.docx`** | `[docx]` | ✅ Yes | Pure-Python (`mammoth`/`python-docx`). **Enabled here.** |
| Word `.doc` (legacy) | — | ❌ No | Binary `.doc` is unsupported by markitdown (needs LibreOffice). Convert to `.docx` first. |
| **PowerPoint `.pptx`** | `[pptx]` | ✅ Yes | Pure-Python (`python-pptx`). Just add the extra + extension. |
| **Excel `.xlsx`** | `[xlsx]` | ✅ Yes | Pure-Python (`openpyxl`). |
| Excel `.xls` (legacy) | `[xls]` | ✅ Yes | Pure-Python (`xlrd`). |
| **HTML** | (built-in) | ✅ Yes | Pure-Python (`beautifulsoup4`). |
| **CSV / JSON / XML** | (built-in) | ✅ Yes | Standard library / pure-Python. |
| **ZIP** (iterates contents) | (built-in) | ✅ Yes | Converts each supported file inside. |
| **EPub** | (built-in) | ✅ Yes | Pure-Python. |
| **Outlook `.msg`** | `[outlook]` | ✅ Yes | Pure-Python (`extract-msg`). |
| Images — EXIF metadata | (built-in) | ✅ Yes | Reads metadata only. |
| Images — **OCR / text** | — | ⚠️ Needs a service | No local OCR. Requires an **LLM client** (e.g. Azure OpenAI vision) or **Azure Document Intelligence** / **Content Understanding**. Works, but it's an external, billable call. |
| Scanned PDFs (OCR) | `[az-doc-intel]` / `[az-content-understanding]` | ⚠️ Needs a service | Same as above — route via Azure Document Intelligence / Content Understanding. |
| **Audio** (transcription) | `[audio-transcription]` | ❌ Not by default | Needs the **`ffmpeg`** system binary, which isn't present on Consumption/Flex. Would require a **custom container** image. |
| **YouTube URLs** | `[youtube-transcription]` | ⚠️ Possible | Pure-Python, but depends on outbound network and YouTube not blocking the datacentre IP. Not a typical Power Platform need. |
| Azure Document Intelligence | `[az-doc-intel]` | ✅ With setup | Higher-quality cloud extraction; billable, needs endpoint + credentials. |
| Azure Content Understanding | `[az-content-understanding]` | ✅ With setup | Multimodal (incl. audio/video) + structured fields; billable, needs endpoint. |

**Rule of thumb:** pure-Python formats (PDF, Office docs, HTML, text, ZIP, EPub, MSG) run great
on the function. Anything needing a **system binary** (audio→`ffmpeg`) needs a **custom
container**; anything needing **OCR** needs an **external Azure AI service**.

### OCR: images inside PDFs and Word files

A common question: *does this extract text from **images** embedded in documents (scans,
screenshots, photos of text)?*

**Short answer: not by default — and that's true for both PDF and DOCX.**

- The built-in **PDF** converter (`pdfminer.six`) only reads the document's **text layer**. A
  **scanned/image-only PDF** has no text layer, so you'll get little or nothing back.
- The built-in **DOCX** converter reads the document's text, lists and tables but **does not OCR
  pictures** embedded in the Word file. Image content is ignored (aside from alt-text if present).
- markitdown's image handling on its own is **EXIF metadata + optional AI captioning**, *not*
  true OCR.

If you need text **out of images** (in PDF, DOCX, PPTX or XLSX), you add an OCR backend. Two
supported routes, neither requiring a system binary:

| Option | What it does | How to enable | Trade-off |
|--------|--------------|---------------|-----------|
| **Azure Document Intelligence** | True OCR for scanned PDFs & images (layout-aware) | `pip install "markitdown[az-doc-intel]"` and construct `MarkItDown(docintel_endpoint="https://<resource>.cognitiveservices.azure.com/")` | Best for **scanned PDFs**; billable Azure service + endpoint/credentials |
| **`markitdown-ocr` plugin (LLM vision)** | OCRs **embedded images inside** PDF/DOCX/PPTX/XLSX using a vision model | `pip install markitdown-ocr` + `MarkItDown(enable_plugins=True, llm_client=<OpenAI>, llm_model="gpt-4o")` | Best for **pictures embedded in Office docs**; needs a vision-capable LLM (billable) |

> This repo ships **without** OCR to stay small, fast, and fully offline for the common case
> (digital PDFs and Word docs). OCR is an **opt-in** you can wire in when a real scanned-document
> need appears. If you want, the function can be extended to enable Document Intelligence behind
> an env var (e.g. `DOCINTEL_ENDPOINT`) so OCR turns on automatically when configured — open an
> issue and we can add it.

---

## Comparison: native vs this function

To make the "why" concrete, the repo includes a SharePoint folder demo flow:

- **[`flows/sharepoint-folder-demo.json`](flows/sharepoint-folder-demo.json)** — uses SharePoint
  **Get files (properties only)** against a document library/folder, filters to `.pdf`/`.docx`, uses
  SharePoint **Get file content** for each supported file's bytes, sends those bytes to
  `/api/convert`, and returns Markdown plus a skipped-file list.

The outcome (verified end-to-end):

| | Native Power Automate | This MarkItDown function |
|---|---|---|
| **DOCX → text** | ❌ No action returns text | ✅ Clean Markdown |
| **Best the native connector can do** | File bytes / base64 blob (or DOCX → PDF, still a blob) | DOCX/PDF → **structured Markdown** |
| **PDF → text** | ❌ Needs premium AI Builder / 3rd-party | ✅ Clean Markdown |
| **Structure (headings/tables/lists)** | Lost | Preserved |
| **Where data goes** | Microsoft 365 service | Your own Azure tenant |
| **Licensing/cost** | Premium connector or AI Builder credits | Azure compute (~$0 light use) |

In a live run, the native path returns unreadable base64/binary bytes (a DOCX is a ZIP — the blob
even starts with the `PK` zip signature), while the function returns:

```markdown
MarkItDown Test

# Section One

Hello from a real .docx file.

* Bullet A
* Bullet B

|  |  |
| --- | --- |
| Name | Value |
| Answer | 42 |
```

---

## 🚀 Deploy it (step by step)

**New to Azure? No problem.** Follow these in order. Total time: ~10 minutes.

### 1. Install the tools (one-time)

| Tool | What it's for | Install |
|------|---------------|---------|
| **Azure CLI** (`az`) | Talk to Azure | <https://learn.microsoft.com/cli/azure/install-azure-cli> |
| **Azure Functions Core Tools v4** (`func`) | Publish the function | <https://learn.microsoft.com/azure/azure-functions/functions-run-local> |

Check they work:

```bash
az version
func --version   # should start with 4
```

### 2. Sign in and pick your subscription

```bash
az login
az account set --subscription "<your-subscription-name-or-id>"
```

### 3. Create the Azure resources

Copy-paste this block. **Change `APP` to something globally unique** (lowercase letters/numbers).

```bash
# --- choose your names ---
RG=rg-markitdown                 # resource group
LOCATION=westeurope              # any Azure region
APP=markitdown-$RANDOM           # MUST be globally unique -> your function URL
STORAGE=mdstor$RANDOM            # 3-24 lowercase letters/numbers, globally unique

# --- create everything ---
az group create -n $RG -l $LOCATION

az storage account create -n $STORAGE -g $RG -l $LOCATION --sku Standard_LRS

az functionapp create \
  -n $APP -g $RG \
  --storage-account $STORAGE \
  --flexconsumption-location $LOCATION \
  --runtime python --runtime-version 3.11 \
  --functions-version 4

echo "Your function will be: https://$APP.azurewebsites.net"
```

> **Why Flex Consumption?** It doesn't need a classic storage file share, so it works even in
> tenants that disable shared-key storage access (a common security policy). It's also
> pay-per-execution.

### 4. Publish the code

```bash
# the function app lives in src/
cd src
func azure functionapp publish $APP --build remote --python
cd ..
```

When it finishes you'll see your endpoints printed:
`/api/convert`, `/api/health`.

### 5. Grab your function key (needed to call it)

```bash
az functionapp keys list -n $APP -g $RG --query "functionKeys.default" -o tsv
```

Your convert URL is:
`https://<APP>.azurewebsites.net/api/convert?code=<that-key>`

### 6. (Recommended) Lock it down to Power Platform + Entra ID

By default the endpoints are protected by a **function key** (`?code=`). For production add an
identity layer (and, optionally, a network layer). **Entra ID is the reliable lock**; the network
restriction is genuinely fiddly with Power Automate — see **[SECURITY.md](SECURITY.md)** for the
full commands and caveats.

**Layer B — require an Entra ID token (recommended primary control):**

1. In the portal: **Function App → Settings → Authentication → Add identity provider →
   Microsoft**. Create (or pick) an app registration, and set **"Restrict access: Require
   authentication"** with **"Unauthenticated requests: HTTP 401"**.
2. In your flow, keep the function key in the URL (`?code=<key>`) **and** add an Entra token:
   use the **HTTP** action with **Authentication = Active Directory OAuth** (Tenant,
   Audience = `api://<appId>`, plus a client ID/secret) — or wrap the function in a
   **custom connector** configured with **Microsoft Entra ID (OAuth 2.0)**.

With Layer B in place a caller needs **both** a valid function key **and** a valid Entra token —
the request is rejected (`401`) if either is missing. (The function stays at `AuthLevel.FUNCTION`,
so a basic key-only deployment is still protected; Layer B is additive, not a replacement.)

**Layer A — restrict the network to Power Platform (optional, defense-in-depth):**

```bash
# Europe example — allow-list the REGION-SPECIFIC connector tags (the generic one is NOT enough)
az functionapp config access-restriction add -g $RG -n $APP \
  --rule-name AllowPP-WE --action Allow --priority 100 --service-tag AzureConnectors.WestEurope
az functionapp config access-restriction add -g $RG -n $APP \
  --rule-name AllowPP-NE --action Allow --priority 101 --service-tag AzureConnectors.NorthEurope
```

> ⚠️ The **raw HTTP action** can egress from Azure Logic Apps IPs that aren't in these tags, so it
> may be blocked even when the tags are allowed. To keep Layer A and your flow working together,
> call the function through a **custom connector** (its traffic stays in the connector network).
> Full details and the reasoning are in [SECURITY.md](SECURITY.md).

### Alternative: one-click "Deploy to Azure" button

> ⚠️ The button requires this repo to be **public** (Azure pulls the code anonymously). If
> your repo is private, use the CLI steps above. The ARM template sets `PROJECT=src` so Azure
> deploys the function from the `src/` subfolder.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FGraafG%2Fpowerplatform-markitdown-function%2Fmain%2Finfra%2Fazuredeploy.json)

---

## 🧪 Usage

### Convert a document

`POST /api/convert?code=<functionKey>`

```json
{ "content": "<base64-encoded file bytes>", "filename": "report.pdf" }
```

Returns **`text/markdown`**. Supported: `.pdf`, `.docx`.

Status codes:

| Status | Meaning |
|--------|---------|
| `200` | Conversion succeeded; body is Markdown |
| `400` | Invalid JSON, missing base64 content, invalid base64, or file too large |
| `401` | Missing/invalid function key or Entra ID token (when Easy Auth is enabled) |
| `415` | Unsupported file type (for example `.doc`, `.pptx`, or missing extension) |
| `500` | Conversion failed inside the parser — including **encrypted/password-protected** `.pdf`/`.docx` files (the extension is valid, so they pass the 415 check, but the parser cannot read the protected bytes); use the returned correlation id to find logs |

### Known limits

- **Default file size limit:** `10 MiB` decoded file bytes. Override with the Function App setting
  `MAX_FILE_BYTES` if your plan has enough memory/time headroom.
- **Base64 overhead:** the JSON request is about 33% larger than the original file, so a 10 MiB file
  becomes roughly 13.3 MiB before JSON/HTTP overhead.
- **Timeouts/memory:** large PDFs and complex DOCX files take longer and use more memory. For big
  batches, keep the Power Automate loop concurrency low and consider a larger Function plan.
- **No OCR by default:** scanned PDFs and images embedded in DOCX/PDF are not read unless you add an
  OCR backend (see [OCR](#ocr-images-inside-pdfs-and-word-files)).
- **Encrypted/protected files:** password-protected PDFs/DOCX files, Microsoft Purview
  sensitivity-label encryption, IRM/RMS-protected files, or similar document-protection wrappers
  are not supported. The function receives the protected file bytes from SharePoint; it does not run
  as the viewing user and cannot unwrap Microsoft 365 protection. Decrypt or export an unprotected
  copy before calling the function.
- **Legacy `.doc`:** not supported. Convert `.doc` to `.docx` first.
- **Demo output files accumulate:** the demo flow writes each converted Markdown back into the same
  SharePoint folder as `<originalName>-yyyyMMdd-HHmmss.md`. These outputs build up over repeated runs;
  they are safely skipped on later runs (the flow only converts `.pdf`/`.docx`). Point the flow at a
  dedicated output folder or prune old `.md` files if you want to keep the source folder clean.

Quick test with `curl` (PowerShell example encodes a local file):

```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("report.pdf"))
$body = @{ content = $b64; filename = "report.pdf" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://<APP>.azurewebsites.net/api/convert?code=<key>" `
  -ContentType "application/json" -Body $body
```

> **Note:** legacy binary **`.doc`** is *not* supported — markitdown reads Word via
> `python-docx`, which only handles modern `.docx`. Convert `.doc` → `.docx` first.

### Health check

`GET /api/health` → `ok` (anonymous, no key).

### Use it from Power Automate

Ready-to-adapt flow templates live in [`flows/`](flows/):

- **`flows/sharepoint-folder-demo.json`** — demo flow: PowerApps (V2) trigger → SharePoint
  **Get all lists** to resolve the library display name to its ID → SharePoint
  **Get files (properties only)** for that library/folder → filter to `.pdf`/`.docx` →
  SharePoint **Get file content** by SharePoint identifier → HTTP `/api/convert` → SharePoint
  **Create file** to write each Markdown result back into the same folder with a datetimestamped
  `<originalName>-yyyyMMdd-HHmmss.md` name → respond with converted Markdown and skipped
  unsupported files.

Minimum demo setup:

1. Create a SharePoint folder, for example `Shared Documents/MarkItDown Demo`.
2. Upload at least one `.pdf` and one `.docx`. Add a `.doc` only if you want to show it being skipped.
3. In Power Automate, import or recreate `flows/sharepoint-folder-demo.json`.
4. Create/select a **SharePoint Online** connection.
5. Set the PowerApps inputs:
   - `SiteAddress`: `https://<tenant>.sharepoint.com/sites/<site>`
   - `LibraryName`: the document library **display name** as shown in SharePoint, for example `Documents` (the flow resolves it to the library ID automatically; do not use the URL segment `Shared Documents`)
   - `FolderPath`: the path inside that library, for example `MarkItDown Demo`
   - `FunctionUrlWithKey`: `https://<APP>.azurewebsites.net/api/convert?code=<functionKey>`
6. Run it. The response echoes `SharePointSite`, `SharePointLibrary`, and `SharePointFolder`, then
   returns `Converted[]` entries with `fileName`, `sharePointIdentifier`, `sharePointPath`,
   `markdownFileName` (the timestamped `.md` written back to SharePoint), `markdownPath`, and
   `markdown`, plus `Skipped[]` entries for unsupported files such as `.doc`. Each converted file
   is also saved into the same SharePoint folder as `<originalName>-yyyyMMdd-HHmmss.md`. Those saved
   `.md` files are skipped on later runs because the filter only matches `.pdf`/`.docx`.

The easiest long-term setup is to **import `connector/openapi.json` as a custom connector** (~5 minutes),
so `Convert` shows up as a normal Power Automate action instead of a raw HTTP call. If you enable
Entra ID Easy Auth, use [`connector/openapi-entra.json`](connector/openapi-entra.json) as the reference
variant and keep the function key query parameter too.

> **SharePoint site:** the templates don't hard-code a site — `SiteAddress` is an input. Point it at
> whichever site/library holds your `.pdf`/`.docx` files.

---

## 🔒 Security

A short version is here; the full policy and hardening checklist is in
**[SECURITY.md](SECURITY.md)**.

- **Keys:** `/api/convert` requires a **function key** (`?code=`). `/api/health` is anonymous
  and returns no data.
- **Lock to Power Platform:** an **Access Restriction** can limit inbound traffic, but use the
  **region-specific** connector tags (e.g. `AzureConnectors.WestEurope` **and**
  `AzureConnectors.NorthEurope` for Europe) — the generic `AzureConnectors` tag isn't enough, and
  the raw HTTP action may still be blocked (use a custom connector). See [SECURITY.md](SECURITY.md).
- **Identity layer (recommended):** enable **Entra ID (Easy Auth)** and call via **Active
  Directory OAuth** from the HTTP action or a **custom connector**. This is *additive* to the
  function key — with it on, a caller needs **both** a valid token **and** the key.
- **No secrets in the repo.** Keys and endpoints live in Azure app settings, never in source.
- **No data is stored.** Documents are converted in a temp file that is deleted immediately
  after; nothing is persisted by the function.
- **Found a vulnerability?** Please report it privately — see [SECURITY.md](SECURITY.md). Do
  **not** open a public issue.

---

## 💸 Cost

- **Function (Flex Consumption):** pay-per-execution — effectively ~$0 for light use.
- **Storage + Application Insights:** a few cents/month.
- **Power Automate:** the HTTP action is premium → needs a Power Automate Premium license.

---

## 🗂️ What's in this repo

```
.
├── src/                  # the Azure Function (deploy from here)
│   ├── function_app.py
│   ├── requirements.txt
│   ├── host.json
│   └── .funcignore
├── infra/                # infrastructure
│   └── azuredeploy.json  # ARM template
├── connector/            # Power Platform custom connector
│   ├── openapi.json      # OpenAPI/Swagger spec
│   └── openapi-entra.json # OpenAPI variant for function key + Entra ID
├── flows/                # example Power Automate flow templates
│   └── sharepoint-folder-demo.json
├── tests/                # minimal unit tests
├── .github/workflows/    # CI
├── requirements-dev.txt
├── README.md
├── TEST-STATUS.md        # documented vs. actually verified
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── LICENSE
```

| Path | Purpose |
|------|---------|
| `src/function_app.py` | The Azure Function (`/api/convert`, `/api/health`) |
| `src/requirements.txt` | Python deps (`azure-functions`, `markitdown[docx,pdf]`) |
| `src/host.json` | Functions host config |
| `infra/azuredeploy.json` | ARM template (infrastructure) |
| `connector/openapi.json` | OpenAPI/Swagger spec — function-key-only custom connector |
| `connector/openapi-entra.json` | OpenAPI variant for function key + Entra ID Easy Auth |
| `flows/sharepoint-folder-demo.json` | SharePoint folder loop demo flow |
| `TEST-STATUS.md` | Which documented behaviours are verified vs. unit-tested vs. untested |
| `tests/` | Minimal Python tests |

---

## 🤝 Contributing

Contributions are very welcome — bug reports, docs fixes, and features alike. See
**[CONTRIBUTING.md](CONTRIBUTING.md)** to get started, and please follow our
**[Code of Conduct](CODE_OF_CONDUCT.md)**.

## 📜 License

[MIT](LICENSE) — do what you like, no warranty.

## 🙏 Acknowledgements

Built on [microsoft/markitdown](https://github.com/microsoft/markitdown).
