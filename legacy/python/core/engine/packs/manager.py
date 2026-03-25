import os
from typing import List, Optional

from engine.packs.pack import Pack, load_pack_from_yaml
from engine.packs.detector import suggest_packs


class PackManager:
    """Manages loading, enabling, and disabling of packs."""

    def __init__(self, packs_dirs: List[str]):
        self._packs: dict[str, Pack] = {}
        for d in packs_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if fname.endswith((".yaml", ".yml")):
                    pack = load_pack_from_yaml(os.path.join(d, fname))
                    if pack is not None and pack.name:
                        self._packs[pack.name] = pack

    @property
    def available_packs(self) -> List[Pack]:
        """Return all loaded packs."""
        return list(self._packs.values())

    @property
    def enabled_packs(self) -> List[Pack]:
        """Return packs where enabled=True."""
        return [p for p in self._packs.values() if p.enabled]

    def enable(self, name: str) -> bool:
        """Enable pack by name. Idempotent. Returns True if found."""
        pack = self._packs.get(name)
        if pack is None:
            return False
        pack.enabled = True
        return True

    def disable(self, name: str) -> bool:
        """Disable pack by name. Idempotent. Returns True if found."""
        pack = self._packs.get(name)
        if pack is None:
            return False
        pack.enabled = False
        return True

    def suggest(self, project_root: str) -> List[Pack]:
        """Delegate to detector.suggest_packs."""
        return suggest_packs(project_root, self.available_packs)

    def get(self, name: str) -> Optional[Pack]:
        """Return pack by name or None."""
        return self._packs.get(name)
