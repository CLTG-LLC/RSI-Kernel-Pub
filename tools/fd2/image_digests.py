"""Freeze metadata-only linux/amd64 registry digests; never run during evaluation.

Convention: tasks.load_tasks(image_digests={docker_image: 'sha256:…'}).
Registry metadata: https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from prepare_frozen import image_repository
from select_smoke import DATASET, REVISION


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("expected frozen sha256 image digest")
    return value


def validate_mapping(payload, sidecar, digest):
    from gold_validity import matrix
    if (payload["dataset"], payload["revision"], payload["platform"]) != (DATASET, REVISION, "linux/amd64"):
        raise ValueError("image mapping dataset/revision/platform mismatch")
    items = payload["items"]
    expected = {item["item_id"]: item for item in matrix(sidecar)}
    if len(items) != len(expected) or {item["item_id"] for item in items} != set(expected):
        raise ValueError("image mapping must cover exactly the included set")
    if set(payload["image_digests"]) != {item["docker_image"] for item in items}:
        raise ValueError("image mapping has missing or extra entries")
    rows = []
    for item in items:
        original = item["docker_image"]
        if not isinstance(original, str) or not re.fullmatch(r"[^\s]+", original):
            raise ValueError("invalid source image")
        pinned = _digest(payload["image_digests"][original])
        if "@" in original and original.split("@", 1)[1] != pinned:
            raise ValueError("image mapping digest mismatch")
        row = expected[item["item_id"]]
        if any(item[key] != value for key, value in row.items()):
            raise ValueError("image mapping item identity mismatch")
        rows.append({**row, "source_image": original, "docker_image": image_repository(original) + "@" + pinned,
                     "image_mapping_sha256": digest})
    return rows


def read_mapping(url, digest, sidecar, *, fetch=urlopen):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query or parsed.fragment
            or not re.fullmatch(r"/[^/]+/[^/]+/releases/download/[^/]+/[^/]+", parsed.path)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("expected a digest-bound public release asset")
    with fetch(url) as response:
        body = response.read()
    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("image mapping SHA-256 mismatch")
    return validate_mapping(json.loads(body), sidecar, digest)


def resolve_digest(image, *, inspect=subprocess.check_output):
    """Registry manifests/config only: no pull, run, layer download or evaluation."""
    command = ["docker", "buildx", "imagetools", "inspect", image, "--format"]
    manifest = json.loads(inspect([*command, "{{json .Manifest}}"], text=True))
    if "manifests" in manifest:
        matches = [entry for entry in manifest["manifests"]
                   if entry.get("platform", {}).get("os") == "linux"
                   and entry["platform"].get("architecture") == "amd64"]
        if len(matches) != 1:
            raise ValueError("expected exactly one linux/amd64 manifest")
        return _digest(matches[0]["digest"])
    # Pin the configuration inspection to the first response's immutable digest.
    digest = _digest(manifest["digest"])
    config = json.loads(inspect(["docker", "buildx", "imagetools", "inspect",
                                image_repository(image) + "@" + digest, "--format", "{{json .Image}}"], text=True))
    if (config.get("os"), config.get("architecture")) != ("linux", "amd64"):
        raise ValueError("not a linux/amd64 image")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar", type=Path, default=Path("docs/prereg-fd2-items.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from gold_validity import matrix
    from select_smoke import load_tables
    tables = load_tables()  # Existing hash-verified metadata-only projection.
    items = []
    for item in matrix(json.loads(args.sidecar.read_text())):
        rows = [row for row in tables[item["split"]] if row["instance_id"] == item["instance_id"]]
        if len(rows) != 1:
            raise ValueError("expected one metadata row per included item")
        items.append({**item, "docker_image": rows[0]["docker_image"]})
    payload = {"dataset": DATASET, "revision": REVISION, "platform": "linux/amd64", "items": items,
               "image_digests": {image: resolve_digest(image) for image in sorted({row["docker_image"] for row in items})}}
    validate_mapping(payload, json.loads(args.sidecar.read_text()), "")
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
