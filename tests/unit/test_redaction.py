from backend.app.services.redaction import RedactionEngine


def test_redaction_masks_sensitive_text() -> None:
    engine = RedactionEngine()
    input_text = "email me at dev@example.com and secret=abcd"
    result = engine.apply(input_text.encode("utf-8"))

    assert result.status == "redacted"
    output = result.redacted_bytes.decode("utf-8")
    assert "dev@example.com" not in output
    assert "[REDACTED_EMAIL]" in output
    assert "[REDACTED_SECRET]" in output


def test_redaction_hash_only_policy_for_json() -> None:
    engine = RedactionEngine()
    raw_json = '{"customer":"Jane","ssn":"123-45-6789","order_total":19.0}'
    result = engine.apply(
        raw_json.encode("utf-8"),
        field_policies={"ssn": "hash_only"},
        content_type="application/json",
    )

    output = result.redacted_bytes.decode("utf-8")
    assert "123-45-6789" not in output
    assert "[REDACTED_SSN]" not in output
    assert result.decisions["ssn"] == "hash_only"
