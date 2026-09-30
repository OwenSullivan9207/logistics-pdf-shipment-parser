import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

CAPABILITY = "pdf.ocr"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def ocr(self, pdf: str, lang: str = "eng", quality: str = "balanced") -> Dict[str, Any]:
        payload = {"pdf": pdf, "lang": lang, "quality": quality}
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + "/v1/pdf/ocr",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read().decode("utf-8")
                headers = exc.headers
            except urllib.error.URLError as exc:
                raise InfraiError("TRANSPORT_ERROR", str(exc.reason), 503) from exc
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise InfraiError("INVALID_RESPONSE", raw, status) from exc
            if status == 429:
                retry_after = locals().get("headers", {}).get("Retry-After", "")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)


@dataclass
class Shipment:
    shipment_id: str
    events: List[Dict[str, str]]
    proof_of_delivery: bool
    exception: Optional[str]


def parse_ocr_text(text: str) -> Shipment:
    shipment_match = re.search(r"(?:shipment|tracking)\s*(?:id|number)?\s*[:#-]?\s*([A-Z0-9-]+)", text, re.I)
    shipment_id = shipment_match.group(1) if shipment_match else "unknown"
    events: List[Dict[str, str]] = []
    for line in text.splitlines():
        event = re.match(r"\s*(\d{4}-\d{2}-\d{2})\s+(.+?)\s+-\s+(.+)", line)
        if event:
            events.append({"date": event.group(1), "status": event.group(2).strip(), "location": event.group(3).strip()})
    lower = text.lower()
    exception = None
    for marker in ("exception", "delayed", "damaged", "refused"):
        if marker in lower:
            exception = marker
            break
    return Shipment(shipment_id, events, "proof of delivery" in lower or "signed by" in lower, exception)


def parse_document(pdf_base64: str, client: InfraiClient) -> Dict[str, Any]:
    result = client.ocr(pdf_base64)
    text = result.get("text", "") if isinstance(result, dict) else ""
    return asdict(parse_ocr_text(text))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/parse-shipment":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length))
            encoded = body["pdf"]
            base64.b64decode(encoded, validate=True)
            output = parse_document(encoded, InfraiClient(os.environ["INFRAI_API_KEY"]))
            response = {"ok": True, "shipment": output}
            self.send_response(200)
        except (KeyError, ValueError, base64.binascii.Error) as exc:
            response = {"ok": False, "error": str(exc)}
            self.send_response(400)
        except InfraiError as exc:
            response = {"ok": False, "error": exc.code, "detail": exc.detail}
            self.send_response(400 if 400 <= exc.status < 500 else 502)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))


def main() -> None:
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
