"""Verify frozen Parquet hashes, then write selected full rows as runner-only JSONL."""

import argparse
import hashlib
import json
import re
from pathlib import Path

# SHA-256 values from the metadata receipt for the same pinned dataset revision.
EXPECTED_SHA256 = {
    "data/c-00000-of-00001.parquet": "a4c382c1416ee6e19964931998610f0bf1adc5132516ed034202675ad77541de",
    "data/cpp-00000-of-00001.parquet": "8448db887817b63e4c0c284ca99de1ccda15023f48e5b2234a4084466e0768ae",
    "data/cs-00000-of-00001.parquet": "29ffe16d0b2cd802e753262b8b0d7fe3f2bb1b489396da238146e79f37937c1f",
    "data/go-00000-of-00001.parquet": "76d2b5dff0f3fac8303d30fa85495539e487d25974ad7c21cd21a545cb4756e2",
    "data/java-00000-of-00001.parquet": "00387685808c71d21ada175335304b1c118859453afadd58ea21a00b0d568ee8",
    "data/js-00000-of-00001.parquet": "bc6ec49ffaf9db97840d55eba6954fae8f5fb0fb071cf49e187f36ffadd55a7a",
    "data/rust-00000-of-00001.parquet": "02ac78e2c51a84eb174ac393bb07b77478f1f96cf260af18835a711dd8074ebc",
    "data/ts-00000-of-00001.parquet": "7e23783e27230c9cfab1035690035c25523043d6af635bc78da3fd2010c32714",
}


def write_selected_jsonl(paths, expected_hashes, selection, output, read_rows):
    """Validate every input before writing; never emit row contents to stdout."""
    for name, path in paths.items():
        if name not in expected_hashes:
            raise ValueError(f"No expected SHA-256 for {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_hashes[name]:
            raise ValueError(f"SHA-256 mismatch for {name}")
    if set(paths) != set(expected_hashes):
        raise ValueError("Frozen Parquet file set is incomplete")
    wanted = {item["instance_id"] for item in selection}
    if len(wanted) != len(selection):
        raise ValueError("Duplicate selected instance IDs")
    rows = []
    for split, path in paths.items():
        for row in read_rows(path):
            if row["instance_id"] in wanted:
                rows.append(row)
    if len(rows) != len(selection) or {row["instance_id"] for row in rows} != wanted:
        raise ValueError("Selected rows do not exactly match the frozen selection")
    selected = {item["instance_id"]: item for item in selection}
    prepared = []
    for row in rows:
        item = selected[row["instance_id"]]
        image = item.get("docker_image", "")
        if "@" in image:
            if (not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image)
                    or image_repository(row["docker_image"]) != image_repository(image)
                    or row["docker_image"] != item.get("source_image", row["docker_image"])
                    or ("@" in row["docker_image"] and row["docker_image"] != image)):
                raise ValueError("frozen image repository or digest mismatch")
            row = {**row, "docker_image": image}
        prepared.append(row)
    rows = prepared
    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    return output


def image_repository(image):
    reference = image.split("@", 1)[0]
    return reference.rsplit(":", 1)[0] if ":" in reference.rsplit("/", 1)[-1] else reference


def pin_image(path, instance_id, digest):
    """Replace one row's image reference with its already-pulled digest."""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Expected a full sha256 image digest")
    with path.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    matches = [row for row in rows if row["instance_id"] == instance_id]
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching selected row")
    image = matches[0]["docker_image"]
    if "@" in image and image.split("@", 1)[1] != digest:
        raise ValueError("frozen image digest mismatch")
    repository = image_repository(image)
    updated = [{**row, "docker_image": f"{repository}@{digest}"}
               if row["instance_id"] == instance_id else row for row in rows]
    with path.open("w", encoding="utf-8") as stream:
        for row in updated:
            stream.write(json.dumps(row) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--dataset-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pin-image", nargs=3, metavar=("JSONL", "INSTANCE_ID", "DIGEST"))
    args = parser.parse_args()
    if args.pin_image:
        pin_image(Path(args.pin_image[0]), args.pin_image[1], args.pin_image[2])
        return
    if not all((args.selection, args.dataset_dir, args.output)):
        parser.error("--selection, --dataset-dir and --output are required when not pinning an image")
    selection = json.loads(args.selection.read_text(encoding="utf-8"))["instances"]
    paths = {name: args.dataset_dir / name for name in EXPECTED_SHA256}
    import pyarrow.parquet as pq
    write_selected_jsonl(paths, EXPECTED_SHA256, selection, args.output,
                         lambda path: pq.read_table(path).to_pylist())
    print(f"Verified {len(EXPECTED_SHA256)} frozen Parquet hashes and wrote {len(selection)} selected rows; contents suppressed.")


if __name__ == "__main__":
    main()
