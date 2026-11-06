"""S5 pilot driver for the memory/skill-library artifact (issue #6, addendum #35).

The kernel is unchanged; this module only supplies the S5 hooks to the S4 driver.
Library hooks: the champion is a JSON library, the adapter renders it for the
traced skill, and the host validates drafts into candidates for paired dev
evaluation without a D4 veto (#45). The spend cap remains 45; its former three
D4 slots are unused headroom.

    python -m rsi_kernel.adapters.gdpevo_memory.pilot optimise --config C --group G
    python -m rsi_kernel.adapters.gdpevo_memory.pilot final --config C
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...candidate import Candidate
from ..gdpevo import pilot
from ..gdpevo.pilot import PilotStop
from .adapter import GDPevoMemoryAdapter
from .library import read_library, render_skill
from .proposer import admit_draft, draft


# Addendum "Spend cap": 36 solver + 3 proposer + 3 D2 + 3 unused D4 slots = 45.
# D4 is retired on this path (#45); its 3 slots remain unused headroom.
SPEND_CAP = 45


def _champion(config):
    """Load the seed library from the pilot's own candidate serialization (``_selected``).

    Shape: ``{"components": {...}, "media_type": "application/json", "parent_ids": []}``,
    the same fields ``campaign.json`` stores for a selected candidate. The empty seed
    is ``{"components": {}, "media_type": "application/json"}`` (addendum §1).
    """
    if pilot._sha(config["path"]) != config["sha256"]:
        raise PilotStop("champion hash mismatch")
    try:
        state = json.loads(Path(config["path"]).read_text(encoding="utf-8"))
        champion = Candidate(state["components"], state["media_type"], tuple(state.get("parent_ids", ())))
        read_library(champion)  # the same validation the adapter will apply
        return champion
    except (OSError, ValueError, KeyError, TypeError):
        raise PilotStop("champion library unreadable") from None


LIBRARY = pilot.Hooks(load_champion=_champion, adapter_class=GDPevoMemoryAdapter,
                      render=render_skill, module="rsi_kernel.adapters.gdpevo_memory.pilot",
                      result_key="draft", container=draft, admit=admit_draft, spend_cap=SPEND_CAP)


def main(argv=None) -> int:
    return pilot.main(argv, hooks=LIBRARY)


if __name__ == "__main__":
    sys.exit(main())
