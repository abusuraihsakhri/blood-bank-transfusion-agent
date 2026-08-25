#!/usr/bin/env python3
"""
TransfusionGuard — MTP Ratio Tracker, Cold Chain Excursion Monitor,
Antibody Panel Auto-Interpreter
Massive transfusion 1:1:1 ratio compliance, AABB cold-chain excursion rules
with cumulative out-of-storage time, and panel-cell reaction pattern scoring.

Zero-dependency. Author: Dr. Abu Suraih Sakhri. License: MIT.
"""
import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ----------------------------- MTP tracker ---------------------------------

MTP_TARGET_RATIO = (1.0, 1.0, 1.0)   # pRBC : FFP : Platelets(6-packs)


@dataclass
class MTPEvent:
    event_id: str
    activated_at: str = ""
    prbc_units: int = 0
    ffp_units: int = 0
    platelet_sixpacks: int = 0

    def issue(self, product: str, units: int = 1) -> None:
        if product == "prbc":
            self.prbc_units += units
        elif product == "ffp":
            self.ffp_units += units
        elif product == "platelets":
            self.platelet_sixpacks += units

    def status(self) -> Dict[str, Any]:
        denom = max(self.prbc_units, 1)
        ffp_ratio = self.ffp_units / denom
        plt_ratio = self.platelet_sixpacks / denom
        # compliance = how close the weakest axis is to target 1:1
        compliance = min(ffp_ratio, plt_ratio, 1.0)
        gaps = {
            "ffp_deficit_units": max(0, self.prbc_units - self.ffp_units),
            "platelet_deficit_units": max(0, self.prbc_units - self.platelet_sixpacks),
        }
        return {
            "event_id": self.event_id,
            "products": {"pRBC": self.prbc_units, "FFP": self.ffp_units,
                         "Platelets_6pk": self.platelet_sixpacks},
            "current_ratio_f_fp_prbc": round(ffp_ratio, 2),
            "current_ratio_plt_prbc": round(plt_ratio, 2),
            "target_ratio": list(MTP_TARGET_RATIO),
            "ratio_compliance_pct": round(100 * compliance, 1),
            "gaps": gaps,
            "recommendation": ("Ratio on target; continue balanced resuscitation"
                               if compliance >= 0.8 else
                               f"Release {max(gaps.values())} unit(s) of lagging component "
                               "to restore 1:1:1"),
        }


# --------------------------- Cold chain monitor -----------------------------

STORAGE_RANGES = {
    "rbc_refrigerator": {"min_c": 1.0, "max_c": 6.0},
    "plasma_freezer": {"min_c": -30.0, "max_c": -18.0},
    "platelet_incubator": {"min_c": 20.0, "max_c": 24.0},
}
MAX_CUMULATIVE_EXCURSION_MIN = {"rbc_refrigerator": 30.0}   # AABB time-out-of-storage


@dataclass
class TempReading:
    sensor_id: str
    temperature_c: float
    minutes_elapsed: float   # monotonic sample clock in minutes


class ColdChainMonitor:
    def __init__(self, storage_type: str):
        if storage_type not in STORAGE_RANGES:
            raise ValueError(f"unknown storage type {storage_type}")
        self.storage_type = storage_type
        self.range_ = STORAGE_RANGES[storage_type]
        self.readings: List[TempReading] = []
        self.excursions: List[Dict[str, Any]] = []
        self._open_excursion: Optional[Dict[str, Any]] = None

    def ingest(self, r: TempReading) -> Dict[str, Any]:
        in_range = self.range_["min_c"] <= r.temperature_c <= self.range_["max_c"]
        result: Dict[str, Any] = {"sensor_id": r.sensor_id, "temp_c": r.temperature_c,
                                  "in_range": in_range}
        if not in_range:
            if self._open_excursion is None:
                self._open_excursion = {"started_min": r.minutes_elapsed,
                                        "peak_temp_c": r.temperature_c}
            else:
                self._open_excursion["peak_temp_c"] = (
                    max(self._open_excursion["peak_temp_c"], r.temperature_c)
                    if self.storage_type != "plasma_freezer" else
                    min(self._open_excursion["peak_temp_c"], r.temperature_c))
        else:
            if self._open_excursion is not None:
                dur = r.minutes_elapsed - self._open_excursion["started_min"]
                exc = {**self._open_excursion, "ended_min": r.minutes_elapsed,
                       "duration_min": round(dur, 1)}
                self.excursions.append(exc)
                self._open_excursion = None
                result["excursion_closed"] = exc
        self.readings.append(r)
        return result

    def status(self) -> Dict[str, Any]:
        cum = sum(e["duration_min"] for e in self.excursions)
        limit = MAX_CUMULATIVE_EXCURSION_MIN.get(self.storage_type, 120.0)
        quarantined = cum > limit
        open_now = None
        if self._open_excursion:
            last_t = self.readings[-1].minutes_elapsed if self.readings else 0
            open_now = {**self._open_excursion, "ongoing_min": round(last_t - self._open_excursion["started_min"], 1)}
            cum_open = cum + open_now["ongoing_min"]
            quarantined = quarantined or cum_open > limit
        return {
            "storage_type": self.storage_type,
            "acceptable_range_c": [self.range_["min_c"], self.range_["max_c"]],
            "total_excursions": len(self.excursions),
            "cumulative_out_of_range_min": round(cum, 1),
            "currently_out_of_range": bool(open_now),
            "open_excursion": open_now,
            "units_require_quarantine": quarantined,
            "rule": f"quarantine if cumulative excursion > {limit} min",
        }


