"""Select one newest MultiLang instance per split, using metadata columns only.

Revision pinning: https://huggingface.co/docs/huggingface_hub/package_reference/file_download#huggingface_hub.hf_hub_download
Column projection: https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

DATASET = "SWE-bench-Live/MultiLang"
REVISION = "eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3"
SPLITS = ("c", "cpp", "cs", "go", "java", "js", "rust", "ts")
COLUMNS = ("instance_id", "created_at", "docker_image")


def select_smoke(tables):
    """Return the newest row per split; equal timestamps use the lowest ID."""
    selected = []
    for split, rows in tables.items():
        candidates = [row for row in rows if row["created_at"] is not None]
        if not candidates:
            raise ValueError(f"No dated instances in split: {split}")
        parsed = [(row["instance_id"],
                   row["created_at"] if isinstance(row["created_at"], datetime) else
                   datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")),
                   row["docker_image"]) for row in candidates]
        instance_id, created_at, docker_image = min(
            parsed, key=lambda row: (-row[1].timestamp(), row[0])
        )
        selected.append({
            "instance_id": instance_id,
            "split": split,
            "created_at": created_at.isoformat(),
            "docker_image": docker_image,
        })
    return selected


def load_tables():
    import pyarrow as pa
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, hf_hub_download

    info = HfApi().dataset_info(DATASET, revision=REVISION)
    if info.sha != REVISION:
        raise RuntimeError("Pinned dataset revision did not resolve to itself")
    tables = {}
    for split in SPLITS:
        pattern = re.compile(rf"data/{split}-[^/]+\.parquet")
        files = sorted(item.rfilename for item in info.siblings if pattern.fullmatch(item.rfilename))
        if not files:
            raise RuntimeError(f"No metadata parquet found for split: {split}")
        parts = []
        for name in files:
            path = hf_hub_download(DATASET, name, repo_type="dataset", revision=REVISION)
            parts.append(pq.ParquetFile(Path(path)).read(columns=list(COLUMNS)))
        tables[split] = pa.concat_tables(parts).to_pylist()
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Also write the JSON selection here")
    args = parser.parse_args()
    rendered = json.dumps({
        "dataset": DATASET,
        "revision": REVISION,
        "instances": select_smoke(load_tables()),
    }, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
