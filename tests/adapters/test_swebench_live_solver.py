"""SweSolver uses only a fake Docker CLI: no daemon, dataset or model is reached."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from rsi_kernel.archive import Archive
from rsi_kernel.candidate import Candidate
from rsi_kernel.compare import paired_compare
from rsi_kernel.splits import load_splits

from rsi_kernel.adapters.swebench_live.tasks import SweTask


DIGEST = "sha256:" + "a" * 64
SKILL = "Solve the issue in the supplied repository."
CANDIDATE = Candidate({"SKILL.md": SKILL}, "text/plain")


REPOSITORY = "registry.invalid/synthetic"  # task image name with its ":latest" tag removed

def task():
    statement = "Fix the synthetic defect."
    return SweTask(
        lang="python" if False else "go", instance_id="owner-repo-1", repo="owner/repo",
        created_at=None, docker_image="registry.invalid/synthetic:latest", rebuild_cmds=(),
        problem_statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
        image_digest=DIGEST, dataset_revision="synthetic-revision", parquet_sha256="b" * 64,
        _statement=statement,
    )


class FakeDocker:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.calls = []
        self.failure = None
        self.platform = "linux/amd64"
        self.digest = DIGEST
        self.workdir = "/repo"
        self.head = "initial-head"
        self.patch = "diff --git a/fixed.txt b/fixed.txt\n+fixed\n"
        self.running = False
        self.assets = tmp_path / "assets"
        self.assets.mkdir()
        self.pins = None
        self.prepare_archives()
        self.attempt_count = 0

    def prepare_archives(self):
        import io
        import tarfile

        from rsi_kernel.adapters.swebench_live.solver import CODEX_ASSETS
        self.pins = {}
        for name, (filename, _, target) in CODEX_ASSETS.items():
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w:gz") as archive:
                info = tarfile.TarInfo(name)
                body = name.encode()
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
            (self.assets / filename).write_bytes(payload.getvalue())
            self.pins[name] = (filename, hashlib.sha256(payload.getvalue()).hexdigest(), target)

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        if self.failure == "timeout" and argv[:2] == ["docker", "exec"] and "git" not in argv:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if self.failure == "solver_exit" and argv[:2] == ["docker", "exec"] and "git" not in argv:
            kwargs["stdout"].write(b"")
            return subprocess.CompletedProcess(argv, 1)
        if "context" in argv:
            out = '{"Host":"unix:///synthetic.sock"}'
        elif argv[:3] == ["docker", "image", "inspect"]:
            reference = argv[-1]
            if reference != REPOSITORY + "@" + DIGEST:
                raise subprocess.CalledProcessError(1, argv)
            if "Architecture" in " ".join(argv):
                out = self.platform
            elif "RepoDigests" in " ".join(argv):
                out = json.dumps([REPOSITORY + "@" + self.digest])  # real Docker: tagless
            else:
                out = self.workdir
        elif argv[:2] == ["docker", "create"]:
            out = "synthetic-container-id"
        elif argv[:2] == ["docker", "start"] and "-a" in argv and argv[-1].endswith("-agent"):
            if self.failure == "timeout":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            if self.failure == "stage_mutation":
                (self.attempt() / "stage/problem_statement.md").write_text("mutated")
            out = '{"type":"synthetic output"}'
        elif argv[:2] == ["docker", "exec"] and "git" not in argv:
            if self.failure == "timeout":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            if self.failure == "stage_mutation":
                (self.attempt() / "stage/problem_statement.md").write_text("mutated")
            out = "1" if self.failure == "solver_exit" else '{"type":"synthetic output"}'
        elif argv[:2] == ["docker", "exec"]:
            if argv[3:5] == ["git", "-C"] and "rev-parse" in argv:
                if self.failure == "not_git":
                    raise subprocess.CalledProcessError(128, argv)
                out = self.workdir + "\n" + self.head
            elif "diff" in argv:
                if self.failure == "extract":
                    raise subprocess.CalledProcessError(1, argv)
                out = "" if self.failure == "empty" else self.patch
            else:
                out = ""
        elif argv[:2] == ["docker", "cp"]:
            if self.failure != "trace_missing":
                rows = [
                    {"type": "session_meta", "payload": {"cwd": self.workdir, "model_provider": "proxy"}},
                    {"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
                    {"type": "event_msg", "payload": {"type": "token_count", "info": {
                        "total_token_usage": {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5}}}},
                ]
                (Path(argv[-1]) / "rollout-synthetic.jsonl").write_text(
                    "\n".join(json.dumps(row) for row in rows))
            out = ""
        elif argv[:2] == ["docker", "inspect"]:
            if self.failure == "solver_exit" and "ExitCode" in " ".join(argv):
                out = "1"
            elif "Running" in " ".join(argv):
                out = "true" if self.failure == "still_running" else "false"
            else:
                out = "0"
        else:
            out = ""
        if self.failure == "create" and argv[:2] == ["docker", "create"]:
            raise subprocess.CalledProcessError(1, argv)
        if self.failure == "grader" and self.is_grade(argv):
            raise subprocess.CalledProcessError(1, argv)
        if kwargs.get("stdout") is not None:
            kwargs["stdout"].write(out.encode())
            return subprocess.CompletedProcess(argv, 0)
        return subprocess.CompletedProcess(argv, 0, out.encode(), b"")

    def attempt(self):
        return sorted((self.tmp_path / "evidence").iterdir())[self.attempt_count]

    def agent(self, suffix):
        scope = (self.attempt() / "container-scope.txt").read_text().strip()
        return next(argv for argv, _ in self.calls if "--name" in argv
                    and argv[argv.index("--name") + 1] == scope + suffix)

    def is_grade(self, argv):
        scope = (self.attempt() / "container-scope.txt").read_text().strip()
        return argv[:2] in (["docker", "create"], ["docker", "run"]) and scope + "-grade" in argv


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    import rsi_kernel.adapters.swebench_live.solver as module

    fake = FakeDocker(tmp_path)
    monkeypatch.setattr(module.subprocess, "run", fake)
    monkeypatch.setattr(module.secrets, "token_hex", lambda _: f"fixed-{fake.attempt_count}")
    monkeypatch.setenv("DOCKER_HOST", "unix:///synthetic.sock")
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    grades = []

    def grader(task_value, prediction, output, *, run, image, container_name):
        grades.append((task_value, json.loads(prediction.read_text()), output, run, image))
        scope = (fake.attempt() / "container-scope.txt").read_text().strip()
        assert container_name == scope + "-grade"
        fake(["docker", "create", "--name", container_name, "--network", "none", image], capture_output=True)
        fake(["docker", "start", "-a", container_name], capture_output=True)
        fake(["docker", "rm", container_name], capture_output=True)
        return {"submitted": 1, "submitted_ids": [task_value.instance_id],
                "empty_patch_ids": [], "success_ids": [task_value.instance_id],
                "failure_ids": [], "error_ids": [], "incomplete_ids": []}, {
                    "instance_id": task_value.instance_id, "resolved": True}

    solver = module.SweSolver(
        tasks=[task()], evidence_dir=tmp_path / "evidence", timeout=30,
        codex_assets=fake.assets, grader=grader, grading_image="synthetic-grader@sha256:" + "c" * 64,
        prompt="Read /work/problem_statement.md and /work/skill/SKILL.md; fix the issue.",
    )
    solver._pins.codex_assets = fake.pins
    return module, solver, fake, grades


def solve(fixture):
    _, solver, _, _ = fixture
    return solver(CANDIDATE, task().item_id, run=0)


def test_canonical_repository_digest_is_used_for_every_image_operation(fixture):
    _, _, fake, _ = fixture
    assert solve(fixture)["score"] == 1.0
    reference = REPOSITORY + "@" + DIGEST
    inspections = [a for a, _ in fake.calls if a[:3] == ["docker", "image", "inspect"]]
    assert inspections and all(a[-1] == reference for a in inspections)
    assert fake.agent("-agent")[fake.agent("-agent").index(reference)] == reference


def test_stage_exact_and_digest_platform_verified_before_container(fixture):
    module, solver, fake, grades = solve_fixture = fixture
    result = solve(fixture)
    assert result["score"] == 1.0
    assert json.loads((fake.attempt() / "stage-manifest.json").read_text()) == {
        "problem_statement.md": hashlib.sha256(task().statement.encode()).hexdigest(),
        "skill/SKILL.md": hashlib.sha256(SKILL.encode()).hexdigest(),
    }
    assert not any(a[:2] == ["docker", "start"] for a, _ in fake.calls[:2])
    assert any(a[:3] == ["docker", "image", "inspect"] for a, _ in fake.calls)
    assert grades[0][1] == {task().instance_id: {"model_patch": fake.patch}}
    assert grades[0][3] == 0


@pytest.mark.parametrize("kind,reason", [("platform", "image_architecture"), ("digest", "image_digest")])
def test_identity_mismatch_stops_before_container_start(fixture, kind, reason):
    _, _, fake, grades = fixture
    if kind == "platform":
        fake.platform = "linux/arm64"
    else:
        fake.digest = "sha256:" + "d" * 64
    result = solve(fixture)
    assert result["score"] is None and result["failure"]["reason"] == reason
    assert not any(a[:2] == ["docker", "start"] for a, _ in fake.calls)
    assert not grades


@pytest.mark.parametrize("kind", ["workdir", "git"])
def test_empty_or_non_git_workdir_is_a_structured_stop(fixture, kind):
    _, _, fake, _ = fixture
    if kind == "workdir":
        fake.workdir = ""
    else:
        fake.failure = "not_git"
    result = solve(fixture)
    assert result["score"] is None and result["failure"]["reason"] in {"repo_workdir", "repo_head"}


def test_codex_cwd_and_static_assets_are_readonly_and_stage_is_rechecked(fixture):
    module, _, fake, _ = fixture
    assert solve(fixture)["score"] == 1.0
    create = fake.agent("-agent")
    for name, target in (("codex", "/usr/local/bin/codex"),
                         ("bwrap", "/usr/local/bin/codex-resources/bwrap"),
                         ("codex-code-mode-host", "/usr/local/bin/codex-code-mode-host")):
        assert any(f"target={target},readonly" in arg and "/.swe-codex-0.166.0/" in arg for arg in create)
    assert module.OFFICIAL_CODEX_DIGESTS == {
        "codex": "a0bf572d2f93f056c6712a6da348e96078dc84f3885fd7be67807ef389cb3978",
        "bwrap": "a37212d853eec479c6ad4f0852ccf857dec422b76747f0349c70a382954be56f",
        "codex-code-mode-host": "7588334fd47bc4003d970b70dfd4d1e4578491b1e9baa72976a4c2d7e97590da",
    }
    solve_exec = next(argv for argv, _ in fake.calls if argv[:2] == ["docker", "exec"] and "git" not in argv)
    assert "codex exec -C /repo" in " ".join(solve_exec)
    measurement = json.loads((fake.attempt() / "measurement.json").read_text())
    assert measurement["model"] == "gpt-6.1-sol"
    assert measurement["token_usage"]["total_tokens"] == 5


def test_stage_mutation_is_stop(fixture):
    _, _, fake, grades = fixture
    fake.failure = "stage_mutation"
    result = solve(fixture)
    assert result["failure"]["reason"] == "stage_mutated" and not grades


def test_solver_process_boundary_network_and_fresh_grader(fixture):
    _, _, fake, _ = fixture
    assert solve(fixture)["score"] == 1.0
    create = fake.agent("-agent")
    assert create[create.index("--platform") + 1] == "linux/amd64"
    assert create[create.index("--network") + 1].endswith("-net")
    assert not any(a.endswith("-egress") for a in create)
    forbidden = ("dataset", "cache", "grader", "evidence", "private", "docker.sock")
    allowed_sources = [fake.attempt() / "stage/problem_statement.md", fake.attempt() / "stage/skill",
                       fake.assets / ".swe-codex-0.166.0"]
    mounts = [arg for arg in create if arg.startswith("type=bind")]
    assert len(mounts) == 5
    assert all(any(str(source) in mount for source in allowed_sources) for mount in mounts)
    assert not any(any(word in arg for word in forbidden) for arg in create
                   if arg.startswith("type=bind") and "/evidence/" not in arg and "/.swe-codex-" not in arg)
    assert not any(a in create for a in ("-v", "--volume", "--privileged", "--env-file"))
    assert not any(a == "-e" or a == "--env" for a in create)
    assert "problem_statement.md,target=/work/problem_statement.md,readonly" in " ".join(create)
    assert "skill,target=/work/skill,readonly" in " ".join(create)
    assert fake.agent("-grade") != create
    grade = fake.agent("-grade")
    assert grade[grade.index("--network") + 1] == "none"
    assert create[-2:] == ["sleep", "infinity"]


def test_extraction_happens_before_agent_stop_and_cleanup(fixture):
    _, _, fake, _ = fixture
    assert solve(fixture)["score"] == 1.0
    events = []
    for argv, _ in fake.calls:
        if argv[:2] == ["docker", "exec"] and "diff" in argv:
            events.append("extract")
        if argv[:2] in (["docker", "stop"], ["docker", "rm"], ["docker", "kill"]):
            events.append(argv[1] + ":" + argv[-1])
    assert events[0] == "extract"
    assert "stop:" in next(event for event in events[1:] if event.endswith("-agent"))
    scope = (fake.attempt() / "container-scope.txt").read_text().strip()
    assert all(scope in event for event in events[1:])
    assert not any("prune" in a for a, _ in fake.calls)


@pytest.mark.parametrize("patch", [
    "",
    "diff --git a/new.txt b/new.txt\nnew file mode 100644\n--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+added\n",
    "diff --git a/old.txt b/old.txt\ndeleted file mode 100644\n--- a/old.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-removed\n",
])
def test_extraction_preserves_empty_added_and_deleted_file_diffs(fixture, patch):
    _, _, fake, grades = fixture
    fake.patch = patch
    assert solve(fixture)["score"] == 1.0
    assert grades[0][1] == {task().instance_id: {"model_patch": patch}}
    diff = next(argv for argv, _ in fake.calls if argv[:2] == ["docker", "exec"] and "diff" in argv)
    assert diff[diff.index("diff") + 1:diff.index("diff") + 3] == ["--cached", fake.head]


def test_empty_patch_is_written_and_graded_not_dropped(fixture):
    _, _, fake, grades = fixture
    fake.failure = "empty"
    assert solve(fixture)["score"] == 1.0
    assert grades[0][1] == {task().instance_id: {"model_patch": ""}}


@pytest.mark.parametrize("failure", ["timeout", "solver_exit", "extract", "trace_missing", "grader"])
def test_missing_result_has_reason_and_blocks_paired_compare(fixture, failure):
    _, _, fake, _ = fixture
    fake.failure = failure
    result = solve(fixture)
    assert result["score"] is None and result["failure"]["status"] == "STOP"
    assert result["failure"]["reason"] and result["evidence_dir"]
    comparison = paired_compare([], [{**result, "run": 0}], [(task().item_id, 0)])
    assert comparison.blocks_acceptance


def test_timeout_which_cannot_kill_container_has_specific_stop(fixture):
    _, _, fake, _ = fixture
    fake.failure = "timeout"
    real_run = fake.__call__

    def run(argv, **kwargs):
        if "{{.State.Running}}" in " ".join(argv):
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, b"true", b"")
        return real_run(argv, **kwargs)

    import rsi_kernel.adapters.swebench_live.solver as module
    original = module.subprocess.run
    module.subprocess.run = run
    try:
        result = solve(fixture)
    finally:
        module.subprocess.run = original
    assert result["failure"]["reason"] == "timeout_container_running"


def test_distinct_grade_output_per_attempt_and_run(fixture):
    _, solver, fake, grades = fixture
    assert solver(CANDIDATE, task().item_id, run=0)["score"] == 1.0
    fake.attempt_count += 1
    assert solver(CANDIDATE, task().item_id, run=1)["score"] == 1.0
    assert grades[0][2] != grades[1][2]
    assert grades[0][2].name == "run-0" and grades[1][2].name == "run-1"


@pytest.mark.parametrize("name,expected", [
    ("starryzhang/sweb.eval.x86_64.demo", "starryzhang/sweb.eval.x86_64.demo"),
    ("starryzhang/sweb.eval.x86_64.demo:latest", "starryzhang/sweb.eval.x86_64.demo"),
    ("registry.invalid:5000/team/demo:v1", "registry.invalid:5000/team/demo"),
    ("team/demo@sha256:" + "a" * 64, "team/demo"),
])
def test_repository_reference_drops_tag_and_digest(name, expected):
    from rsi_kernel.adapters.swebench_live import solver as module
    assert module._image_repository(name) == expected
