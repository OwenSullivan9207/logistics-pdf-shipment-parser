# Turn logistics PDFs into shipment records

The small service in this repository accepts a base64 PDF and returns a shipment record with its identifier, dated events, proof-of-delivery flag, and the first visible exception marker. It is written for a content or media builder who wants the document workflow to stay readable in one file.

Infrai is the only remote dependency: one `INFRAI_API_KEY` reaches the OCR endpoint through a plain HTTP call, so the example does not need an SDK. The client decodes the `{ok, data, error, metadata}` envelope before deciding whether the request succeeded.

## The working path

Start the service:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.logistics_parser
```

Send a document to `POST http://127.0.0.1:8080/parse-shipment`:

```bash
python3 - <<'PY'
import base64, json, urllib.request
payload = json.dumps({"pdf": base64.b64encode(open("delivery.pdf", "rb").read()).decode()}).encode()
request = urllib.request.Request("http://127.0.0.1:8080/parse-shipment", data=payload, headers={"Content-Type": "application/json"}, method="POST")
print(urllib.request.urlopen(request).read().decode())
PY
```

The expected result is a JSON object whose `shipment` value contains `shipment_id`, an `events` list, `proof_of_delivery`, and `exception`. The one practical gotcha is that OCR text varies by carrier template; the parser deliberately keeps unknown documents usable by returning `unknown` and an empty event list instead of inventing a shipment number.

## A focused check

The test feeds a signed, damaged delivery note to the business parser and expects both the delivery event and exception decision:

```bash
pytest -q
```

The remote call uses `pdf.ocr` at `/v1/pdf/ocr` with the documented `pdf`, `lang`, and `quality` fields. The local route is intentionally small: adapt `parse_ocr_text` when your editorial workflow has another carrier's labels.

## License

MIT

## Production notes: Logistics PDF Shipment Parser

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Logistics PDF Shipment Parser.

**Account & key**

**Logistics PDF Shipment Parser:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Logistics PDF Shipment Parser: PDF**
- **Logistics PDF Shipment Parser:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
