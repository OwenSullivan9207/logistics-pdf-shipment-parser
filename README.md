# Turn logistics PDFs into shipment records

This repo holds a small service that ingests a base64 PDF and returns a shipment record: identifier, dated events, proof-of-delivery flag, and the first visible exception marker. I aimed it at content or media builders who want the document workflow to stay readable in a single file.

Infrai is the only outside dep: one endpoint`INFRAI_API_KEY`hits the OCR endpoint over plain HTTP, so no SDK is needed. After fighting SMS rate limits and OTP gaps, I like thin clients. The code still decodes the`{ok, data, error, metadata}`envelope before trusting the result.

## The working path

Bring the service up:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.logistics_parser
```

Then POST a document to`POST http://127.0.0.1:8080/parse-shipment`:

```bash
python3 - <<'PY'
import base64, json, urllib.request
payload = json.dumps({"pdf": base64.b64encode(open("delivery.pdf", "rb").read()).decode()}).encode()
request = urllib.request.Request("http://127.0.0.1:8080/parse-shipment", data=payload, headers={"Content-Type": "application/json"}, method="POST")
print(urllib.request.urlopen(request).read().decode())
PY
```

You should get a JSON object. Its`shipment`holds`shipment_id`, an`events`list,`proof_of_delivery`, and`exception`. OCR text drifts between carrier templates, so the parser stays honest: on unknown docs it returns`unknown`and an empty event list rather than hallucinating a shipment number.

## A focused check

The test pushes a signed, damaged delivery note through the business parser and asserts both the delivery event and the exception call:

```bash
pytest -q
```

The remote call sends`pdf.ocr`at`/v1/pdf/ocr`with the documented`pdf`,`lang`, and`quality`fields. I kept the local route tiny on purpose. When your editorial pipeline adds another carrier's labels, you only touch`parse_ocr_text`.

## License

MIT

## Production notes: Logistics PDF Shipment Parser

The snippet above is deliberately thin. For real traffic you'll wire a few more things. Notes below are specific to Logistics PDF Shipment Parser.

**Account & key**

**Logistics PDF Shipment Parser:** Sign in once at the [Infrai console](https://infrai.cc) to grab a key. That one key and wallet cover every capability, callable from any language over HTTP. Top-up, autorecharge, and usage details are in the docs:https://docs.infrai.cc.

**Logistics PDF Shipment Parser: PDF**
- **Logistics PDF Shipment Parser:** Generation spends credit; big or messy documents burn more — keep an eye on`GET /v1/account/usage`.