from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    rules_version: str

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("TRENDS_DATA_DIR", ".local/trends-analyzer")).resolve()
        return cls(
            data_dir=data_dir,
            rules_version=os.getenv("RULES_VERSION", "rules-mvp-0.1"),
        )
