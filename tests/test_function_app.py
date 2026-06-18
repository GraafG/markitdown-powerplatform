import base64
import json
import sys
from pathlib import Path

import azure.functions as func
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import function_app  # noqa: E402


def _request(payload):
    return func.HttpRequest(
        method="POST",
        url="/api/convert",
        body=json.dumps(payload).encode("utf-8"),
        params={},
    )


def test_decode_content_rejects_invalid_base64():
    with pytest.raises(ValueError, match="not valid base64"):
        function_app._decode_content("not base64")


def test_decode_content_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(function_app, "MAX_FILE_BYTES", 3)
    payload = base64.b64encode(b"1234").decode("ascii")

    with pytest.raises(ValueError, match="too large"):
        function_app._decode_content(payload)


def test_convert_missing_filename():
    payload = {
        "content": base64.b64encode(b"hello").decode("ascii"),
    }

    response = function_app.convert(_request(payload))

    assert response.status_code == 400
    assert b"filename" in response.get_body()


def test_convert_happy_path_docx(tmp_path):
    """Build a minimal .docx in-memory and verify end-to-end conversion."""
    from docx import Document

    doc = Document()
    doc.add_paragraph("Hello MarkItDown")
    docx_path = tmp_path / "sample.docx"
    doc.save(str(docx_path))

    content_b64 = base64.b64encode(docx_path.read_bytes()).decode("ascii")
    payload = {"content": content_b64, "filename": "sample.docx"}

    response = function_app.convert(_request(payload))

    assert response.status_code == 200
    body = response.get_body().decode("utf-8")
    assert "Hello MarkItDown" in body


def test_convert_rejects_unsupported_extension():
    payload = {
        "content": base64.b64encode(b"hello").decode("ascii"),
        "filename": "legacy.doc",
    }

    response = function_app.convert(_request(payload))

    assert response.status_code == 415
    assert b"Unsupported" in response.get_body()


def test_convert_requires_json_object():
    request = func.HttpRequest(
        method="POST",
        url="/api/convert",
        body=b'["not", "an", "object"]',
        params={},
    )

    response = function_app.convert(request)

    assert response.status_code == 400
    assert b"JSON object" in response.get_body()
