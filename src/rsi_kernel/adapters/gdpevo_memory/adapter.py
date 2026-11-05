"""Library host contract; reuse GDPevo staging, grading, splits and isolation.

The solver's staged SKILL.md must hash-match the deterministic rendered library
both before and after invocation. Failure raises within GDPevo's existing solver
boundary, producing score=None/failure.reason=solver (blocks paired acceptance).
Precedent: deepseek-harness@fcc0ad46 packages/skill/skill/src/index.ts:390–458
(catalog precedence, deduplication and file watchers can alter loaded skills).
"""

from pathlib import Path

from ...candidate import Candidate
from ..gdpevo.adapter import GDPevoAdapter, validate_skill
from .library import read_library, render_skill


def _verify_staged(path: Path, rendered: Candidate) -> None:
    if (path.is_symlink() or not path.is_file()
            or Candidate({"SKILL.md": path.read_bytes()}, "text/plain").id != rendered.id):
        raise ValueError("staged skill hash mismatch")


class GDPevoMemoryAdapter(GDPevoAdapter):
    def __init__(self, *, champion: Candidate, solver, **host_config):
        read_library(champion)
        self._library_champion = champion
        self._memory_solver = solver
        super().__init__(champion=render_skill(champion), solver=self._solve, **host_config)

    def get_artifact(self) -> Candidate:
        read_library(self._library_champion)
        return self._library_champion

    def evaluate(self, candidate: Candidate, item_ids) -> list[dict]:
        return super().evaluate(render_skill(candidate), item_ids)

    def _solve(self, rendered, item_id, input_dir, prediction, env):
        staged = input_dir.parent / "SKILL.md"
        staged.write_bytes(validate_skill(rendered).encode("utf-8"))
        _verify_staged(staged, rendered)
        self._memory_solver(rendered, item_id, input_dir, prediction, env)
        _verify_staged(staged, rendered)

    def apply(self, approved_candidate_hash: str) -> None:
        known = {self.get_artifact().id} | {record["id"] for record in self.archive.public_view().candidates()}
        if approved_candidate_hash not in known:
            raise ValueError("unknown candidate hash")
        self.archive.record_decision({"candidate_id": approved_candidate_hash, "mode": "record-only"})
