import base64
import binascii
import logging
import os
import tempfile
import uuid

import azure.functions as func

from markitdown import MarkItDown

app = func.FunctionApp()

# markitdown picks the right converter from the file extension. Legacy binary
# ".doc" is intentionally NOT supported: markitdown relies on python-docx, which
# only reads the modern ".docx" (Office Open XML) format.
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024
try:
    MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", str(DEFAULT_MAX_FILE_BYTES)))
except (ValueError, TypeError):
    logging.warning(
        "Invalid MAX_FILE_BYTES value %r, falling back to %d",
        os.environ.get("MAX_FILE_BYTES"),
        DEFAULT_MAX_FILE_BYTES,
    )
    MAX_FILE_BYTES = DEFAULT_MAX_FILE_BYTES

_md = MarkItDown()


def _decode_content(content_b64: str) -> bytes:
    try:
        data = base64.b64decode(content_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("'content' is not valid base64.") from exc

    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            f"File is too large ({len(data)} bytes). "
            f"Maximum supported size is {MAX_FILE_BYTES} bytes."
        )

    return data


@app.route(route="convert", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def convert(req: func.HttpRequest) -> func.HttpResponse:
    """Convert a base64-encoded PDF/Word document to Markdown text.

    Expected JSON body:
        {
            "content":  "<base64-encoded file bytes>",
            "filename": "report.pdf"
        }

    Returns: text/markdown body with the converted content.
    """
    correlation_id = str(uuid.uuid4())

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Request body must be valid JSON.", status_code=400)

    if not isinstance(body, dict):
        return func.HttpResponse("Request body must be a JSON object.", status_code=400)

    content_b64 = body.get("content")
    filename = body.get("filename")

    if not isinstance(content_b64, str) or not content_b64.strip():
        return func.HttpResponse("Missing 'content' (base64) in body.", status_code=400)

    if not isinstance(filename, str) or not filename.strip():
        return func.HttpResponse("Missing 'filename' in body.", status_code=400)

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return func.HttpResponse(
            f"Unsupported or missing extension '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            status_code=415,
        )

    try:
        data = _decode_content(content_b64)
    except ValueError as exc:
        return func.HttpResponse(str(exc), status_code=400)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        result = _md.convert(tmp_path)
        # NOTE: text_content is returned as-is. If a downstream consumer
        # renders it as HTML, crafted documents could inject scripts.
        # Consumers should sanitize the Markdown before rendering to HTML.
        return func.HttpResponse(
            result.text_content,
            mimetype="text/markdown",
            status_code=200,
        )
    except Exception:  # noqa: BLE001 - markitdown can raise parser-specific exceptions
        logging.exception("Conversion failed (correlation_id=%s)", correlation_id)
        return func.HttpResponse(
            f"Conversion failed. Check function logs with correlation_id={correlation_id}.",
            status_code=500,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                logging.warning("Could not delete temp file %s", tmp_path)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok", status_code=200)
