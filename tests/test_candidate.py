import hashlib

import pytest

from rsi_kernel.candidate import ALLOWED_MEDIA_TYPES, Candidate


def test_id_is_sha256_over_sorted_components_and_order_independent():
    a = Candidate({"b": "2", "a": b"1"}, "text/plain")
    b = Candidate({"a": b"1", "b": "2"}, "text/plain")
    assert a.id == b.id
    assert len(a.id) == 64 and int(a.id, 16) >= 0


def test_id_changes_when_any_component_changes():
    a = Candidate({"a": "1"}, "text/plain")
    b = Candidate({"a": "2"}, "text/plain")
    assert a.id != b.id


def test_component_boundaries_are_unambiguous():
    # "ab"+"c" must not hash like "a"+"bc"
    a = Candidate({"ab": "c"}, "text/plain")
    b = Candidate({"a": "bc"}, "text/plain")
    assert a.id != b.id


def test_parent_ids_kept_and_not_part_of_content_hash():
    a = Candidate({"a": "1"}, "text/plain", parent_ids=("p1",))
    b = Candidate({"a": "1"}, "text/plain")
    assert a.parent_ids == ("p1",)
    assert a.id == b.id


@pytest.mark.parametrize(
    "media_type",
    ["application/x-sh", "application/x-python", "application/octet-stream", "text/x-python", ""],
)
def test_non_data_media_types_rejected(media_type):
    with pytest.raises(ValueError):
        Candidate({"a": "1"}, media_type)


def test_allowlist_is_data_only():
    assert ALLOWED_MEDIA_TYPES == frozenset(
        {"text/plain", "application/json", "application/yaml", "application/x-safetensors"}
    )


def test_component_values_must_be_str_or_bytes():
    with pytest.raises(TypeError):
        Candidate({"a": 1}, "text/plain")


def test_hash_matches_documented_encoding():
    c = Candidate({"a": "x"}, "text/plain")
    h = hashlib.sha256()
    for part in (b"a", b"x"):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    assert c.id == h.hexdigest()
