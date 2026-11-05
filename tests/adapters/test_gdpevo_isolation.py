from dataclasses import replace

import pytest

from rsi_kernel.isolation import ProposerRuntime

# Each issue #3 exclusion is exercised; fixture names are not real GDPevo data.
EXCLUSIONS = [
    "data/task_groups/toy/test_tasks/001/input/prompt.txt",
    "data/task_groups/toy/train_tasks/001/output/answer.json",
    "data/task_groups/toy/train_tasks/001/eval/eval.sh",
    "data/task_groups/toy/train_tasks/001/notes/notes.md",
    "data/task_groups/toy/env/judge_answers/answer.json",
    "experiments/report.yaml", "data_construction/data.json", "site/index.html",
    *[f"evaluation/eval_workspace/toy/{name}/secret" for name in
      ("task_group", "runs", "original_traces", "scratch", "report", "skills")],
    "data/task_groups/toy/train_tasks/002/input/prompt.txt",
]


@pytest.mark.parametrize("relative", EXCLUSIONS)
@pytest.mark.parametrize("mount", ["dev_data_dir", "output_dir"])
def test_gdpevo_e0_protected_mounts_denied(host, relative, mount):
    adapter = host[0]
    staged = adapter.work_dir.parent / "staged-dev"
    output = adapter.work_dir.parent / "proposal-output"
    runtime = adapter.proposer_runtime("fake-image", staged, output)
    runtime = replace(runtime, **{mount: adapter.root / relative})
    with pytest.raises(PermissionError, match="protected"):
        runtime.docker_argv(["true"])


@pytest.mark.parametrize("which", ["ancestor", "direct_symlink", "nested_symlink"])
def test_generic_denylist_rejects_ancestor_and_symlink_mounts(tmp_path, which):
    protected = tmp_path / "protected"
    protected.mkdir()
    staged = tmp_path / "staged"
    staged.mkdir()
    if which == "ancestor":
        source = tmp_path
    elif which == "direct_symlink":
        source = tmp_path / "link"
        source.symlink_to(protected, target_is_directory=True)
    else:
        (staged / "leak").symlink_to(protected, target_is_directory=True)
        source = staged
    runtime = ProposerRuntime("fake-image", source, tmp_path.parent / "safe-output", deny_paths=(protected,))
    with pytest.raises(PermissionError, match="protected"):
        runtime.docker_argv(["true"])


def test_staged_proposer_keeps_no_network_and_judge_off(host):
    adapter = host[0]
    runtime = adapter.proposer_runtime("fake-image", adapter.work_dir.parent / "staged", adapter.work_dir.parent / "out")
    argv = runtime.docker_argv(["python", "-c", "pass"])
    assert argv[argv.index("--network") + 1] == "none"
    assert "TASK_ENV_ENABLE_JUDGE=0" in argv
    assert argv.count("--mount") == 2
    with pytest.raises(ValueError, match="judge"):
        runtime.docker_argv(["true"], {"TASK_ENV_ENABLE_JUDGE": "1"})


@pytest.mark.parametrize("value", ["1", "true", "yes", "on"])
def test_judge_enabling_config_refused(api, value):
    with pytest.raises(ValueError, match="judge"):
        api.judge_off({"TASK_ENV_ENABLE_JUDGE": value})


def test_judge_off_does_not_mutate_config(api):
    original = {"TASK_ENV_ENABLE_JUDGE": "0"}
    assert dict(api.judge_off(original)) == original
    assert original == {"TASK_ENV_ENABLE_JUDGE": "0"}
