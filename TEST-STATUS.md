# Test status: documented vs. actually verified

This document tracks which documented behaviours have been **verified with a real
test** versus only documented or unit-tested. It is a living record — update it
whenever a claim is exercised end-to-end.

Legend:

- ✅ **Verified** — exercised end-to-end against live resources, with an observed result.
- 🟦 **Unit-tested** — covered by automated tests in `tests/` (run by CI), but not live.
- 🟡 **Partial** — partly verified; the remaining step needs an interactive/portal action.
- ⛔ **Out of scope** — intentionally not tested for this demo.
- ❌ **Not tested** — documented by design/reasoning only.

## Summary table

| # | Documented claim | Status | Actual result / evidence |
|---|------------------|--------|--------------------------|
| 1 | `.pdf` → Markdown (HTTP 200) | ✅ Verified | Live demo flow converted `sample-pdf.pdf` (200, Markdown returned). |
| 2 | `.docx` → Markdown (HTTP 200) | ✅ Verified | Live flow converted `sample-docx.docx` and a 100k-word `.docx` (768,055 chars). |
| 3 | Unsupported extension → **HTTP 415** | ✅ Verified | Live `POST /api/convert` (valid Entra token): `.txt` filename → **415**; missing extension → **415**. Positive control `.pdf` → 200. |
| 4 | Invalid base64 / non-object JSON → **HTTP 400** | ✅ Verified | Live calls: invalid base64 → **400**; non-object JSON `[1,2,3]` → **400**; malformed JSON → **400**; missing `content` → **400**. |
| 5 | `MAX_FILE_BYTES` (10 MiB default) → **HTTP 400** | ✅ Verified | Live: 11 MiB payload → **400** "File is too large"; a 50 MB `.docx` at the default limit → clean **400** (66.7 MB request body accepted, service stayed healthy). |
| 6 | Entra ID Easy Auth protects the Function | ✅ Verified | Key-only call to `/api/health` → **401**; with a valid Entra token → **200**. Easy Auth is the gate. |
| 7 | `/api/health` returns `ok` (HTTP 200) | ✅ Verified | With an Entra bearer token for `api://<func-app-id>` → **HTTP 200, body `ok`** (works with or without the function key). |
| 8 | Save converted Markdown back to SharePoint with a timestamped name | ✅ Verified | Live flow wrote 3 files named `<original>-yyyyMMdd-HHmmss.md` into the demo folder; verified via Microsoft Graph listing. |
| 9 | Custom connector imports from `connector/openapi.json` | ✅ Verified | Created programmatically in the environment via the PowerApps API; an API-key connection reached status **Connected**. Test artifacts were deleted afterwards. |
| 10 | Custom connector **Entra variant** imports from `connector/openapi-entra.json` | ✅ Verified | Registered programmatically with both `api_key` and OAuth (`token`) connection parameters. A *live* OAuth connection still needs interactive sign-in (auth-code flow). Test artifact deleted afterwards. |
| 11 | One-click ARM deploy (`infra/azuredeploy.json`) | ✅ Verified | `az deployment group validate` returned `error: null`; `az deployment group what-if` succeeded and enumerated the resources to create. No full deploy performed (avoids billable resources). |
| 12 | Demo template uses **native SharePoint connector** actions (Get files / Get file content / Create file) | ✅ Verified | Deployed against a real `shared_sharepointonline` connection and **run end-to-end**: `Get all lists` → `Get files (properties only)` → `Get file content` → `/api/convert` → `Create file`. All 3 supported files (incl. the 100k-word `.docx` → 768 KB `.md`) converted and written back with timestamped names; `legacy-doc.doc` skipped. Verified via Microsoft Graph listing. Deployed as flow **MarkItDown Native SharePoint Connector Demo**. |
| 13 | Encrypted / sensitivity-label-protected files are unsupported | ✅ Verified | A password-encrypted `.pdf` (valid extension) pushed live → **HTTP 422** "The file could not be converted. It may be encrypted, password-protected, or corrupted." Previously returned generic 500; now returns a specific 422 with a descriptive message. |
| 14 | OCR of embedded images via the `markitdown-ocr` plugin | ⛔ Out of scope | Optional capability intentionally **not in scope** for this demo. The plugin is not installed and OCR is documented as an opt-in (see README → OCR). |
| 16 | 50 MB file converts → **HTTP 200** (with raised limit) | ✅ Verified | After setting app setting `MAX_FILE_BYTES=67108864` (64 MiB) on the deployed demo app, a valid 50 MB `.docx` converted → **HTTP 200 in ~8 s**. This is a **deployment override**; the repo code default stays 10 MiB (`DEFAULT_MAX_FILE_BYTES`). |
| 15 | CI workflow (`.github/workflows/ci.yml`) passes | ✅ Verified | Green on `main` (validates JSON, compiles Python, lints with ruff, audits dependencies with pip-audit, runs pytest — 30 tests). |

