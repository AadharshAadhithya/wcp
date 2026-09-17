from wcp.ids import is_ulid, new_ulid


def test_new_ulid_is_canonical_and_embeds_timestamp() -> None:
    value = new_ulid(timestamp_ms=0)

    assert len(value) == 26
    assert value.startswith("0000000000")
    assert is_ulid(value)


def test_ulid_rejects_ambiguous_characters_and_overflow() -> None:
    assert not is_ulid("01JABCDEFGHJKMNPQRSTVWXYIO")
    assert not is_ulid("81JABCDEFGHJKMNPQRSTVWXYZ")
