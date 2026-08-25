"""
Blood Bank & Transfusion Safety Management Engine
=================================================
Comprehensive clinical decision support and hemovigilance platform for:
- ABO/Rh(D) component-specific compatibility (RBC, FFP, Platelets, Cryo)
- Alloantibody screening, rule-out panel adjudication, and antigen-negative frequency
- Massive Transfusion Protocol (MTP) 1:1:1 balanced ratio monitoring
- AABB / FDA cold chain excursion & time-out-of-storage monitoring
- Acute transfusion reaction classification (AHTR, TRALI, TACO, FNHTR) & DAT investigation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class BloodProductType(str, Enum):
    PRBC = "pRBC"
    FFP = "FFP"
    PLATELETS = "Platelets"
    CRYOPRECIPITATE = "Cryoprecipitate"
    WHOLE_BLOOD = "WholeBlood"


class ReactionType(str, Enum):
    AHTR = "Acute Hemolytic Transfusion Reaction (AHTR)"
    DHTR = "Delayed Hemolytic Transfusion Reaction (DHTR)"
    FNHTR = "Febrile Non-Hemolytic Transfusion Reaction (FNHTR)"
    ALLERGIC_MILD = "Mild Allergic / Urticarial"
    ANAPHYLACTIC = "Anaphylactic / Severe Allergic"
    TRALI = "Transfusion-Related Acute Lung Injury (TRALI)"
    TACO = "Transfusion-Associated Circulatory Overload (TACO)"
    SEPTIC = "Bacterial Sepsis / Contamination"
    PTP = "Post-Transfusion Purpura"


class ReactionSeverity(str, Enum):
    GRADE_1_MILD = "Grade 1 (Mild)"
    GRADE_2_MODERATE = "Grade 2 (Moderate)"
    GRADE_3_SEVERE = "Grade 3 (Severe / Non-fatal)"
    GRADE_4_LIFE_THREATENING = "Grade 4 (Life Threatening)"
    GRADE_5_FATAL = "Grade 5 (Fatal)"


# Common Caucasian/Global red cell antigen prevalence frequencies (for compatible donor calculation)
ANTIGEN_PREVALENCE: Dict[str, float] = {
    "D": 0.85,
    "C": 0.68,
    "E": 0.29,
    "c": 0.80,
    "e": 0.98,
    "K": 0.09,
    "k": 0.998,
    "Fya": 0.66,
    "Fyb": 0.83,
    "Jka": 0.77,
    "Jkb": 0.73,
    "S": 0.55,
    "s": 0.89,
    "M": 0.78,
    "N": 0.72,
}

# Standard RBC Compatibility: Key = Patient ABO/Rh, Value = Set of acceptable donor pRBC types
RBC_COMPATIBILITY_TABLE: Dict[str, Set[str]] = {
    "O-": {"O-"},
    "O+": {"O-", "O+"},
    "A-": {"O-", "A-"},
    "A+": {"O-", "O+", "A-", "A+"},
    "B-": {"O-", "B-"},
    "B+": {"O-", "O+", "B-", "B+"},
    "AB-": {"O-", "A-", "B-", "AB-"},
    "AB+": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
}

# Plasma / FFP Compatibility: Key = Patient ABO, Value = Set of acceptable donor FFP types
PLASMA_COMPATIBILITY_TABLE: Dict[str, Set[str]] = {
    "O": {"O", "A", "B", "AB"},
    "A": {"A", "AB"},
    "B": {"B", "AB"},
    "AB": {"AB"},
}


@dataclass
class PatientProfile:
    patient_id: str
    name: str
    abo_rh: str  # e.g., "O+", "A-", "AB+"
    identified_antibodies: List[str] = field(default_factory=list)  # e.g., ["Anti-K", "Anti-Fya"]
    rh_phenotype: Optional[Dict[str, str]] = None  # e.g., {"D": "+", "C": "+", "E": "-", "c": "+", "e": "+"}
    special_requirements: List[str] = field(default_factory=list)  # e.g., ["Irradiated", "CMV-Negative", "Washed"]


@dataclass
class BloodUnit:
    unit_id: str
    product_type: BloodProductType
    abo_rh: str
    antigen_phenotype: Dict[str, str] = field(default_factory=dict)  # e.g., {"D": "+", "K": "-", "Fya": "-"}
    days_to_expiration: int = 35
    is_irradiated: bool = False
    is_cmv_negative: bool = False
    is_washed: bool = False
    is_quarantined: bool = False


# ==============================================================================
# 1. CROSSMATCH & COMPONENT COMPATIBILITY ENGINE
# ==============================================================================

class CrossmatchEngine:
    """Evaluates immunologic compatibility for RBC, FFP, Platelets, and Cryoprecipitate."""

    @classmethod
    def check_rbc_compatibility(
        cls,
        patient_type: str,
        donor_type: str,
    ) -> bool:
        """Check if donor pRBC is ABO/Rh(D) compatible with patient."""
        patient_type = patient_type.strip().upper()
        donor_type = donor_type.strip().upper()
        allowed = RBC_COMPATIBILITY_TABLE.get(patient_type, set())
        return donor_type in allowed

    @classmethod
    def check_plasma_compatibility(
        cls,
        patient_abo: str,
        donor_abo: str,
    ) -> bool:
        """Check if donor Plasma/FFP is compatible with patient ABO."""
        # Strip Rh sign if present for plasma
        p_abo = patient_abo.replace("+", "").replace("-", "").strip().upper()
        d_abo = donor_abo.replace("+", "").replace("-", "").strip().upper()
        allowed = PLASMA_COMPATIBILITY_TABLE.get(p_abo, set())
        return d_abo in allowed

    @classmethod
    def crossmatch_unit(
        cls,
        patient: PatientProfile,
        unit: BloodUnit,
    ) -> Dict[str, Any]:
        """
        Execute full clinical crossmatch:
        - Product-specific ABO/Rh check
        - Unexpected antibody vs donor antigen conflict check
        - Special processing verification (Irradiation, CMV negative, Washed)
        """
        reasons_incompatible = []

        if unit.is_quarantined:
            return {
                "compatible": False,
                "reasons": ["Unit is quarantined due to cold-chain excursion or testing hold"],
                "recommendation": "DO NOT ISSUE - Unit Quarantined",
            }

        # 1. ABO/Rh compatibility
        if unit.product_type in [BloodProductType.PRBC, BloodProductType.WHOLE_BLOOD]:
            if not cls.check_rbc_compatibility(patient.abo_rh, unit.abo_rh):
                reasons_incompatible.append(f"ABO/Rh incompatible pRBC: Donor {unit.abo_rh} -> Patient {patient.abo_rh}")
        elif unit.product_type in [BloodProductType.FFP, BloodProductType.CRYOPRECIPITATE]:
            if not cls.check_plasma_compatibility(patient.abo_rh, unit.abo_rh):
                reasons_incompatible.append(f"ABO incompatible Plasma: Donor {unit.abo_rh} -> Patient {patient.abo_rh}")

        # 2. Antibody vs Antigen mismatch
        for ab in patient.identified_antibodies:
            # Clean antibody name to antigen key, e.g. "Anti-K" -> "K", "anti-Fya" -> "Fya"
            target_ag = ab.replace("Anti-", "").replace("anti-", "").strip()
            unit_ag_status = unit.antigen_phenotype.get(target_ag, "")
            if unit_ag_status == "+":
                reasons_incompatible.append(f"Donor unit expresses antigen '{target_ag}', patient has alloantibody '{ab}'")

        # 3. Special requirements
        for req in patient.special_requirements:
            req_lower = req.lower()
            if "irradiat" in req_lower and not unit.is_irradiated:
                reasons_incompatible.append("Patient requires Irradiated unit to prevent TA-GVHD")
            if "cmv" in req_lower and not unit.is_cmv_negative:
                reasons_incompatible.append("Patient requires CMV-Seronegative unit")
            if "wash" in req_lower and not unit.is_washed:
                reasons_incompatible.append("Patient requires Washed red cells")

        is_compatible = len(reasons_incompatible) == 0
        return {
            "patient_id": patient.patient_id,
            "unit_id": unit.unit_id,
            "product_type": unit.product_type.value,
            "compatible": is_compatible,
            "reasons_incompatible": reasons_incompatible,
            "recommendation": "Issue unit for transfusion" if is_compatible else "DO NOT ISSUE - Incompatible",
        }

    @classmethod
    def calculate_compatible_donor_frequency(
        cls,
        patient_abo_rh: str,
        antibodies: List[str],
    ) -> Dict[str, Any]:
        """
        Calculate expected percentage of randomly selected donor units that are compatible
        based on ABO/Rh and antigen negative requirements:
        P(compatible) = P(ABO/Rh compatible) * prod(1 - P(antigen_i))
        """
        # ABO/Rh general frequency estimate (US population)
        abo_freq = {
            "O+": 0.38, "O-": 0.07, "A+": 0.34, "A-": 0.06,
            "B+": 0.09, "B-": 0.02, "AB+": 0.03, "AB-": 0.01
        }
        allowed_types = RBC_COMPATIBILITY_TABLE.get(patient_abo_rh.upper(), set())
        p_abo_compat = sum(abo_freq.get(t, 0.05) for t in allowed_types)

        p_antigen_neg = 1.0
        antigens_to_avoid = []
        for ab in antibodies:
            ag = ab.replace("Anti-", "").replace("anti-", "").strip()
            prev = ANTIGEN_PREVALENCE.get(ag, 0.50)
            p_antigen_neg *= (1.0 - prev)
            antigens_to_avoid.append({"antigen": ag, "prevalence": prev, "antigen_neg_frequency": round(1.0 - prev, 3)})

        total_compat_fraction = p_abo_compat * p_antigen_neg
        units_to_screen_for_1_compat = math.ceil(1.0 / max(total_compat_fraction, 1e-6))

        return {
            "patient_abo_rh": patient_abo_rh,
            "abo_compatible_fraction": round(p_abo_compat, 4),
            "antigen_negative_fraction": round(p_antigen_neg, 6),
            "overall_compatible_donor_fraction": round(total_compat_fraction, 6),
            "overall_compatible_donor_percentage": round(total_compat_fraction * 100.0, 4),
            "estimated_units_to_screen_for_one_compatible": units_to_screen_for_1_compat,
            "antigens_evaluated": antigens_to_avoid,
        }


# ==============================================================================
# 2. MASSIVE TRANSFUSION PROTOCOL (MTP) TRACKER
# ==============================================================================

@dataclass
class MTPTracker:
    """Tracks blood component ratios during Massive Transfusion Protocol resuscitation."""
    event_id: str
    patient_id: str
    target_ratio: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # pRBC : FFP : Platelets (single donor or 6-pack)
    issued_prbc: int = 0
    issued_ffp: int = 0
    issued_platelets: int = 0
    issued_cryo_pools: int = 0

    def issue_product(self, product: BloodProductType, units: int = 1) -> None:
        if product == BloodProductType.PRBC:
            self.issued_prbc += units
        elif product == BloodProductType.FFP:
            self.issued_ffp += units
        elif product == BloodProductType.PLATELETS:
            self.issued_platelets += units
        elif product == BloodProductType.CRYOPRECIPITATE:
            self.issued_cryo_pools += units

    def get_status(self) -> Dict[str, Any]:
        denom = max(self.issued_prbc, 1)
        ffp_ratio = self.issued_ffp / denom
        plt_ratio = self.issued_platelets / denom

        compliance = min(ffp_ratio, plt_ratio, 1.0)
        ffp_deficit = max(0, self.issued_prbc - self.issued_ffp)
        plt_deficit = max(0, self.issued_prbc - self.issued_platelets)

        if compliance >= 0.8:
            status = "Optimal 1:1:1 Balanced Resuscitation"
            rec = "Continue balanced protocol; monitor fibrinogen and ionized calcium"
        elif ffp_deficit > plt_deficit:
            status = "FFP Deficit (Dilutional Coagulopathy Risk)"
            rec = f"Issue {ffp_deficit} additional units of FFP immediately"
        else:
            status = "Platelet Deficit (Thrombocytopenia Risk)"
            rec = f"Issue {plt_deficit} additional unit(s) of Platelets immediately"

        return {
            "event_id": self.event_id,
            "patient_id": self.patient_id,
            "units_issued": {
                "pRBC": self.issued_prbc,
                "FFP": self.issued_ffp,
                "Platelets": self.issued_platelets,
                "Cryoprecipitate_pools": self.issued_cryo_pools,
            },
            "current_ratio": f"{self.issued_prbc}:{self.issued_ffp}:{self.issued_platelets}",
            "ffp_to_prbc_ratio": round(ffp_ratio, 2),
            "platelet_to_prbc_ratio": round(plt_ratio, 2),
            "ratio_compliance_pct": round(compliance * 100.0, 1),
            "coagulopathy_risk_status": status,
            "recommendation": rec,
            "gaps": {"ffp_deficit_units": ffp_deficit, "platelet_deficit_units": plt_deficit},
        }


# ==============================================================================
# 3. AABB COLD CHAIN & EXCURSION MONITOR
# ==============================================================================

@dataclass
class TempReading:
    timestamp_minutes: float
    temperature_c: float
    sensor_id: str


class ColdChainMonitor:
    """Monitors blood product storage compliance and cumulative out-of-storage times."""

    STORAGE_STANDARDS = {
        BloodProductType.PRBC: {"min_c": 1.0, "max_c": 6.0, "max_excursion_minutes": 30.0},
        BloodProductType.FFP: {"min_c": -50.0, "max_c": -18.0, "max_excursion_minutes": 15.0},
        BloodProductType.PLATELETS: {"min_c": 20.0, "max_c": 24.0, "max_excursion_minutes": 60.0},
    }

    def __init__(self, product_type: BloodProductType):
        self.product_type = product_type
        self.limits = self.STORAGE_STANDARDS.get(product_type, {"min_c": 1.0, "max_c": 6.0, "max_excursion_minutes": 30.0})
        self.readings: List[TempReading] = []
        self.closed_excursions: List[Dict[str, Any]] = []
        self._active_excursion_start: Optional[float] = None
        self._active_peak_temp: float = 0.0

    def record_reading(self, reading: TempReading) -> Dict[str, Any]:
        self.readings.append(reading)
        temp = reading.temperature_c
        in_range = self.limits["min_c"] <= temp <= self.limits["max_c"]

        if not in_range:
            if self._active_excursion_start is None:
                self._active_excursion_start = reading.timestamp_minutes
                self._active_peak_temp = temp
            else:
                if abs(temp - self.limits["max_c"]) > abs(self._active_peak_temp - self.limits["max_c"]):
                    self._active_peak_temp = temp
        else:
            if self._active_excursion_start is not None:
                duration = reading.timestamp_minutes - self._active_excursion_start
                self.closed_excursions.append({
                    "start_min": self._active_excursion_start,
                    "end_min": reading.timestamp_minutes,
                    "duration_min": duration,
                    "peak_temp_c": self._active_peak_temp,
                })
                self._active_excursion_start = None

        return {"in_range": in_range, "temp_c": temp, "timestamp_min": reading.timestamp_minutes}

    def evaluate_compliance(self) -> Dict[str, Any]:
        total_closed_min = sum(e["duration_min"] for e in self.closed_excursions)
        ongoing_min = 0.0
        if self._active_excursion_start is not None and self.readings:
            ongoing_min = self.readings[-1].timestamp_minutes - self._active_excursion_start

        cumulative_excursion_min = total_closed_min + ongoing_min
        max_allowed = self.limits["max_excursion_minutes"]
        quarantine_required = cumulative_excursion_min > max_allowed

        return {
            "product_type": self.product_type.value,
            "acceptable_temperature_range_c": [self.limits["min_c"], self.limits["max_c"]],
            "total_excursions_count": len(self.closed_excursions) + (1 if self._active_excursion_start else 0),
            "cumulative_out_of_storage_minutes": round(cumulative_excursion_min, 1),
            "max_allowed_excursion_minutes": max_allowed,
            "currently_in_excursion": self._active_excursion_start is not None,
            "quarantine_required": quarantine_required,
            "decision": "QUARANTINE UNIT - Exceeded Safe Storage Limits" if quarantine_required else "Unit Safe for Issue",
        }


# ==============================================================================
# 4. TRANSFUSION REACTION ADJUDICATION & HEMOVIGILANCE
# ==============================================================================

class TransfusionSafetyManager:
    """Hemovigilance adjudication for acute and delayed adverse transfusion reactions."""

    @staticmethod
    def adjudicate_reaction(
        temp_rise_c: float,
        onset_minutes: int,
        hypotension: bool = False,
        dyspnea: bool = False,
        hemoglobinuria: bool = False,
        urticaria: bool = False,
        wheezing_or_stridor: bool = False,
        dat_positive: bool = False,
        bacterial_gram_positive: bool = False,
        jvd_or_fluid_overload: bool = False,
    ) -> Dict[str, Any]:
        """
        Rule-based clinical diagnostic algorithm for acute adverse reactions.
        """
        reaction_type = ReactionType.FNHTR
        severity = ReactionSeverity.GRADE_1_MILD
        immediate_actions = [
            "STOP TRANSFUSION IMMEDIATELY",
            "Maintain IV access with Normal Saline (0.9% NaCl)",
            "Perform clerical check of patient ID and unit labels",
        ]
        investigation_workup = [
            "Send unit bag, IV tubing, and post-transfusion EDTA blood sample to Blood Bank",
            "Direct Antiglobulin Test (DAT / Coombs) on post-transfusion sample",
            "Repeat ABO/Rh typing and crossmatch on pre- and post-transfusion samples",
            "Visual check of post-transfusion plasma and urine for free hemoglobin (pink/red discoloration)",
        ]

        if bacterial_gram_positive or (hypotension and temp_rise_c >= 2.5 and onset_minutes <= 30):
            reaction_type = ReactionType.SEPTIC
            severity = ReactionSeverity.GRADE_4_LIFE_THREATENING
            immediate_actions.extend([
                "Start broad-spectrum empiric IV antibiotics (e.g. Vancomycin + Cefepime)",
                "Send blood cultures from patient (2 sites) and blood unit bag to Microbiology",
                "Initiate aggressive fluid resuscitation and vasopressors for septic shock",
            ])
        elif dat_positive or (hemoglobinuria and (temp_rise_c >= 1.0 or hypotension)):
            reaction_type = ReactionType.AHTR
            severity = ReactionSeverity.GRADE_4_LIFE_THREATENING if hypotension else ReactionSeverity.GRADE_3_SEVERE
            immediate_actions.extend([
                "Check for free hemoglobin (hemoglobinemia / hemoglobinuria)",
                "Monitor urine output (>100 mL/hr); administer IV fluids and diuretics to prevent acute tubular necrosis",
                "Coagulation panel (PT, PTT, Fibrinogen, D-Dimer) to rule out DIC",
            ])
        elif dyspnea:
            if jvd_or_fluid_overload:
                reaction_type = ReactionType.TACO
                severity = ReactionSeverity.GRADE_3_SEVERE
                immediate_actions.extend([
                    "Place patient upright",
                    "Administer supplemental O2",
                    "Administer IV Loop Diuretics (e.g., Furosemide 40 mg IV)",
                ])
                investigation_workup.append("Check pre/post BNP or NT-proBNP and Chest X-ray")
            else:
                reaction_type = ReactionType.TRALI
                severity = ReactionSeverity.GRADE_4_LIFE_THREATENING
                immediate_actions.extend([
                    "Initiate respiratory support (High-flow O2 or mechanical ventilation)",
                    "AVOID aggressive diuretics (non-cardiogenic pulmonary edema)",
                    "Notify Blood Bank to defer donor and screen for anti-HLA / anti-HNA antibodies",
                ])
                investigation_workup.append("Chest X-ray (bilateral non-cardiogenic alveolar infiltrates)")
        elif wheezing_or_stridor or (urticaria and hypotension):
            reaction_type = ReactionType.ANAPHYLACTIC
            severity = ReactionSeverity.GRADE_4_LIFE_THREATENING
            immediate_actions.extend([
                "Administer Epinephrine 0.3-0.5 mg IM (1:1000)",
                "Administer IV Diphenhydramine 50 mg and IV Methylprednisolone",
                "Maintain airway; prepare for intubation if laryngeal edema develops",
            ])
            investigation_workup.append("Check patient serum IgA level (rule out Anti-IgA antibodies in IgA-deficient patient)")
        elif urticaria:
            reaction_type = ReactionType.ALLERGIC_MILD
            severity = ReactionSeverity.GRADE_1_MILD
            immediate_actions.append("Administer Antihistamines (Diphenhydramine 25-50 mg PO/IV); may resume if symptoms resolve")
        elif temp_rise_c >= 1.0:
            reaction_type = ReactionType.FNHTR
            severity = ReactionSeverity.GRADE_2_MODERATE
            immediate_actions.extend([
                "Administer Antipyretics (Acetaminophen 650-1000 mg)",
                "Consider leukoreduced blood components for future transfusions",
            ])

        return {
            "adjudicated_reaction": reaction_type.value,
            "severity_grade": severity.value,
            "immediate_actions": immediate_actions,
            "investigation_workup": investigation_workup,
            "requires_blood_bank_notification": True,
            "fda_cber_reporting_mandatory": severity in [ReactionSeverity.GRADE_4_LIFE_THREATENING, ReactionSeverity.GRADE_5_FATAL],
        }
