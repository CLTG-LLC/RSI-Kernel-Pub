"""Reconcile FD2 run directories by filenames only; never open solve artifacts."""
import argparse
from collections import Counter
import os
from pathlib import Path

# Explicit lead-recorded historical bindings, not inferred from an empty directory.
EMPTY_GOLD_TARGETS = {f"fd2-gold-smoke-{number}" for number in (1, 2, 3, 4, 6)}
SOLVE_BINDINGS = {
    "fd2-smoke/evidence/swe-4117ba39": ("rust/yvgude__lean-ctx-632", 0),
    "fd2-noise-floor/evidence/swe-40a78b3e": ("c/DeusData__codebase-memory-mcp-632", 0),
    "fd2-noise-floor/evidence/swe-7a46233d": ("c/DeusData__codebase-memory-mcp-632", 1),
    "fd2-noise-floor/evidence/swe-1f739d15": ("c/DeusData__codebase-memory-mcp-632", 2),
    "fd2-noise-floor/evidence/swe-585f9e35": ("c/colbymchenry__codegraph-1051", 0),
}
# This one lead-verified STOP completed a model solve but never obtained a grade.
FAILED_SOLVE_BINDING = "fd2-noise-floor/evidence/swe-7a46233d"
# RemoteGrader writes this nested transport record; it is not another model attempt.
GRADE_FAILURE_RECORD = f"{FAILED_SOLVE_BINDING}/harness/run-1/failure.json"
SOLVE_FILES = {"attempt.json", "model_patch.diff", "measurement.json", "result.json"}
# Solver __call__ writes container-scope.txt and attempt.json before staging/model use.
ATTEMPT_MARKERS = SOLVE_FILES - {"result.json"} | {"container-scope.txt", "attempt-timing.json", "failure.json"}


def inventory(root):
    files = set()
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        # Installed dependencies/Git objects cannot be campaign evidence.
        if any((Path(directory) / name).is_symlink() for name in dirs):
            raise ValueError(f"symlink directory in inventory: {Path(directory).relative_to(root)}")
        dirs[:] = [name for name in dirs if name not in {".git", ".venv", "harness-venv", "__pycache__"}]
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"symlink file in inventory: {path.relative_to(root)}")
            files.add(path.relative_to(root))
    return files


def classify(root, files):
    name = root.name
    if name in EMPTY_GOLD_TARGETS and not files:
        return "gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)"
    if name in {"fd2-gold-smoke-7", "fd2-gold-smoke-8"} and Path("fd2-gold-smoke-summary/summary.json") in files:
        return "gold run, no model call; summary record present"
    if name == "fd2-gold-validity-1" and Path("fd2-gold-validity-aggregate/validity.json") in files:
        return "gold validity, no model call; aggregate record present"
    if name == "fd2-host-smoke" and Path("smoke/output/summary.json") in files:
        return "gold host-fidelity run, no model call; summary present; vendored result.json files are not solves"
    if name == "fd2-code-c590af8" and Path("pyproject.toml") in files:
        return "code checkout, not an execution record"
    if name == "fd2-codex-assets-0.166.0" and any(path.name.endswith(".tar.gz") for path in files):
        return "runtime assets, not an execution record"
    if name == "fd2-freeze" and Path("artifact/image-digests.json") in files:
        return "image metadata freeze, no model call"
    if name == "fd2-smoke-prerun" and any(path.name == "code-identity.txt" for path in files):
        return "preflight records (4 dry-run, 1 run launcher); solve counted at fd2-smoke, not again here"
    if name == "fd2-smoke" and any(path.name == "model_patch.diff" for path in files):
        return "solver smoke; root result.json is not a second solve"
    if name == "fd2-noise-floor":
        return "voided partial noise floor, operational STOP"
    raise ValueError(f"unclassified or missing record: {name}")


def reconcile(runs_root):
    lines, stops, counts = [], [], Counter()
    complete_bindings = set()
    roots = sorted(path for path in runs_root.glob("fd2-*") if path.is_dir())
    if not roots:
        stops.append("no FD2 run directories")
    for root in roots:
        try:
            if root.is_symlink():
                raise ValueError(f"symlink run directory: {root.name}")
            files = inventory(root)
            lines.append(f"rsi-runs/{root.name}: {classify(root, files)}")
            parents = {path.parent for path in files if path.name in ATTEMPT_MARKERS
                       and f"{root.name}/{path.as_posix()}" != GRADE_FAILURE_RECORD}
            parents |= {path.parent for path in files if path.name == "result.json" and "evidence" in path.parts}
            for parent in sorted(parents):
                binding = f"{root.name}/{parent.as_posix()}"
                required = SOLVE_FILES
                if binding == FAILED_SOLVE_BINDING:
                    required = SOLVE_FILES - {"result.json"} | {"failure.json"}
                if not all(parent / name in files for name in required):
                    stops.append(f"incomplete solve record: {binding}")
                    continue
                if binding not in SOLVE_BINDINGS:
                    stops.append(f"solve record has no content-free instance binding: {binding}")
                    continue
                complete_bindings.add(binding)
                item, run = SOLVE_BINDINGS[binding]
                counts[item] += 1
        except (OSError, ValueError) as error:
            stops.append(str(error))
    for binding in sorted(set(SOLVE_BINDINGS) - complete_bindings):
        stops.append(f"registered solve binding missing or incomplete: {binding}")
    lines.extend(f"{item}: {count}" for item, count in sorted(counts.items()))
    lines.append(f"total_model_solves={sum(counts.values())}")
    lines.extend(f"STOP: {stop}" for stop in stops)
    return "\n".join(lines), stops


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, required=True)
    args = parser.parse_args()
    report, stops = reconcile(args.runs_root)
    print(report)
    raise SystemExit(bool(stops))


if __name__ == "__main__":
    main()
