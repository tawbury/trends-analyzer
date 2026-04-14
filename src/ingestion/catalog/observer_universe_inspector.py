from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ObserverUniverseFinding:
    path: Path
    role: str
    reusable: bool
    reason: str


class ObserverUniverseInspector:
    def __init__(self, *, observer_root: Path) -> None:
        self.observer_root = observer_root

    def inspect(self) -> list[ObserverUniverseFinding]:
        candidates = [
            (
                self.observer_root / "src" / "universe" / "symbol_api.py",
                "symbol collection fallback strategy",
                True,
                "Reusable as design reference; depends on Observer engine and runtime paths.",
            ),
            (
                self.observer_root / "src" / "universe" / "symbol_generator.py",
                "symbol artifact generation",
                False,
                "Tightly coupled to Observer paths, health files, and collection state.",
            ),
            (
                self.observer_root / "src" / "universe" / "universe_manager.py",
                "QTS universe snapshot generation",
                False,
                "Applies previous-close min_price filtering and Observer snapshot policies.",
            ),
            (
                self.observer_root / "data" / "symbols",
                "generated symbol artifacts",
                True,
                "Usable only as a temporary bridge when files exist and freshness is acceptable.",
            ),
            (
                self.observer_root / "data" / "universe",
                "filtered universe artifacts",
                False,
                "Contains QTS-oriented filtered snapshots and can exclude low-priced symbols.",
            ),
        ]
        return [
            ObserverUniverseFinding(path=path, role=role, reusable=reusable, reason=reason)
            for path, role, reusable, reason in candidates
        ]
