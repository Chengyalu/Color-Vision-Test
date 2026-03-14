from pathlib import Path

import colour

from .base import ArrangementTestBase
from color_vision_tests.scoring.arrangement import calculate_max_radius_from_reference


def rgb_to_luv_uv(rgb):
    rgb_norm = [c / 255.0 for c in rgb]
    xyz = colour.sRGB_to_XYZ(rgb_norm)
    luv = colour.XYZ_to_Luv(xyz)
    return float(luv[1]), float(luv[2])


class FMD15Test(ArrangementTestBase):
    @classmethod
    def create_default(cls):
        path = Path(__file__).resolve().parent.parent / "data" / "fmd15_colors.json"
        test = cls.from_json(name="FM D-15", path=path, anchor_index=0)

        test.coordinates = {
            i: rgb_to_luv_uv(color)
            for i, color in enumerate(test.colors)
        }

        test.calculated_max_radius = calculate_max_radius_from_reference(
            list(range(len(test.colors))),
            test.coordinates,
        )
        return test