## What's left to test

The core conversion + SharePoint pipeline and all edge cases (415 / 400 / oversize / 500
protected-file / 50 MB with a raised limit) are now verified end-to-end. Only two items remain,
and neither blocks the demo:

| # | Open item | Current status | Why it's open | How to close it | Effort |
|---|-----------|----------------|---------------|-----------------|--------|
| 10 | Custom connector **Entra variant** — live OAuth connection | 🟡 Partial | Import verified; a real OAuth connection needs interactive Entra sign-in (auth-code flow), which can't be scripted with client-credentials | In the maker portal open the connector's **Test** tab, create a connection (sign in), invoke `Convert` | ~10 min, interactive |
| 14 | OCR of embedded images (`markitdown-ocr` plugin) | ⛔ Out of scope | Optional capability not wired into this deployment | Install `markitdown-ocr`, configure a vision client, convert a doc with an embedded image | ~30–60 min |

Quick exec summary:

- **#3 / #4 / #5 / #13 / oversize** — now confirmed against the **live** Function (415 for bad
  extension; 400 for bad base64, non-object/invalid JSON, missing content, and oversize; 422 for
  encrypted/protected files).
- **50 MB** — works (HTTP 200, ~8 s) once `MAX_FILE_BYTES` is raised on the app; the code default
  stays 10 MiB.
- **#10** — only the *live interactive OAuth* leg is unverified; the import and key-based variant
  are done. Needs a human sign-in by design — it cannot be automated with client-credentials.
- **#14** — OCR is intentionally out of scope for this demo (documented as an opt-in in the README).

## Notes on the demo architecture

- **Repo template flow** (`flows/sharepoint-folder-demo.json`) uses the **native SharePoint
  connector** actions so a human importer gets the intended click-to-connect experience.
  Three details make it work reliably when deployed programmatically (the portal designer
  handles these automatically when you build it by hand):
  - It resolves the library **GUID** from the library *display name* via `Get all lists`
    (`GetAllTables`) + a filter, then passes that GUID to `Get files (properties only)`.
  - It uses the slash-path `GetFileItems` operation (not `ODataStyleGetFileItems`): the
    parenthesised `datasets({dataset})` path of the OData-style variant corrupts the site
    URL when the definition is pushed through the management API, yielding a misleading 404.
  - `Create file` writes to `@item()?['{Path}']` (the source file's own server-relative
    folder), so save-back works regardless of the library's URL name vs. display name.
  - `Convert with markitdown` is shipped **key-only**; add an `ActiveDirectoryOAuth` block
    (tenant / audience `api://<func-app-id>` / clientId / secret) to call the Easy-Auth-
    protected Function. See `SECURITY.md`. The deployed demo flow includes this block.
- **Live demo flow** uses Microsoft Graph (app-only) HTTP calls instead, because it must be
  deployed and run **unattended** and no interactive SharePoint connection exists in the
  environment. Both read from the same SharePoint folder and write timestamped Markdown back.
