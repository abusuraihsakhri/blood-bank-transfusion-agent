"""Blood Bank Crossmatch Testing: compatibility determination, antigen matching, antibody screening."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class BloodType(Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


COMPATIBILITY_MATRIX = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}

DONOR_COMPATIBILITY = {
    "O-": {"can_receive": ["O-"], "can_donate": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]},
    "O+": {"can_receive": ["O-", "O+"], "can_donate": ["O+", "A+", "B+", "AB+"]},
    "A-": {"can_receive": ["O-", "A-"], "can_donate": ["A-", "A+", "AB-", "AB+"]},
    "A+": {"can_receive": ["O-", "O+", "A-", "A+"], "can_donate": ["A+", "AB+"]},
    "B-": {"can_receive": ["O-", "B-"], "can_donate": ["B-", "B+", "AB-", "AB+"]},
    "B+": {"can_receive": ["O-", "O+", "B-", "B+"], "can_donate": ["B+", "AB+"]},
    "AB-": {"can_receive": ["O-", "A-", "B-", "AB-"], "can_donate": ["AB-", "AB+"]},
    "AB+": {"can_receive": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"], "can_donate": ["AB+"]},
}


@dataclass
class PatientBloodType:
    patient_id: str
    abo: str
    rh: bool
    antibodies: List[str] = field(default_factory=list)
    antigens: List[str] = field(default_factory=list)


@dataclass
class DonorUnit:
    unit_id: str
    blood_type: str
    antigens: List[str]
    antibody_screen: bool = False
    days_old: int = 0
    irradiated: bool = False


class CrossmatchEngine:
    """ABO/Rh compatibility and antibody screening for transfusion."""

    def __init__(self):
        self._patients: Dict[str, PatientBloodType] = {}
        self._units: Dict[str, DonorUnit] = {}

    def register_patient(self, patient: PatientBloodType) -> None:
        self._patients[patient.patient_id] = patient

    def register_unit(self, unit: DonorUnit) -> None:
        self._units[unit.unit_id] = unit

    def check_abo_rh_compatibility(self, patient_type: str, donor_type: str) -> Dict[str, Any]:
        """Check ABO/Rh compatibility."""
        compatible_donors = COMPATIBILITY_MATRIX.get(patient_type, [])
        compatible = donor_type in compatible_donors
        return {
            "patient_type": patient_type,
            "donor_type": donor_type,
            "compatible": compatible,
            "reason": "ABO/Rh match" if compatible else f"{donor_type} incompatible with {patient_type}",
        }

    def antibody_screening(self, patient: PatientBloodType) -> Dict[str, Any]:
        """Screen patient for unexpected antibodies."""
        known_clinically = ["anti-K", "anti-Fya", "anti-Jka", "anti-E", "anti-c"]
        detected = [ab for ab in patient.antibodies if ab in known_clinically]
        return {
            "patient_id": patient.patient_id,
            "antibodies_detected": detected,
            "screening_result": "positive" if detected else "negative",
            "significant_antibodies": detected,
        }

    def antigen_matching(self, patient: PatientBloodType, unit: DonorUnit) -> Dict[str, Any]:
        """Match donor antigens against patient antibodies."""
        if not patient.antibodies:
            return {"match": True, "reason": "No antibodies to match against"}

        required_antigens_must_avoid = []
        for ab in patient.antibodies:
            target_antigen = ab.replace("anti-", "")
            if target_antigen in unit.antigens:
                return {
                    "match": False,
                    "reason": f"Donor unit has {target_antigen} antigen, patient has {ab}",
                    "conflicting_antigen": target_antigen,
                }

        return {"match": True, "reason": "Donor lacks all patient antibody targets"}

    def crossmatch_test(self, patient_id: str, unit_id: str) -> Dict[str, Any]:
        """Full crossmatch: ABO/Rh + antibody screen + antigen match."""
        patient = self._patients.get(patient_id)
        unit = self._units.get(unit_id)

        if not patient or not unit:
            return {"error": "Patient or unit not found"}

        abo = self.check_abo_rh_compatibility(
            f"{patient.abo}{'+' if patient.rh else '-'}",
            unit.blood_type
        )
        antigen = self.antigen_matching(patient, unit)

        compatible = abo["compatible"] and antigen["match"]
        return {
            "patient_id": patient_id,
            "unit_id": unit_id,
            "compatible": compatible,
            "abo_rh_compatible": abo["compatible"],
            "antigen_match": antigen["match"],
            "details": {"abo": abo, "antigen": antigen},
            "recommendation": "Issue unit" if compatible else "Do not issue",
        }

    def find_compatible_units(self, patient_id: str) -> Dict[str, Any]:
        """Find all compatible units for a patient."""
        patient = self._patients.get(patient_id)
        if not patient:
            return {"error": "Patient not found"}

        compatible = []
        incompatible = []
        for uid, unit in self._units.items():
            result = self.crossmatch_test(patient_id, uid)
            entry = {"unit_id": uid, "blood_type": unit.blood_type, "days_old": unit.days_old}
            if result.get("compatible"):
                compatible.append(entry)
            else:
                incompatible.append({**entry, "reason": result.get("details", {}).get("abo", {}).get("reason", "unknown")})

        compatible.sort(key=lambda x: x["days_old"])
        return {
            "patient_id": patient_id,
            "compatible_units": compatible,
            "incompatible_units": incompatible,
            "num_compatible": len(compatible),
            "recommendation": compatible[0]["unit_id"] if compatible else "No compatible units found",
        }
