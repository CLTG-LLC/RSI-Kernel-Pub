"""GDPevo proposer isolation, using the kernel launcher rather than another one.

Design §7 (S3) forbids source-repository mounts; only independently staged dev inputs
and projected dev reflection records may be mounted. Denying the entire source
root covers every issue #3 exclusion, even paths not present yet and newly added
adjudication inputs. The synthetic Docker test verifies this staging boundary
and the standalone GEPA proposer; it does not validate a live host solver.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from ...isolation import ProposerRuntime


def judge_off(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    """Require explicit off, not upstream's train-only judge (design §7, S3)."""
    if (env or {}).get("TASK_ENV_ENABLE_JUDGE", "0") != "0":
        raise ValueError("upstream judge must be disabled")
    return MappingProxyType({**(env or {}), "TASK_ENV_ENABLE_JUDGE": "0"})


@dataclass(frozen=True)
class GDPevoProposerRuntime(ProposerRuntime):
    def docker_argv(self, command: Sequence[str], env: Mapping[str, str] | None = None) -> list[str]:
        return super().docker_argv(command, judge_off(env))
