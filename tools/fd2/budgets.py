"""Recompute registered FD2 budgets from pinned, content-free validity metadata."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

SIDECAR_SHA256 = "5ad4c899e96a85cc83d28030829e4faba720a50fdbd8a53767af2d0304abfff9"
VALIDITY_SHA256 = "e15756d3b1a27e2c2364753af79690971de76fb19a697f190eff70fa04c600e8"
# Lead-recorded capacity-abort disposition, not a silent missing-result exclusion.
JOB_LIMIT_EXCLUSION = "c/DynamoRIO__dynamorio-7903"
# One measured solver smoke, not tuned thresholds or distribution estimates.
SOLVE_SECONDS = 693.6
TOKENS = {"input": 3963217, "cached_input": 3866880, "output": 25190, "reasoning_output": 12166}


def pinned_json(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch: {path.name}")
    return json.loads(data)


def formulas(dev, adj, hold):
    eval_cap = dev * 3 * (1 + 3)
    final, noise = (adj + hold) * 3 * 2, adj * 3
    return {"eval_cap": eval_cap, "spend_cap": eval_cap + 3 + 3,
            "final": final, "noise_floor": noise, "smoke_done": 1,
            "total_solves": eval_cap + final + noise + 1}


def survivors(sidecar, validity):
    rows = validity["instances"]
    ids = [row["item_id"] for row in rows]
    included = [item for split in sidecar["splits"].values() for item in split["item_ids"]]
    if len(ids) != len(set(ids)) or len(included) != len(set(included)) or set(ids) != set(included):
        raise ValueError("duplicate, missing or unexpected validity identity")
    if any(row["validation_incomplete"] and row["item_id"] != JOB_LIMIT_EXCLUSION for row in rows):
        raise ValueError("unclassified incomplete gold validation: STOP")
    valid = {row["item_id"] for row in rows if row["valid"] and not row["validation_incomplete"]}
    return {name: [item for item in split["item_ids"] if item in valid]
            for name, split in sidecar["splits"].items()}


def verify_evaluator(validity, frozen_ref):
    root = Path(__file__).resolve().parents[2]
    checked = set()
    for row in validity["instances"]:
        receipt = row["receipt"]
        if receipt["workflow_commit"] != "e3318b7cb672072da49d229ffbc8aa8e7cfb15dc":
            raise ValueError("unexpected evaluator workflow commit")
        for name, expected in receipt["evaluator_identity"]["files_sha256"].items():
            if (name, expected) in checked:
                continue
            data = subprocess.run(["git", "show", f"{frozen_ref}:{name}"], cwd=root,
                                  check=True, capture_output=True).stdout
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"frozen evaluator SHA-256 mismatch: {name}")
            checked.add((name, expected))
    return len(checked)


def evaluator_hash(validity):
    # Registered content_id framing, ported from src/rsi_kernel/candidate.py.
    identities = {row["item_id"]: row["receipt"]["evaluator_identity"] for row in validity["instances"]}
    components = {"evaluator_identity": json.dumps(identities, sort_keys=True)}
    digest = hashlib.sha256()
    for name in sorted(components):
        for part in (name.encode(), components[name].encode()):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()


def report(sidecar, validity):
    splits = survivors(sidecar, validity)
    rows = {row["item_id"]: row for row in validity["instances"]}
    counts = {name: len(items) for name, items in splits.items()}
    print("survivors:", json.dumps(counts, sort_keys=True))
    for name, items in splits.items():
        repos = {repo for repo in sidecar["splits"][name]["repos"]
                 if any(item.split("/", 1)[1].startswith(repo.replace("/", "__") + "-") for item in items)}
        images = {rows[item]["receipt"]["evaluator_identity"]["image"] for item in items}
        languages = dict(sorted(Counter(item.split("/", 1)[0] for item in items).items()))
        print(f"{name}: repositories={len(repos)} distinct_images={len(images)} languages={json.dumps(languages)}")
    caps = formulas(counts["dev"], counts["adjudication"], counts["holdout"])
    print("registered:", json.dumps(caps, sort_keys=True))
    for phase, count in (("campaign", caps["eval_cap"]), ("noise_floor", caps["noise_floor"]),
                         ("final", caps["final"]), ("smoke_done", 1), ("total", caps["total_solves"])):
        print(f"{phase}: solves={count} serial_solve_seconds={count * SOLVE_SECONDS:.1f} "
              f"tokens={json.dumps({key: value * count for key, value in TOKENS.items()})}")
    surviving = {item for items in splits.values() for item in items}
    image_sizes = {rows[item]["receipt"]["evaluator_identity"]["image"]:
                   max(run.get("image_size_bytes") or 0 for run in rows[item]["runs"])
                   for item in surviving}
    print(f"surviving_distinct_images={len(image_sizes)} recorded_image_bytes={sum(image_sizes.values())}")
    reasons = {}
    for item in sorted(set(rows) - surviving):
        row = rows[item]
        reason = ("job_limit_operational" if item == JOB_LIMIT_EXCLUSION else
                  "low_disk" if row["operational_exclusion"] else
                  "flaky" if any(run["resolved"] for run in row["runs"]) else "never-resolved")
        reasons.setdefault(reason, []).append(item)
    for reason, items in sorted(reasons.items()):
        print(f"excluded {reason} ({len(items)}): " + ", ".join(items))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar", type=Path, default=Path(__file__).resolve().parents[2] / "docs/prereg-fd2-items.json")
    parser.add_argument("--validity", type=Path, required=True)
    parser.add_argument("--frozen-ref", required=True, help="Local Git ref corresponding to the frozen public evaluator tree")
    args = parser.parse_args()
    sidecar = pinned_json(args.sidecar, SIDECAR_SHA256)
    validity = pinned_json(args.validity, VALIDITY_SHA256)
    print(f"frozen_evaluator_file_hashes_verified={verify_evaluator(validity, args.frozen_ref)}")
    print(f"evaluator_hash={evaluator_hash(validity)}")
    report(sidecar, validity)


if __name__ == "__main__":
    main()
