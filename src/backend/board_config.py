"""
Board Configuration
===================
Load board definitions from boards.json.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class BoardConfig:
    name: str
    modules: int
    reset_can_ids: List[int] = field(default_factory=list)


def load_boards(path: Path | None = None) -> List[BoardConfig]:
    """Load board definitions from a JSON file.

    Falls back to boards.json next to the project root.
    """
    if path is None:
        path = Path(__file__).resolve().parents[2] / "boards.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    boards: List[BoardConfig] = []
    for entry in raw:
        ids = [int(x, 16) for x in entry["reset_can_ids"]]
        boards.append(BoardConfig(
            name=entry["name"],
            modules=entry["modules"],
            reset_can_ids=ids,
        ))
    return boards
