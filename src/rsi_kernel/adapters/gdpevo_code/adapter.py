"""T3 exact-key and frozen-parent contract; reuse S4 evaluation and record-only apply."""

from ...candidate import Candidate, content_id
from ..gdpevo.adapter import GDPevoAdapter

COMPONENT = "solver.py"


def validate_code(candidate: Candidate, champion: Candidate | None = None) -> str:
    if candidate.media_type != "text/plain" or set(candidate.components) != {COMPONENT}:
        raise ValueError("only the solver.py text component is admitted")
    if content_id(candidate.components) != candidate.id:
        raise ValueError("candidate hash mismatch")
    if champion is not None:
        validate_code(champion)
        if champion.parent_ids:
            raise ValueError("frozen champion must be a root artifact")
        parents = () if candidate.id == champion.id else (champion.id,)
        if candidate.parent_ids != parents:
            raise ValueError("candidate parent mismatch")
    value = candidate.components[COMPONENT]
    text = value.decode("utf-8") if isinstance(value, bytes) else value
    if not text.strip() or "\0" in text:
        raise ValueError("solver source must be non-empty UTF-8 text")
    return text


class GDPevoCodeAdapter(GDPevoAdapter):
    def __init__(self, *, champion: Candidate, **host_config):
        validate_code(champion, champion)
        self._code_champion = champion
        super().__init__(champion=champion, **host_config)

    def _validate_candidate(self, candidate):
        return validate_code(candidate, self._code_champion)
