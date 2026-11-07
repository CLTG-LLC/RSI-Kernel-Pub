"""Docker is faked here: these tests never call a model or Docker daemon."""

import hashlib
import importlib
import json
import subprocess
from pathlib import Path

import pytest

from rsi_kernel.candidate import Candidate
from rsi_kernel.adapters.gdpevo.tasks import FrozenTask


GROUP_001_ENDPOINTS = "GET /health\nGET /api/manifest\nGET /api/events\nPOST /api/judge\n"
GROUP_002_ENDPOINTS = "GET /health\nGET /api/customers\nGET /api/quotes\nPOST /api/judge\n"
# Groups 004/008 serve only the nested health route; group 005 serves both.
GROUP_004_ENDPOINTS = "GET /api/health\nGET /api/items\nPOST /api/judge\n"
BOTH_HEALTH_ENDPOINTS = "GET /health\nGET /api/health\nGET /api/items\nPOST /api/judge\n"
BOTH_GROUPS = {"task_group_001": GROUP_001_ENDPOINTS, "task_group_002": GROUP_002_ENDPOINTS}


def write_group(root, group, endpoints, task_id="001"):
    """One synthetic group: task layout plus its own env/endpoints.txt."""
    task_dir = root / "data/task_groups" / group / "train_tasks" / task_id
    files = {
        "input/prompt.txt": "synthetic task",
        "eval/eval.sh": "#!/bin/sh\necho '{\"total_score\": 1}'\n",
        "eval/evaluate.py": "# synthetic trusted grader\n",
        # Grader-only reference answer: evaluators read ../output/answer.json.
        "output/answer.json": '{"synthetic": "gold"}\n',
    }
    for name, body in files.items():
        path = task_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    env = root / "data/task_groups" / group / "env"
    env.mkdir(parents=True, exist_ok=True)
    (env / "Dockerfile").write_text("FROM python:3.12-slim\nCOPY server.py /server.py\n")
    (env / "server.py").write_text("# synthetic environment\n")
    (env / "endpoints.txt").write_text(endpoints)
    (root / "data/task_groups" / group / "task_group.yaml").write_text("state_mode: read_only\n")
    return FrozenTask(group, "train", task_id, {
        name: hashlib.sha256((task_dir / name).read_bytes()).hexdigest() for name in files
    })


@pytest.fixture
def build_solver(tmp_path, monkeypatch):
    """One synthetic upstream root per call; groups differ only by endpoints.txt."""
    def build(groups):
        mod = importlib.import_module("rsi_kernel.adapters.gdpevo.solver_docker")
        root = tmp_path / "upstream"
        tasks = [write_group(root, group, endpoints) for group, endpoints in groups.items()]
        prompt = root / "evaluation/eval_workspace/codex/guides/agent_prompts.md"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("## Test Solver\n```text\nAttempt <unique_eval_attempt_id>, condition <base|fewshot|self|reflect-3>.\n```\n")
        hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in root.rglob("*") if p.is_file()}
        monkeypatch.setattr(mod, "UPSTREAM_HASHES", hashes)
        # One evidence tree per group set, so a second build in a test stays isolated.
        evidence = tmp_path / ("evidence-" + "-".join(sorted(groups)))
        solver = mod.DockerSolver(root=root, tasks=tasks, evidence_dir=evidence, timeout=60)
        fake = FakeDocker(root, solver)
        monkeypatch.setattr(mod.subprocess, "run", fake)
        incoming = tmp_path / "incoming/input"
        incoming.mkdir(parents=True, exist_ok=True)
        (incoming / "prompt.txt").write_text("synthetic task")
        return mod, solver, fake, incoming, tmp_path / "incoming/answer.json"
    return build


@pytest.fixture
def docker_solver(build_solver):
    return build_solver({"task_group_001": GROUP_001_ENDPOINTS})


