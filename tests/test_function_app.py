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