# ----------------------- Antibody panel interpreter -------------------------

ANTIGEN_ORDER = ["D", "C", "E", "c", "e", "K", "Fya", "Jka", "S"]

ANTIBODY_PATTERNS = {
    "Anti-D":  {"D": "+", "C": "-", "E": "-", "c": "-", "e": "-", "K": "-", "Fya": "-", "Jka": "-", "S": "-"},
    "Anti-C":  {"D": "-", "C": "+", "E": "-", "c": "-", "e": "-", "K": "-", "Fya": "-", "Jka": "-", "S": "-"},
    "Anti-E":  {"D": "-", "C": "-", "E": "+", "c": "-", "e": "-", "K": "-", "Fya": "-", "Jka": "-", "S": "-"},
    "anti-c":  {"D": "-", "C": "-", "E": "-", "c": "+", "e": "-", "K": "-", "Fya": "-", "Jka": "-", "S": "-"},
    "Anti-K":  {"D": "-", "C": "-", "E": "-", "c": "-", "e": "-", "K": "+", "Fya": "-", "Jka": "-", "S": "-"},
    "Anti-Fya": {"D": "-", "C": "-", "E": "-", "c": "-", "e": "-", "K": "-", "Fya": "+", "Jka": "-", "S": "-"},
    "Anti-Jka": {"D": "-", "C": "-", "E": "-", "c": "-", "e": "-", "K": "-", "Fya": "-", "Jka": "+", "S": "-"},
    "Anti-S":  {"D": "-", "C": "-", "E": "-", "c": "-", "e": "-", "K": "-", "Fya": "-", "Jka": "-", "S": "+"},
}


def interpret_panel(panel_reactions: Dict[str, str]) -> Dict[str, Any]:
    """
    panel_reactions: cell_id -> reaction string over ANTIGEN_ORDER, e.g.
      "cell1": "+-+-----+-"
    Scores each candidate antibody by fraction of matching cells.
    """
    cells = list(panel_reactions.keys())
    results = []
    for antibody, pattern in ANTIBODY_PATTERNS.items():
        match, total = 0, 0
        for cell_id in cells:
            vec = panel_reactions[cell_id]
            expected = [pattern.get(a, "-") for a in ANTIGEN_ORDER]
            for obs, exp in zip(vec[:len(expected)], expected):
                total += 1
                if obs.lower() == exp.lower():
                    match += 1
        score = match / total if total else 0.0
        results.append({"antibody": antibody, "match_score": round(score, 4)})
    results.sort(key=lambda x: -x["match_score"])
    top = results[0]
    confidence = "high" if top["match_score"] >= 0.9 else \
                 "moderate" if top["match_score"] >= 0.75 else "low"
    return {
        "antigen_order": ANTIGEN_ORDER,
        "cells_evaluated": len(cells),
        "ranked_candidates": results,
        "best_candidate": top,
        "confidence": confidence,
        "note": ("confirm with phenotype of patient RBCs and selected-cell panel"
                 if confidence != "high" else
                 f"{top['antibody']} likely; select antigen-negative units"),
    }


if __name__ == "__main__":
    mtp = MTPEvent("MTP-2026-041", activated_at="02:14")
    for p, n in [("prbc", 4), ("ffp", 2), ("prbc", 2), ("platelets", 3)]:
        mtp.issue(p, n)
    print(json.dumps(mtp.status(), indent=2))

    mon = ColdChainMonitor("rbc_refrigerator")
    for temp, tmin in [(4.0, 0), (5.5, 10), (7.8, 20), (8.5, 35), (4.5, 60), (4.2, 70)]:
        mon.ingest(TempReading("fridge-1", temp, tmin))
    print(json.dumps(mon.status(), indent=2))

    panel = {
        "cell1": "+-+-----+-",
        "cell2": "+---++---+",
        "cell3": "-+----+--+",
        "cell4": "+--++----+",
        "cell5": "---+-+---+",
    }
    print(json.dumps(interpret_panel(panel), indent=2))