class FakeDocker:
    def __init__(self, root, solver):
        self.root, self.solver = root, solver
        self.calls = []
        self.failure = None
        self.health = ["starting", "healthy"]
        self.attach_started = False
        self.health_body = {"ok": True}
        self.judge_http_status = 404

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        text = " ".join(argv)
        out = ""
        if argv[0] == "git":
            if "HEAD" in argv:
                out = self.solver.upstream_commit + "\n"
            elif "archive" in argv:
                import io
                import tarfile
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    for selected in argv[argv.index(self.solver.upstream_commit) + 1:]:
                        path = self.root / selected
                        archive.add(path, arcname=selected)
                return subprocess.CompletedProcess(argv, 0, stream.getvalue(), b"")
            else:
                relative = argv[-1].split(":", 1)[1]
                body = (self.root / relative).read_bytes()
                out = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() + "\n"
        elif "context" in argv and "inspect" in argv:
            out = '{"Host":"unix:///synthetic-colima.sock","SkipTLSVerify":false}'
        elif argv[1:3] == ["image", "inspect"]:
            out = "linux/arm64\nlinux/arm64\n" if "Architecture" in text else "sha256:synthetic\n"
        elif "Health.Status" in text:
            out = self.health.pop(0) if len(self.health) > 1 else self.health[0]
        elif "ExitCode" in text:
            out = "1" if self.failure == "solver_exit" else "0"
        elif argv[1] == "create":
            if self.failure == "create":
                raise subprocess.CalledProcessError(1, argv, output="private")
            out = "agent-id"
        elif argv[1] == "start":
            self.attach_started = True
            evidence = self.attempt()
            if self.failure != "missing_answer":
                (evidence / "work/answer.json").write_text("not json" if self.failure == "answer_json" else "{}")
            if self.failure == "mutation":
                (evidence / "work/input/prompt.txt").write_text("changed")
            if self.failure == "contamination":
                (evidence / "work/contamination_report.txt").write_text("STOP")
            if self.failure == "timeout":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            out = '{"type":"completed"}\n'
        elif argv[1] == "cp":
            sessions = Path(argv[-1])
            sessions.mkdir(parents=True, exist_ok=True)
            if self.failure != "trace_missing":
                scope = (self.attempt() / "container-scope.txt").read_text().strip()
                provider = "wrong" if self.failure == "trace_provider" else "proxy"
                model = "wrong" if self.failure == "trace_model" else "gpt-6.1-sol"
                rows = [
                    {"type": "session_meta", "payload": {"cwd": "/work", "model_provider": provider}},
                    {"type": "response_item", "payload": {"text": scope}},
                    {"type": "turn_context", "payload": {"model": model}},
                    {"type": "event_msg", "payload": {"type": "token_count", "info": {
                        "total_token_usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3}}}},
                    {"type": "event_msg", "payload": {"type": "token_count", "info": {
                        "total_token_usage": {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}}}},
                ]
                if self.failure == "usage_missing":
                    rows = rows[:-2]
                (sessions / "rollout-primary.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
        elif argv[1] == "run" and "/trusted/eval/eval.sh" in argv:
            sanity = "empty-prediction" in text
            if self.failure == "grader_exit" and not sanity:
                raise subprocess.CalledProcessError(1, argv, output="private grader")
            if self.failure == "grader_json" and not sanity:
                out = "invalid"
            else:
                out = json.dumps({"total_score": 1 if (not sanity or self.failure == "sanity") else 0})
                if self.failure == "grader_error" and not sanity:
                    out = '{"total_score":0,"error":"private rubric"}'
                if self.failure == "grader_score" and not sanity:
                    out = '{"total_score":true}'
        elif argv[1] == "run" and "python3" in argv:
            if self.failure in ("judge", "health_status"):
                raise subprocess.CalledProcessError(1, argv, output="private check")
            out = json.dumps({"health": self.health_body, "judge_http_status": self.judge_http_status})
        if kwargs.get("stdout") is not None:
            kwargs["stdout"].write(out.encode())
            return subprocess.CompletedProcess(argv, 0, None, None)
        return subprocess.CompletedProcess(argv, 0, out.encode(), b"")

    def attempt(self):
        return next(self.solver.evidence_dir.iterdir())


def solve(fixture, env=None, item_id="task_group_001/train/001"):
    _, solver, _, incoming, prediction = fixture
    return solver(Candidate({"SKILL.md": "synthetic skill"}, "text/plain"),
                  item_id, incoming, prediction,
                  env or {"TASK_ENV_ENABLE_JUDGE": "0"})


def test_per_group_access_note_port_and_health(docker_solver, build_solver):
    mod, solver, fake, _, _ = docker_solver
    assert solve(docker_solver)["score"] == 1
    note = (fake.attempt() / "work/environment_access.md").read_text()
    assert note.startswith("Environment base URL: http://task-env:9001/\n")
    assert "No credentials are required." in note
    assert "GET /api/manifest" in note and "GET /api/events" in note
    assert "/health" not in note and "/api/judge" not in note
    assert "instead of any localhost URL" in note
    env = next(a for a, _ in fake.calls if "TASK_ENV_ENABLE_JUDGE=0" in a)
    assert "TASK_ENV_PORT=9001" in env and "127.0.0.1:9001/health" in " ".join(env)
    check = next(a for a, _ in fake.calls if "python3" in a and a[:2] == ["docker", "run"])
    assert "task-env:9001" in check[-1]

    second = build_solver({"task_group_002": GROUP_002_ENDPOINTS})
    mod, solver, fake, _, _ = second
    assert solve(second, item_id="task_group_002/train/001")["score"] == 1
    note = (fake.attempt() / "work/environment_access.md").read_text()
    assert note.startswith("Environment base URL: http://task-env:9002/\n")
    assert "GET /api/customers" in note and "GET /api/manifest" not in note
    assert "/health" not in note and "/api/judge" not in note
    env = next(a for a, _ in fake.calls if "TASK_ENV_ENABLE_JUDGE=0" in a)
    assert "TASK_ENV_PORT=9002" in env and "127.0.0.1:9002/health" in " ".join(env)
    assert "task-env:9002" in next(a for a, _ in fake.calls if "python3" in a and a[:2] == ["docker", "run"])[-1]


@pytest.mark.parametrize("method", ["POST /api/records", "PUT /api/records/{id}"])
def test_non_judge_write_endpoint_stops_before_solve(build_solver, method):
    fixture = build_solver({"task_group_001": f"GET /health\n{method}\nPOST /api/judge\n"})
    _, _, fake, _, _ = fixture
    result = solve(fixture)
    assert result["failure"] == {"status": "STOP", "reason": "env_endpoint"}
    assert not any(a[0] == "docker" for a, _ in fake.calls)
    assert not fake.attach_started


@pytest.mark.parametrize("failure", ["health_status", "judge"])
def test_health_or_judge_check_failure_is_a_stop(docker_solver, failure):
    _, _, fake, _, _ = docker_solver
    fake.failure = failure
    result = solve(docker_solver)
    assert result["score"] is None and result["failure"]["status"] == "STOP"
    assert not fake.attach_started


def test_any_json_health_body_passes(docker_solver):
    _, _, fake, _, _ = docker_solver
    fake.health_body = {"ok": True, "service": "synthetic"}
    assert solve(docker_solver)["score"] == 1


def test_judge_check_must_still_be_404(docker_solver):
    _, _, fake, _, _ = docker_solver
    fake.judge_http_status = 200
    result = solve(docker_solver)
    assert result["failure"] == {"status": "STOP", "reason": "environment_check"}
    assert not fake.attach_started


def test_stage_is_exact_readonly_and_no_credentials(docker_solver):
    mod, solver, fake, _, prediction = docker_solver
    result = solve(docker_solver)
    assert result["score"] == 1 and prediction.read_text() == "{}"
    evidence = fake.attempt()
    assert set(json.loads((evidence / "stage-manifest.json").read_text())) == {
        "input/prompt.txt", "skill/SKILL.md", "environment_access.md"}
    create = next(argv for argv, _ in fake.calls if argv[:2] == ["docker", "create"])
    assert all(flag not in create for flag in ["-e", "--env", "--env-file", "--privileged"])
    for target in ["/work/input", "/work/skill", "/work/environment_access.md"]:
        assert any(f"target={target},readonly" in arg for arg in create)
    assert "gpt-6.1-sol" in " ".join(create) and 'model_reasoning_effort="xhigh"' in " ".join(create)
    assert 'approval_policy="never"' in " ".join(create) and "--sandbox danger-full-access" in " ".join(create)
    assert "requires_openai_auth = false" in " ".join(create)
    assert "http://model-fwd:8080/v1" in " ".join(create)
    assert (evidence / "build/model-fwd.conf").read_text() == mod.FORWARDER_CONF
    assert (evidence / "prompt.txt").read_text().startswith("Attempt gdp-")
    assert "condition self." in (evidence / "prompt.txt").read_text()
    assert (evidence / "build/Dockerfile").read_bytes() == (Path(mod.__file__).with_name("Dockerfile")).read_bytes()


def test_judge_disabled_readiness_and_grading_offline(docker_solver):
    mod, _, fake, _, _ = docker_solver
    assert solve(docker_solver)["score"] == 1
    env = next(a for a, _ in fake.calls if "TASK_ENV_ENABLE_JUDGE=0" in a)
    assert "--health-cmd" in env
    assert not any(a.startswith("--health-") for a in env if a != "--health-cmd")
    check = next(a for a, _ in fake.calls if "python3" in a and a[:2] == ["docker", "run"])
    assert "/health" in check[-1] and "/api/judge" in check[-1] and "404" in check[-1]
    assert mod.NGINX_IMAGE in " ".join(" ".join(a) for a, _ in fake.calls)
    graders = [a for a, _ in fake.calls if "/trusted/eval/eval.sh" in a]
    assert len(graders) == 2
    assert all(a[a.index("--network") + 1] == "none" for a in graders)


def test_evidence_final_cumulative_usage_and_scoped_cleanup(docker_solver):
    _, _, fake, _, _ = docker_solver
    result = solve(docker_solver)
    evidence = fake.attempt()
    measured = json.loads((evidence / "measurement.json").read_text())
    trace = Path(measured["trace"])
    assert measured["token_usage"] == {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}
    assert measured["trace_sha256"] == hashlib.sha256(trace.read_bytes()).hexdigest()
    assert measured["cost_usd"] is None
    assert json.loads((evidence / "attempt-timing.json").read_text())["elapsed_seconds"] >= 0
    assert json.loads((evidence / "score.json").read_text()) == {"total_score": 1}
    assert result["evidence_dir"] == str(evidence)
    scope = (evidence / "container-scope.txt").read_text().strip()
    cleanup = [a for a, _ in fake.calls if "rm" in a]
    assert cleanup and all(scope in " ".join(a) for a in cleanup)
    assert not any("prune" in a for a, _ in fake.calls)


@pytest.mark.parametrize("failure", ["create", "sanity", "judge", "solver_exit", "timeout",
    "missing_answer", "answer_json", "mutation", "contamination", "trace_missing", "trace_provider",
    "trace_model", "grader_exit", "grader_json", "grader_error", "grader_score"])
def test_each_stop_retains_artifacts_and_resources(docker_solver, failure):
    _, _, fake, _, _ = docker_solver
    fake.failure = failure
    result = solve(docker_solver)
    assert result["score"] is None and result["failure"]["reason"]
    assert result["failure"]["status"] == "STOP"
    assert json.loads((fake.attempt() / "failure.json").read_text()) == result
    assert not any("rm" in a for a, _ in fake.calls)
    assert "private" not in json.dumps(result["failure"])


def test_unhealthy_is_stop_before_model(docker_solver):
    _, _, fake, _, _ = docker_solver
    fake.health = ["unhealthy"]
    result = solve(docker_solver)
    assert result["failure"]["reason"] == "environment_unhealthy"
    assert not fake.attach_started


def test_input_drift_stops_before_docker(docker_solver):
    _, _, fake, incoming, _ = docker_solver
    (incoming / "prompt.txt").write_text("changed")
    assert solve(docker_solver)["failure"]["reason"] == "staging_manifest_mismatch"
    assert not any(a[0] == "docker" for a, _ in fake.calls)


def test_missing_usage_is_null_not_invented(docker_solver):
    _, _, fake, _, _ = docker_solver
    fake.failure = "usage_missing"
    assert solve(docker_solver)["score"] == 1
    assert json.loads((fake.attempt() / "measurement.json").read_text())["token_usage"] is None


def test_non_dev_and_credential_env_rejected(docker_solver):
    _, solver, fake, incoming, prediction = docker_solver
    result = solver(Candidate({"SKILL.md": "x"}, "text/plain"), "task_group_001/test/001",
                    incoming, prediction, {"TASK_ENV_ENABLE_JUDGE": "0"})
    assert result["failure"]["reason"] == "staging"
    assert not any(a[0] == "docker" for a, _ in fake.calls)


def test_adapter_consumes_docker_score_without_host_grader(docker_solver, monkeypatch):
    from rsi_kernel.adapters.gdpevo import GDPevoAdapter, carve_splits
    from rsi_kernel.archive import Archive
    _, solver, fake, _, _ = docker_solver
    task = next(iter(solver.tasks.values()))
    candidate = Candidate({"SKILL.md": "synthetic skill"}, "text/plain")
    adapter = GDPevoAdapter(root=solver.root, champion=candidate, tasks=[task],
        splits=carve_splits([task], {task.group: [task.task_id]}), solver=solver,
        evaluator_timeout=60, work_dir=solver.evidence_dir.parent / "stages",
        archive=Archive(solver.evidence_dir.parent / "public", solver.evidence_dir.parent / "private"))
    monkeypatch.setattr(adapter, "_grade", lambda *a: pytest.fail("host grader must not run"))
    result = adapter.evaluate(candidate, [task.item_id])[0]
    assert result["score"] == 1 and result["feedback"] == {"score": 1, "correct": True}
    assert Path(result["evidence_dir"]).exists()
    assert not any(a[0] == "/bin/sh" for a, _ in fake.calls)


def test_adapter_preserves_docker_stop(docker_solver):
    from rsi_kernel.adapters.gdpevo import GDPevoAdapter, carve_splits
    from rsi_kernel.archive import Archive
    _, solver, fake, _, _ = docker_solver
    task = next(iter(solver.tasks.values()))
    candidate = Candidate({"SKILL.md": "synthetic skill"}, "text/plain")
    adapter = GDPevoAdapter(root=solver.root, champion=candidate, tasks=[task],
        splits=carve_splits([task], {task.group: [task.task_id]}), solver=solver,
        evaluator_timeout=60, work_dir=solver.evidence_dir.parent / "stages",
        archive=Archive(solver.evidence_dir.parent / "public", solver.evidence_dir.parent / "private"))
    fake.health = ["unhealthy"]
    result = adapter.evaluate(candidate, [task.item_id])[0]
    assert result["failure"] == {"status": "STOP", "reason": "environment_unhealthy"}
    assert Path(result["evidence_dir"]).exists()


@pytest.mark.parametrize("env", [{"TASK_ENV_ENABLE_JUDGE": "1"},
    {"TASK_ENV_ENABLE_JUDGE": "0", "OPENAI_API_KEY": "SYNTHETIC_SECRET"},
    {"TASK_ENV_ENABLE_JUDGE": "0", "PROVIDER_API_KEY": "SYNTHETIC_SECRET"}])
def test_solver_rejects_judge_or_secret_environment(docker_solver, env):
    _, _, fake, _, _ = docker_solver
    result = solve(docker_solver, env)
    assert result["failure"]["reason"] == "solver_env"
    assert not any(a[0] == "docker" for a, _ in fake.calls)
    assert "SYNTHETIC_SECRET" not in json.dumps(result)


@pytest.mark.parametrize("field,value,reason", [
    ("upstream_commit", "wrong", "upstream_commit"),
    ("DOCKERFILE_SHA256", "0" * 64, "dockerfile_hash"),
])
def test_pin_mismatch_is_structured_stop(docker_solver, monkeypatch, field, value, reason):
    mod, solver, fake, _, _ = docker_solver
    if field == "upstream_commit":
        original = fake.__call__
        def run(argv, **kwargs):
            if argv[0] == "git" and "HEAD" in argv:
                return subprocess.CompletedProcess(argv, 0, b"wrong", b"")
            return original(argv, **kwargs)
        monkeypatch.setattr(mod.subprocess, "run", run)
    else:
        monkeypatch.setattr(mod, field, value)
    result = solve(docker_solver)
    assert result["failure"]["reason"] == reason
    assert not any("rm" in a for a, _ in fake.calls)


def test_docker_health_timeout_uses_caller_budget(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    fake.health = ["starting"]
    ticks = iter([0, 61])
    monkeypatch.setattr(mod.time, "monotonic", lambda: next(ticks))
    result = solve(docker_solver)
    assert result["failure"]["reason"] == "environment_timeout"
    assert not fake.attach_started


def test_trace_malformed_is_structured_stop(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    original = fake.__call__
    def run(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[:2] == ["docker", "cp"]:
            (Path(argv[-1]) / "rollout-primary.jsonl").write_text('[]\n')
        return result
    monkeypatch.setattr(mod.subprocess, "run", run)
    result = solve(docker_solver)
    assert result["score"] is None and result["failure"]["status"] == "STOP"


def test_solver_network_internal_forwarder_alone_dual_homed(docker_solver):
    _, _, fake, _, _ = docker_solver
    assert solve(docker_solver)["score"] == 1
    scope = (fake.attempt() / "container-scope.txt").read_text().strip()
    networks = [a for a, _ in fake.calls if a[:3] == ["docker", "network", "create"]]
    assert ["docker", "network", "create", "--internal", scope + "-net"] in networks
    assert ["docker", "network", "create", scope + "-egress"] in networks
    connections = [a for a, _ in fake.calls if a[:3] == ["docker", "network", "connect"]]
    assert connections == [["docker", "network", "connect", "--alias", "model-fwd", scope + "-net", scope + "-fwd"]]
    for role in ["-env", "-agent"]:
        argv = next(a for a, _ in fake.calls if "--name" in a and a[a.index("--name") + 1] == scope + role)
        assert argv[argv.index("--network") + 1] == scope + "-net"
        assert scope + "-egress" not in argv
    forwarder = next(a for a, _ in fake.calls if "--name" in a and a[a.index("--name") + 1] == scope + "-fwd")
    assert forwarder[forwarder.index("--network") + 1] == scope + "-egress"
    removals = [a for a, _ in fake.calls if a[:3] == ["docker", "network", "rm"]]
    assert any(scope + "-net" in a for a in removals)
    assert any(scope + "-egress" in a for a in removals)


@pytest.mark.parametrize("failure", ["missing_section", "missing_fence", "placeholder"])
def test_bad_upstream_prompt_is_structured_stop(docker_solver, monkeypatch, failure):
    mod, solver, fake, _, _ = docker_solver
    path = solver.root / mod.PROMPT_PATH
    path.write_text({"missing_section": "no test solver", "missing_fence": "## Test Solver\nno fence",
                     "placeholder": "## Test Solver\n```text\n<unknown>\n```"}[failure])
    monkeypatch.setattr(mod, "UPSTREAM_HASHES", {**mod.UPSTREAM_HASHES,
        mod.PROMPT_PATH: hashlib.sha256(path.read_bytes()).hexdigest()})
    result = solve(docker_solver)
    assert result["score"] is None and result["failure"]["reason"] == "prompt"
    assert not any(a[0] == "docker" for a, _ in fake.calls)


def test_missing_archived_input_is_stop(docker_solver, monkeypatch):
    mod, solver, fake, _, _ = docker_solver
    original = fake.__call__
    def run(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[:2] == ["docker", "cp"]:
            (fake.attempt() / "trusted/data/task_groups/task_group_001/env/server.py").unlink()
        return result
    monkeypatch.setattr(mod.subprocess, "run", run)
    result = solve(docker_solver)
    assert result["score"] is None and result["failure"]["reason"] == "upstream_manifest"
    assert not any("rm" in a for a, _ in fake.calls)


def test_cleanup_not_before_evidence(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    original = fake.__call__
    def run(argv, **kwargs):
        if "rm" in argv:
            out = fake.attempt()
            for name in ["result.json", "score.json", "measurement.json", "attempt-timing.json"]:
                assert (out / name).is_file()
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    assert solve(docker_solver)["score"] == 1


def test_stage_verifies_only_archived_input_and_eval_subset(docker_solver):
    mod, solver, fake, incoming, _ = docker_solver
    task = next(iter(solver.tasks.values()))
    directory = task.directory(solver.root)
    # Real GDPevo task layout: a note exists but is never archived nor mounted.
    notes = directory / "notes/notes.md"
    notes.parent.mkdir()
    notes.write_text("SYNTHETIC_NOTES")
    hashes = {**task.hashes, "notes/notes.md": hashlib.sha256(notes.read_bytes()).hexdigest()}
    task = FrozenTask(task.group, task.subset, task.task_id, hashes)
    solver.tasks = {task.item_id: task}
    out = solver.evidence_dir / "stage-only"
    out.mkdir(parents=True)
    trusted, work, _, _ = solver._stage(Candidate({"SKILL.md": "skill"}, "text/plain"),
                                      task, incoming, out, "gdp-stage-only")
    # Gold reaches the trusted, grader-only area; notes never leave the source.
    assert set(mod._manifest(trusted / directory.relative_to(solver.root))) == {
        "input/prompt.txt", "eval/eval.sh", "eval/evaluate.py", "output/answer.json"}
    assert set(mod._manifest(work)) == {"input/prompt.txt", "skill/SKILL.md", "environment_access.md"}
    assert not any(a[0] == "docker" for a, _ in fake.calls)


def test_grader_output_mount_is_readonly_and_solver_never_sees_it(docker_solver):
    _, solver, fake, _, _ = docker_solver
    assert solve(docker_solver)["score"] == 1
    gold = (fake.attempt() / "trusted/data/task_groups/task_group_001/train_tasks/001/output").resolve()
    graders = [a for a, _ in fake.calls if "/trusted/eval/eval.sh" in a]
    # Sanity and final grading both get the task gold, read-only.
    assert len(graders) == 2
    for argv in graders:
        assert f"type=bind,source={gold},target=/trusted/output,readonly" in argv
        assert argv[argv.index("--network") + 1] == "none"
    solver_run = next(a for a, _ in fake.calls if a[:2] == ["docker", "create"])
    assert not any("/trusted/output" in arg or str(gold) in arg for arg in solver_run)
    staged = json.loads((fake.attempt() / "stage-manifest.json").read_text())
    assert not any(name.startswith("output/") for name in staged)


def test_task_without_gold_gets_no_output_mount(build_solver):
    fixture = build_solver({"task_group_001": GROUP_001_ENDPOINTS})
    _, solver, fake, _, _ = fixture
    task = next(iter(solver.tasks.values()))
    # A task with no reference answer: gold is an optional staged subset.
    (task.directory(solver.root) / "output/answer.json").unlink()
    hashes = {name: digest for name, digest in task.hashes.items() if not name.startswith("output/")}
    task = FrozenTask(task.group, task.subset, task.task_id, hashes)
    solver.tasks = {task.item_id: task}
    assert solve(fixture)["score"] == 1
    graders = [a for a, _ in fake.calls if "/trusted/eval/eval.sh" in a]
    assert len(graders) == 2 and not any("/trusted/output" in " ".join(a) for a in graders)


def test_adapter_canonicalizes_temp_parent_before_solver(host, monkeypatch):
    import rsi_kernel.adapters.gdpevo.adapter as adapter_module
    adapter = host[0]
    alias = adapter.work_dir.parent / "temp-alias"
    alias.symlink_to(adapter.work_dir.parent, target_is_directory=True)
    real_temporary = adapter_module.tempfile.TemporaryDirectory

    def aliased_temporary(*args, **kwargs):
        kwargs["dir"] = alias / adapter.work_dir.name
        return real_temporary(*args, **kwargs)

    def solver(candidate, item, inputs, prediction, env):
        assert inputs == inputs.resolve()
        assert prediction == prediction.resolve()
        assert not any(p.is_symlink() for p in (inputs, *inputs.parents))
        prediction.write_text('{"answer":"toy-ok"}')

    monkeypatch.setattr(adapter_module.tempfile, "TemporaryDirectory", aliased_temporary)
    adapter.solver = solver
    assert adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])[0]["score"] == 1


def test_staging_symlink_remains_a_specific_stop(docker_solver):
    _, solver, fake, incoming, prediction = docker_solver
    alias = incoming.parent / "alias"
    alias.symlink_to(incoming, target_is_directory=True)
    result = solver(Candidate({"SKILL.md": "skill"}, "text/plain"), "task_group_001/train/001",
                    alias, prediction, {"TASK_ENV_ENABLE_JUDGE": "0"})
    assert result["failure"]["reason"] == "staging_symlink"
    assert not any(a[0] == "docker" for a, _ in fake.calls)


def test_staging_overlap_is_a_specific_stop(docker_solver, monkeypatch):
    mod, solver, fake, incoming, _ = docker_solver
    monkeypatch.setattr(mod.secrets, "token_hex", lambda _: "fixed")
    result = solver(Candidate({"SKILL.md": "skill"}, "text/plain"), "task_group_001/train/001",
                    incoming, solver.evidence_dir / "gdp-fixed/answer.json", {"TASK_ENV_ENABLE_JUDGE": "0"})
    assert result["failure"]["reason"] == "staging_overlap"
    assert not any(a[0] == "docker" for a, _ in fake.calls)


# PR #24 accepted S2 findings: single fix round.
@pytest.mark.parametrize("role", ["agent", "grade", "sanity"])
def test_fix_timeout_stops_only_owned_container_without_deletion(docker_solver, monkeypatch, role):
    mod, _, fake, _, _ = docker_solver
    original = fake.__call__
    running = True
    def run(argv, **kwargs):
        nonlocal running
        name = next((a for a in argv if a.endswith("-" + role)), None)
        if role == "agent" and argv[:2] == ["docker", "start"]:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if role != "agent" and argv[:2] == ["docker", "run"] and name:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if argv[:2] in (["docker", "kill"], ["docker", "stop"]):
            running = False
        if argv[:2] == ["docker", "inspect"] and "{{.State.Running}}" in argv:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, str(running).lower().encode(), b"")
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    result = solve(docker_solver)
    scope = (fake.attempt() / "container-scope.txt").read_text().strip()
    stops = [a for a, _ in fake.calls if a[:2] in (["docker", "kill"], ["docker", "stop"])]
    assert len(stops) == 1 and stops[0][-1] == scope + "-" + role
    assert not running and result["failure"]["status"] == "STOP"
    assert any(a[:2] == ["docker", "inspect"] and "{{.State.Running}}" in a for a, _ in fake.calls)
    assert not any("rm" in a for a, _ in fake.calls)


def test_fix_ambient_proxy_config_and_env_never_reach_docker(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    ambient = fake.root.parent / "ambient-docker"
    ambient.mkdir()
    (ambient / "config.json").write_text(json.dumps({"proxies": {"default": {"httpProxy": "SYNTHETIC_PROXY"}}}))
    monkeypatch.setenv("DOCKER_CONFIG", str(ambient))
    monkeypatch.setenv("DOCKER_CONTEXT", "synthetic-colima")
    monkeypatch.setenv("DOCKER_HOST", "unix:///ignored.sock")
    monkeypatch.setenv("HTTP_PROXY", "SYNTHETIC_PROXY")
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_SECRET")
    original = fake.__call__
    def run(argv, **kwargs):
        if "context" in argv and "inspect" in argv:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, b'{"Host":"unix:///synthetic-colima.sock","SkipTLSVerify":false}', b"")
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    assert solve(docker_solver)["score"] == 1
    calls = [(a, k) for a, k in fake.calls if a[0] == "docker"]
    config = fake.attempt() / "docker-config"
    # Only plugin discovery survives (buildx); proxies/auth never do.
    assert [p.name for p in config.iterdir()] == ["config.json"]
    assert json.loads((config / "config.json").read_text()) == {"cliPluginsExtraDirs": [str(ambient / "cli-plugins")]}
    for argv, kwargs in calls:
        env = kwargs["env"]
        assert set(env) <= {"PATH", "HOME", "DOCKER_CONFIG", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_BUILDKIT"}
        assert env["DOCKER_CONFIG"] == str(config)
        assert env["DOCKER_BUILDKIT"] == "1"
        assert "SYNTHETIC_PROXY" not in json.dumps(env) and "SYNTHETIC_SECRET" not in json.dumps(env)
        assert "--build-arg" not in argv
        if "context" not in argv:
            assert env["DOCKER_HOST"] == "unix:///synthetic-colima.sock"
            assert "DOCKER_CONTEXT" not in env
    assert sum("context" in a and "inspect" in a for a, _ in calls) == 1


@pytest.mark.parametrize("sanity,expected", [(False, .8), (True, 1)])
def test_fix_normalization_used_by_final_and_sanity_graders(docker_solver, monkeypatch, sanity, expected):
    mod, _, fake, _, _ = docker_solver
    original = fake.__call__
    def run(argv, **kwargs):
        is_grader = "/trusted/eval/eval.sh" in argv
        is_sanity = "empty-prediction" in " ".join(argv)
        if is_grader and is_sanity == sanity:
            fake.calls.append((argv, kwargs))
            kwargs["stdout"].write(json.dumps({"normalized_score": 0 if sanity else .8, "total_score": .2}).encode())
            return subprocess.CompletedProcess(argv, 0, None, None)
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    assert solve(docker_solver)["score"] == expected


def test_fix_timeout_running_verification_fails_closed(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    fake.failure = "timeout"
    original = fake.__call__
    def run(argv, **kwargs):
        if "{{.State.Running}}" in argv:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, b"true", b"")
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    result = solve(docker_solver)
    assert result["failure"]["reason"] == "timeout_container_running"
    assert not any("rm" in a for a, _ in fake.calls)


def test_fix_explicit_daemon_host_uses_empty_config_without_context_lookup(docker_solver, monkeypatch):
    _, _, fake, _, _ = docker_solver
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("DOCKER_HOST", "unix:///explicit.sock")
    monkeypatch.setenv("DOCKER_API_VERSION", "SYNTHETIC_UNSUPPORTED")
    assert solve(docker_solver)["score"] == 1
    calls = [(a, k) for a, k in fake.calls if a[0] == "docker"]
    assert not any("context" in a for a, _ in calls)
    assert all(k["env"]["DOCKER_HOST"] == "unix:///explicit.sock" for _, k in calls)
    assert all("DOCKER_API_VERSION" not in k["env"] for _, k in calls)


def test_fix_malformed_context_endpoint_stops_before_builds(docker_solver, monkeypatch):
    mod, _, fake, _, _ = docker_solver
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    original = fake.__call__
    def run(argv, **kwargs):
        if "context" in argv:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, b'{"Host":"tcp://remote:2376","SkipTLSVerify":false}', b"")
        return original(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", run)
    result = solve(docker_solver)
    assert result["failure"]["reason"] == "docker_context_endpoint"
    assert not any("build" in a or "run" in a for a, _ in fake.calls)


def _run_environment_check(mod, health, judge, path="/health"):
    # Executes the real ENVIRONMENT_CHECK script against a local synthetic server.
    import http.server, subprocess, sys, threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def _reply(self, spec):
            code, body, location = spec
            self.send_response(code)
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._reply(health if self.path == path else (200, b'{"ok": true}', None))

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self._reply(judge if self.path == "/api/judge" else (404, b"", None))

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        script = mod.ENVIRONMENT_CHECK.replace(
            "http://task-env:PORT", f"http://127.0.0.1:{server.server_port}").replace("HEALTH_PATH", path)
        return subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=30)
    finally:
        server.shutdown()


def test_environment_check_script_uses_the_group_health_route():
    # Upstream guide: the health endpoint is documented per environment.
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    path = mod._health_path(GROUP_004_ENDPOINTS)
    ok = _run_environment_check(mod, (200, b'{"ok": true}', None), (404, b"", None), path=path)
    assert ok.returncode == 0 and json.loads(ok.stdout)["health"] == {"ok": True}
    # The derived route is the one probed: a failing /api/health fails the check.
    assert _run_environment_check(mod, (503, b"", None), (404, b"", None), path=path).returncode != 0


@pytest.mark.parametrize("endpoints,expected", [
    (GROUP_001_ENDPOINTS, "/health"),
    (GROUP_004_ENDPOINTS, "/api/health"),
    (BOTH_HEALTH_ENDPOINTS, "/health"),
])
def test_health_path_comes_from_the_group_endpoints(endpoints, expected):
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    assert mod._health_path(endpoints) == expected


def test_health_path_absent_is_a_stop():
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    with pytest.raises(mod._Stop) as error:
        mod._health_path("GET /api/items\nPOST /api/judge\n")
    assert error.value.reason == "env_health_path"


def test_access_note_health_only_group_is_byte_identical():
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    assert mod._access_note("task_group_001", GROUP_001_ENDPOINTS) == (
        "Environment base URL: http://task-env:9001/\n"
        "No credentials are required.\n"
        "Allowed GET endpoints:\n"
        "GET /api/manifest\n"
        "GET /api/events\n"
        "Use this base URL instead of any localhost URL in the task inputs.\n")


def test_access_note_omits_both_health_routes():
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    note = mod._access_note("task_group_005", BOTH_HEALTH_ENDPOINTS)
    assert "/health" not in note and "/api/health" not in note
    assert "GET /api/items" in note and "/api/judge" not in note


def test_per_group_health_route_reaches_healthcheck_and_check_script(build_solver):
    # Groups 004/008 serve only /api/health; the Docker healthcheck must use it.
    fixture = build_solver({"task_group_004": GROUP_004_ENDPOINTS})
    _, _, fake, _, _ = fixture
    assert solve(fixture, item_id="task_group_004/train/001")["score"] == 1
    env = next(a for a, _ in fake.calls if "TASK_ENV_ENABLE_JUDGE=0" in a)
    assert "127.0.0.1:9004/api/health" in " ".join(env)
    assert "127.0.0.1:9004/health" not in " ".join(env)
    check = next(a for a, _ in fake.calls if "python3" in a and a[:2] == ["docker", "run"])
    assert 'base="http://task-env:9004"' in check[-1] and 'base+"/api/health"' in check[-1]
    note = (fake.attempt() / "work/environment_access.md").read_text()
    assert "GET /api/items" in note and "health" not in note


def test_environment_check_script_contract():
    # No docker_solver fixture: it replaces subprocess.run with the Docker fake.
    from rsi_kernel.adapters.gdpevo import solver_docker as mod
    ok = _run_environment_check(mod, (200, b'{"ok": true}', None), (404, b"", None))
    assert ok.returncode == 0 and json.loads(ok.stdout) == {"health": {"ok": True}, "judge_http_status": 404}
    binary = _run_environment_check(mod, (200, b"\xff\xfeok", None), (404, b"", None))
    assert binary.returncode == 0 and json.loads(binary.stdout)["judge_http_status"] == 404
    assert _run_environment_check(mod, (503, b"", None), (404, b"", None)).returncode != 0
    assert _run_environment_check(mod, (302, b"", "/elsewhere"), (404, b"", None)).returncode != 0
    assert _run_environment_check(mod, (200, b"{}", None), (200, b"{}", None)).returncode != 0
    assert _run_environment_check(mod, (200, b"{}", None), (302, b"", "/missing")).returncode != 0
