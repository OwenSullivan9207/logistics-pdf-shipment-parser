from src.logistics_parser import parse_ocr_text


def test_signed_delivery_with_exception_is_structured():
    text = "Shipment ID: SHP-42\n2026-08-01 Delivered - Shanghai\nProof of delivery signed by Lin\nException: damaged carton"
    result = parse_ocr_text(text)
    assert result.shipment_id == "SHP-42"
    assert result.proof_of_delivery is True
    assert result.exception == "exception"
    assert result.events[0]["status"] == "Delivered"
