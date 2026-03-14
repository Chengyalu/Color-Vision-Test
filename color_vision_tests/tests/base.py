from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Tuple

RGB = Tuple[int, int, int]


@dataclass
class ArrangementTestBase:
    name: str
    colors: List[RGB]
    anchor_index: int = 0
    shuffled_order: List[int] = field(default_factory=list)

    @classmethod
    def from_json(cls, name: str, path: Path, anchor_index: int = 0):
        data = json.loads(path.read_text(encoding='utf-8'))
        colors = [tuple(item) for item in data]
        return cls(name=name, colors=colors, anchor_index=anchor_index)

    def start(self, seed: int | None = None) -> List[int]:
        indices = list(range(len(self.colors)))
        movable = [idx for idx in indices if idx != self.anchor_index]
        rng = random.Random(seed)
        rng.shuffle(movable)
        self.shuffled_order = [self.anchor_index] + movable
        return self.shuffled_order

    def swap_positions(self, pos_a: int, pos_b: int) -> None:
        if pos_a == pos_b:
            return
        if pos_a == 0 or pos_b == 0:
            return
        self.shuffled_order[pos_a], self.shuffled_order[pos_b] = self.shuffled_order[pos_b], self.shuffled_order[pos_a]

    def get_rgb_sequence(self) -> List[RGB]:
        if not self.shuffled_order:
            self.start()
        return [self.colors[idx] for idx in self.shuffled_order]

    def get_response_order(self) -> List[int]:
        return list(self.shuffled_order)

    def get_target_order(self) -> List[int]:
        return list(range(len(self.colors)))
