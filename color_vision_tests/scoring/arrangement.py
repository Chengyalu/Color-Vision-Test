from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class DiscColor:
    index: int
    x: float
    y: float


@dataclass
class Vector:
    start: DiscColor
    end: DiscColor

    @property
    def u(self) -> float:
        return self.end.x - self.start.x

    @property
    def v(self) -> float:
        return self.end.y - self.start.y


class MomentOfInertia:
    def __init__(self, spots: Sequence[DiscColor]):
        self.spots = list(spots)
        self.c_index = None
        self.s_index = None
        self.tes = None
        self.majorRadius = 0.0
        self.minorRadius = 0.0

        self.vectors = self.calculate_vectors()
        self.angle = self.calculate_angle()
        self.moments = self.calculate_moments()

    def calculate_vectors(self) -> List[Vector]:
        vecs: List[Vector] = []
        for i in range(1, len(self.spots)):
            vecs.append(Vector(self.spots[i - 1], self.spots[i]))
        return vecs

    def calculate_angle(self) -> float:
        if not self.vectors:
            return 0.0

        sum1 = 0.0
        sum2 = 0.0
        for vector in self.vectors:
            sum1 += 2 * vector.u * vector.v
            sum2 += vector.u ** 2 - vector.v ** 2

        if sum2 == 0:
            return 0.0
        return math.atan(sum1 / sum2) / 2

    def calculate_moments(self):
        if not self.vectors:
            self.majorRadius = 0.0
            self.minorRadius = 0.0
            return [0.0, 0.0]

        moms = [0.0, 0.0]
        angle1 = self.angle
        angle2 = angle1 + (math.pi / 2)

        for vector in self.vectors:
            moms[0] += (vector.v * math.cos(angle1) - vector.u * math.sin(angle1)) ** 2
            moms[1] += (vector.v * math.cos(angle2) - vector.u * math.sin(angle2)) ** 2

        moms[0] = math.sqrt(moms[0] / len(self.vectors))
        moms[1] = math.sqrt(moms[1] / len(self.vectors))

        if moms[0] > moms[1]:
            self.majorRadius = moms[0]
            self.minorRadius = moms[1]
        else:
            self.majorRadius = moms[1]
            self.minorRadius = moms[0]

        return moms

    def calculate_c_index(self, calculated_max_radius: float) -> float:
        if calculated_max_radius == 0:
            return 0.0
        return self.majorRadius / calculated_max_radius

    def calculate_s_index(self) -> float:
        if self.minorRadius == 0:
            return float("inf")
        return self.majorRadius / self.minorRadius

    def calculate_tes(self) -> float:
        return math.sqrt(self.majorRadius ** 2 + self.minorRadius ** 2)


def _build_spots_from_order(order: List[int], coordinates: Dict[int, tuple[float, float]]) -> List[DiscColor]:
    spots: List[DiscColor] = []
    for idx in order:
        if idx not in coordinates:
            raise KeyError(f"Missing coordinate for cap index {idx}")
        x, y = coordinates[idx]
        spots.append(DiscColor(index=idx, x=x, y=y))
    return spots


def calculate_max_radius_from_reference(reference_order: List[int], coordinates: Dict[int, tuple[float, float]]) -> float:
    """
    用参考顺序计算 calculated_max_radius。
    一般传入正确顺序 [0,1,2,...,15]。
    """
    ref_spots = _build_spots_from_order(reference_order, coordinates)
    moi = MomentOfInertia(ref_spots)
    return moi.majorRadius


def arrangement_summary(
    order: List[int],
    coordinates: Dict[int, tuple[float, float]],
    calculated_max_radius: float,
) -> Dict[str, object]:
    expected = sorted(coordinates.keys())
    positional_errors = sum(1 for a, b in zip(order, expected) if a != b)

    adjacent_jumps = [abs(order[i + 1] - order[i]) for i in range(len(order) - 1)]

    spots = _build_spots_from_order(order, coordinates)
    moi = MomentOfInertia(spots)

    c_index = moi.calculate_c_index(calculated_max_radius)
    s_index = moi.calculate_s_index()
    tes = moi.calculate_tes()

    return {
        "response_order": order,
        "expected_order": expected,
        "positional_errors": positional_errors,
        "adjacent_jumps": adjacent_jumps,
        "total_adjacent_jump": sum(adjacent_jumps) if adjacent_jumps else 0,
        "max_adjacent_jump": max(adjacent_jumps) if adjacent_jumps else 0,
        "major_radius": round(moi.majorRadius, 6),
        "minor_radius": round(moi.minorRadius, 6),
        "C-INDEX": round(c_index, 6),
        "TES": round(tes, 6),
        "S-INDEX": round(s_index, 6) if math.isfinite(s_index) else "inf",
    }