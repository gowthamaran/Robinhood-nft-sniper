from sniper.security.redaction import abbreviated, redact


def test_private_key_shape_is_redacted() -> None:
    value = "ab" * 32
    assert value not in redact(f"key={value}")
    assert "REDACTED_PRIVATE_KEY" in redact(value)


def test_rpc_credentials_are_redacted() -> None:
    output = redact("https://alice:password@example.test/rpc?api_key=supersecret")
    assert "password" not in output
    assert "supersecret" not in output


def test_abbreviation() -> None:
    assert abbreviated("0x1234567890abcdef") == "0x1234...cdef"
