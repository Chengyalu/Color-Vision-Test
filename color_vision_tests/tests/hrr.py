from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HRRPlate:
    plate_id: str
    positions: list[str]   # [top-left, top-right, bottom-left, bottom-right]


class HRRTest:
    def __init__(self, plates: list[HRRPlate], assets_dir: Path):
        self.plates = plates
        self.assets_dir = assets_dir

    @classmethod
    def create_default(cls):
        root = Path(__file__).resolve().parent.parent
        key_path = root / "data" / "hrr_keys.json"
        assets_dir = root / "assets" / "hrr"

        with open(key_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        plates = [
            HRRPlate(
                plate_id=item["plate_id"],
                positions=item["positions"],
            )
            for item in raw
        ]
        return cls(plates=plates, assets_dir=assets_dir)

    def get_image_path(self, plate: HRRPlate) -> Path:
        for ext in [".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG"]:
            p = self.assets_dir / f"{plate.plate_id}{ext}"
            if p.exists():
                return p
        return self.assets_dir / f"{plate.plate_id}.png"

    def find_icon_path(self, stem: str) -> Path | None:
        candidates = [
            stem,
            stem.lower(),
            stem.upper(),
        ]
        for name in candidates:
            for ext in [".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG"]:
                p = self.assets_dir / f"{name}{ext}"
                if p.exists():
                    return p
        return None