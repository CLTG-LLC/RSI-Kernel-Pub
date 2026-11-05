import json

import pytest

from rsi_kernel.splits import SplitConfigError, load_splits, load_splits_file


def _cfg(**over):
    cfg = {
        "splits": [
            {"name": "dev", "purpose": "dev", "selection_eligible": True, "item_ids": ["a", "b"]},
            {"name": "adj", "purpose": "adjudication", "selection_eligible": False, "item_ids": ["c"]},
            {"name": "ho", "purpose": "holdout", "selection_eligible": False, "item_ids": ["d"]},
        ]
    }
    for i, patch in over.items():
        cfg["splits"][int(i[1:])].update(patch)
    return cfg


def test_valid_config_loads():
    splits = load_splits(_cfg())
    assert splits.dev_item_ids() == frozenset({"a", "b"})
    assert splits.by_name["adj"].purpose == "adjudication"


@pytest.mark.parametrize("idx", ["s1", "s2"])
def test_selection_eligible_holdout_or_adjudication_rejected(idx):
    with pytest.raises(SplitConfigError, match="selection"):
        load_splits(_cfg(**{idx: {"selection_eligible": True}}))


def test_unknown_purpose_rejected():
    with pytest.raises(SplitConfigError, match="purpose"):
        load_splits(_cfg(s0={"purpose": "train"}))


def test_overlapping_item_ids_rejected():
    with pytest.raises(SplitConfigError, match="overlap"):
        load_splits(_cfg(s2={"item_ids": ["a"]}))


def test_duplicate_split_name_rejected():
    with pytest.raises(SplitConfigError, match="duplicate"):
        load_splits(_cfg(s1={"name": "dev"}))


def test_missing_or_non_bool_selection_flag_rejected():
    cfg = _cfg()
    del cfg["splits"][0]["selection_eligible"]
    with pytest.raises(SplitConfigError):
        load_splits(cfg)
    with pytest.raises(SplitConfigError):
        load_splits(_cfg(s0={"selection_eligible": "yes"}))


def test_load_from_json_file(tmp_path):
    p = tmp_path / "splits.json"
    p.write_text(json.dumps(_cfg(s1={"selection_eligible": True})))
    with pytest.raises(SplitConfigError):
        load_splits_file(p)
