"""Harness-code pilot: whole-file GEPA rewrite, S4 driver/rules unchanged."""

import sys
from pathlib import Path

from ...candidate import Candidate
from ..gdpevo import pilot
from ..gdpevo.proposer import propose
from .adapter import COMPONENT, GDPevoCodeAdapter, validate_code
from .solver_docker import CodeDockerSolver, CodeLimits

INSTRUCTION = (
    "\nRewrite the complete Python solver.py file, not a diff. "
    "It receives a UTF-8 task prompt on stdin and returns only a JSON object "
    "with exactly one non-empty string field, prompt. It can read /work/input, "
    "/work/skill/SKILL.md and /work/environment_access.md. "
    "Model/provider configuration, invocation, grading and metering are trusted "
    "and not editable. Return the entire replacement source in a code block."
)


def render(champion):
    return Candidate({"SKILL.md": validate_code(champion)}, "text/plain")


def rewrite(rendered, records, splits, model):
    candidate = propose(rendered, records, splits, lambda prompt: model(prompt + INSTRUCTION))
    return None if candidate is None else candidate.components["SKILL.md"]


def admit(champion, payload, decider, dev_results):
    validate_code(champion, champion)
    if payload is None:
        return None
    candidate = Candidate({COMPONENT: payload}, "text/plain", parent_ids=(champion.id,))
    if candidate.id == champion.id:
        return None
    validate_code(candidate, champion)
    return candidate


def load_champion(config):
    path = Path(config["path"])
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise pilot.PilotStop("symlink in champion path")
    if pilot._sha(path) != config["sha256"]:
        raise pilot.PilotStop("champion hash mismatch")
    champion = Candidate({COMPONENT: path.read_bytes()}, "text/plain")
    validate_code(champion, champion)
    # Text serialization is used by the existing campaign writer.
    return Candidate({COMPONENT: validate_code(champion)}, "text/plain")


def solver_factory(config, group, **kwargs):
    """Required config: code_limits and fixed skills[group] {path, sha256}."""
    return CodeDockerSolver(champion=load_champion(config["champions"][group]),
                            skill=pilot._champion(config["skills"][group]),
                            limits=CodeLimits(**config["code_limits"]), **kwargs)


CODE = pilot.Hooks(load_champion=load_champion, adapter_class=GDPevoCodeAdapter,
                   render=render, module="rsi_kernel.adapters.gdpevo_code.pilot",
                   result_key="source", container=rewrite, admit=admit,
                   spend_cap=pilot.SPEND_CAP, solver_factory=solver_factory)


def main(argv=None):
    return pilot.main(argv, hooks=CODE)


if __name__ == "__main__":
    sys.exit(main())
