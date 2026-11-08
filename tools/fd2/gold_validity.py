"""Content-free matrix/summary plumbing; evaluation stays in gold_smoke.sh."""

import argparse
import json
import os
from pathlib import Path


RUN_FIELDS = ("image_digests", "wall_seconds", "started_at", "completed_at",
              "command_status", "disk_free_bytes_before", "disk_free_bytes_after", "image_size_bytes")


def matrix(sidecar):
    rows = [{"item_id": item, "split": item.split("/", 1)[0],
             "instance_id": item.split("/", 1)[1]}
            for split in sidecar["splits"].values() for item in split["item_ids"]]
    if len({row["item_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate included items")
    return rows


def summarize(item_id, rows, stop_reason=None):
    runs = []
    for number in (1, 2, 3):
        matches = [row for row in rows if row.get("run") == number]
        row = matches[0] if len(matches) == 1 else None
        reason = row.get("reason") if row else stop_reason or "missing_run"
        executed = row.get("executed", True) if row else False
        status = ("unexecuted" if not executed else "aborted" if reason or row.get("command_status") != 0
                  else "completed")
        runs.append({"run": number, "status": status, "reason": reason,
                     "resolved": row.get("resolved") is True if status == "completed" else None,
                     **{key: row.get(key) if row else None for key in RUN_FIELDS}})
    operational_exclusion = any(row["reason"] == "low_disk" for row in runs)
    return {"item_id": item_id, "runs": runs,
            "valid": all(row["status"] == "completed" and row["resolved"] for row in runs),
            "operational_exclusion": operational_exclusion,
            "validation_incomplete": any(row["status"] != "completed" for row in runs) and not operational_exclusion}


def aggregate(sidecar, directory, *, jobs=None):
    summaries, survivors, groups = [], [], {}
    for item in matrix(sidecar):
        folder = directory / f"fd2-gold-validity-{item['instance_id']}"
        path, receipt_path = folder / "summary.json", folder / "runner.json"
        summary = json.loads(path.read_text()) if path.is_file() else summarize(item["item_id"], [])
        if summary["item_id"] != item["item_id"]:
            raise ValueError("summary identity mismatch")
        receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else None
        if receipt is not None:
            if (receipt.get("item_id") != item["item_id"] or not receipt.get("workflow_commit")
                    or not receipt.get("run_id") or not receipt.get("evaluator_identity")
                    or not receipt.get("runner_image_build")):
                raise ValueError("receipt identity mismatch")
            for key, env in (("workflow_commit", "GITHUB_SHA"), ("run_id", "GITHUB_RUN_ID")):
                if os.environ.get(env) and str(receipt[key]) != os.environ[env]:
                    raise ValueError("receipt workflow/run mismatch")
            build_key = json.dumps(receipt["runner_image_build"], sort_keys=True)
            group = groups.setdefault(build_key, {"runner_image_build": receipt["runner_image_build"],
                                                   "item_ids": [], "outcomes": []})
            group["item_ids"].append(item["item_id"])
            group["outcomes"].append({"item_id": item["item_id"], "valid": summary["valid"],
                                       "validation_incomplete": summary["validation_incomplete"]})
        else:
            summary = {**summary, "valid": False, "validation_incomplete": True}
        summary = {**summary, "receipt": receipt}
        summaries.append(summary)
        if summary["valid"]:
            survivors.append(item)
    repos = {repo for split in sidecar["splits"].values() for repo in split["repos"]
             if any(item["instance_id"].startswith(repo.replace("/", "__") + "-") for item in survivors)}
    return {"instances": summaries, "validation_incomplete": any(s["validation_incomplete"] for s in summaries),
            "surviving_instances": len(survivors), "surviving_repositories": len(repos),
            "surviving_languages": len({item["split"] for item in survivors}),
            "by_runner_build": list(groups.values()), "job_timestamps": jobs or []}


def receipt(item_id=None, image=None, mapping_sha256=None):
    from remote_grade import evaluator_identity, runner_image_build
    return {"item_id": item_id, "image_mapping_sha256": mapping_sha256,
            "evaluator_identity": evaluator_identity(image), "runner_image_build": runner_image_build(),
            "workflow_commit": os.environ.get("GITHUB_SHA"), "run_id": os.environ.get("GITHUB_RUN_ID"),
            "job": os.environ.get("GITHUB_JOB"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}


def job_timestamps(path):
    # GitHub's authoritative job lifecycle fields, not local wall-clock guesses.
    # created_at is job creation (the queue-measurement origin); no queued_at is
    # exposed. https://docs.github.com/en/rest/actions/workflow-jobs
    pages = json.loads(path.read_text())
    keys = ("id", "name", "run_id", "run_attempt", "created_at", "started_at", "completed_at", "status", "conclusion")
    return [{key: job.get(key) for key in keys} for page in pages for job in page["jobs"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("matrix", "select", "summary", "aggregate", "receipt"))
    parser.add_argument("--sidecar", type=Path, default=Path("docs/prereg-fd2-items.json"))
    parser.add_argument("--item-id")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image")
    parser.add_argument("--source-image")
    parser.add_argument("--mapping-url")
    parser.add_argument("--mapping-sha256")
    parser.add_argument("--jobs", type=Path)
    args = parser.parse_args()
    sidecar = json.loads(args.sidecar.read_text())
    if args.mode == "matrix":
        from image_digests import read_mapping
        result = {"include": read_mapping(args.mapping_url, args.mapping_sha256, sidecar)}
    elif args.mode == "select":
        from select_smoke import DATASET, REVISION, load_tables
        from prepare_frozen import image_repository
        from image_digests import _digest
        item = next(row for row in matrix(sidecar) if row["item_id"] == args.item_id)
        rows = [row for row in load_tables()[item["split"]] if row["instance_id"] == item["instance_id"]]
        if len(rows) != 1:
            raise ValueError("expected exactly one included instance")
        if (not args.image or "@" not in args.image or rows[0]["docker_image"] != args.source_image
                or image_repository(args.image) != image_repository(args.source_image)):
            raise ValueError("frozen image metadata mismatch")
        _digest(args.image.split("@", 1)[1])
        if "@" in args.source_image and args.source_image != args.image:
            raise ValueError("frozen image digest mismatch")
        result = {"dataset": DATASET, "revision": REVISION,
                  "instances": [{**item, "docker_image": args.image, "source_image": args.source_image}]}
    elif args.mode == "summary":
        source = json.loads(args.input.read_text()) if args.input.is_file() else {}
        rows = [row for item in source.get("instances", []) for row in item["runs"]]
        journal = args.input.parent / "runs.ndjson"
        if not source and journal.is_file():
            rows = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
        active_path = args.input.parent / "active-run.json"
        if active_path.is_file():
            active = json.loads(active_path.read_text())
            if not any(row["run"] == active["run"] for row in rows):
                rows.append({**active, "resolved": False, "command_status": None,
                             "reason": source.get("stop_reason") or "silent_termination"})
        result = summarize(args.item_id, rows, source.get("stop_reason"))
    elif args.mode == "receipt":
        result = receipt(args.item_id, args.image, args.mapping_sha256)
    else:
        result = aggregate(sidecar, args.input, jobs=job_timestamps(args.jobs) if args.jobs else None)
    rendered = json.dumps(result, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    else:
        print(rendered)
    if args.mode == "aggregate" and result["validation_incomplete"]:
        raise SystemExit("Gold validation is incomplete; see the content-free aggregate.")


if __name__ == "__main__":
    main()
