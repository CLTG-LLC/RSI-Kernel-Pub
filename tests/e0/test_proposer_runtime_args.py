from pathlib import Path

import pytest

from rsi_kernel.isolation import ProposerRuntime


def test_argv_has_no_network_allowlisted_env_and_only_two_mounts(tmp_path):
    rt = ProposerRuntime(image="python:3.12-slim", dev_data_dir=tmp_path / "dev", output_dir=tmp_path / "out")
    argv = rt.docker_argv(["python", "-c", "pass"], env={"RSI_RUN_ID": "r1"})
    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    envs = [argv[i + 1] for i, a in enumerate(argv) if a == "-e"]
    assert envs == ["RSI_RUN_ID=r1"]
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "--mount"]
    assert mounts == [
        f"type=bind,source={(tmp_path / 'dev').resolve()},target=/data/dev,readonly",
        f"type=bind,source={(tmp_path / 'out').resolve()},target=/out",
    ]
    assert not any(a in ("-v", "--volume", "--env-file", "--privileged") for a in argv)
    assert argv[-3:] == ["python", "-c", "pass"]


@pytest.mark.parametrize("name", ["", "A=B", "1BAD", "a b"])
def test_invalid_env_names_rejected(tmp_path, name):
    rt = ProposerRuntime("img", tmp_path / "dev", tmp_path / "out")
    with pytest.raises(ValueError):
        rt.docker_argv(["true"], env={name: "x"})


def test_mount_source_with_comma_rejected(tmp_path):
    with pytest.raises(ValueError):
        ProposerRuntime("img", tmp_path / "a,b", tmp_path / "out").docker_argv(["true"])


def test_same_dir_for_dev_and_output_rejected(tmp_path):
    with pytest.raises(ValueError):
        ProposerRuntime("img", Path(tmp_path), Path(tmp_path)).docker_argv(["true"])


@pytest.mark.parametrize("dev,out", [("root/dev", "root"), ("root", "root/out")])
def test_nested_dev_and_output_dirs_rejected(tmp_path, dev, out):
    # A writable /out that contains dev (or vice versa) would bypass the read-only
    # dev mount and expose protected siblings (review PR5 finding 1).
    with pytest.raises(ValueError):
        ProposerRuntime("img", tmp_path / dev, tmp_path / out).docker_argv(["true"])
