"""Blood Transfusion Safety: adverse reaction classification, patient verification, consent management."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ReactionSeverity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life_threatening"
    FATAL = "fatal"


class ReactionType(Enum):
    HEMOLYTIC = "hemolytic"
    FEBRILE_NON_HEMOLYTIC = "febrile_non_hemolytic"
    ALLERGIC = "allergic"
    ANAPHYLACTIC = "anaphylactic"
    TRANSMISSION = "transfusion_transmitted"
    TA_GVHD = "transfusion_associated_gvhd"
    TRALI = "trali"
    TACO = "taco"


@dataclass
class AdverseReaction:
    reaction_id: str
    patient_id: str
    unit_id: str
    reaction_type: ReactionType
    severity: ReactionSeverity
    onset_time_min: int
    symptoms: List[str]
    temperature_rise_c: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)


class TransfusionSafetyManager:
    """Adverse reaction management and pre-transfusion verification."""

    VERIFICATION_STEPS = [
        "patient_identity",
        "blood_type_match",
        "consent_documented",
        "antibody_screen_complete",
        "crossmatch_compatible",
    ]

    def __init__(self):
        self._reactions: List[AdverseReaction] = []
        self._verifications: Dict[str, List[str]] = {}

    def pre_transfusion_check(self, patient_id: str, unit_id: str, patient_data: Dict, unit_data: Dict) -> Dict[str, Any]:
        """Verify all pre-transfusion requirements."""
        checks = {}
        all_passed = True

        if patient_data.get("name") and unit_data.get("patient_name"):
            checks["patient_identity"] = patient_data["name"] == unit_data["patient_name"]
        else:
            checks["patient_identity"] = False

        checks["blood_type_match"] = patient_data.get("blood_type") == unit_data.get("blood_type")
        checks["consent_documented"] = patient_data.get("consent_signed", False)
        checks["antibody_screen_complete"] = bool(unit_data.get("antibody_screen_complete", False))
        checks["crossmatch_compatible"] = unit_data.get("crossmatch_result") == "compatible"

        all_passed = all(checks.values())

        return {
            "patient_id": patient_id,
            "unit_id": unit_id,
            "all_checks_passed": all_passed,
            "checks": checks,
            "recommendation": "Proceed with transfusion" if all_passed else "HOLD - resolve issues before proceeding",
            "failed_checks": [k for k, v in checks.items() if not v],
        }

    def classify_reaction(self, reaction: AdverseReaction) -> Dict[str, Any]:
        """Classify adverse reaction and recommend actions."""
        severity_actions = {
            ReactionSeverity.MILD: "Monitor closely, slow transfusion rate",
            ReactionSeverity.MODERATE: "Stop transfusion, notify physician, treat symptoms",
            ReactionSeverity.SEVERE: "STOP transfusion immediately, activate emergency protocol",
            ReactionSeverity.LIFE_THREATENING: "STOP, activate code, prepare for resuscitation",
            ReactionSeverity.FATAL: "STOP, full resuscitation, mandatory reporting",
        }

        type_actions = {
            ReactionType.HEMOLYTIC: "Draw new sample for re-crossmatch, check for hemolysis",
            ReactionType.FEBRILE_NON_HEMOLYTIC: "Administer antipyretics; consider leukoreduced components for future transfusions when indicated",
            ReactionType.ALLERGIC: "Administer antihistamines, monitor for progression",
            ReactionType.ANAPHYLACTIC: "Epinephrine, IV fluids, activate anaphylaxis protocol",
            ReactionType.TRALI: "Provide supportive respiratory care; avoid routine diuresis unless there is independent evidence of volume overload; notify blood bank",
            ReactionType.TACO: "Slow or stop transfusion, assess fluid status, consider diuretics",
        }

        return {
            "reaction_id": reaction.reaction_id,
            "type": reaction.reaction_type.value,
            "severity": reaction.severity.value,
            "severity_action": severity_actions.get(reaction.severity, "Unknown severity"),
            "type_action": type_actions.get(reaction.reaction_type, "Investigate"),
            "immediate_action": "STOP TRANSFUSION" if reaction.severity.value in ["severe", "life_threatening", "fatal"] else "Assess and respond",
            "reporting_required": reaction.severity.value in ["severe", "life_threatening", "fatal"],
        }

    def investigate_reaction(self, reaction: AdverseReaction) -> Dict[str, Any]:
        """Investigate root cause of adverse reaction."""
        checklist = {
            "check_patient_identity": True,
            "verify_blood_type": True,
            "inspect_unit_appearance": True,
            "check_transfusion_rate": True,
            "review_patient_history": True,
        }

        findings = []
        if reaction.reaction_type == ReactionType.HEMOLYTIC:
            findings.append("Check for ABO incompatibility")
            findings.append("Repeat crossmatch with pre- and post-transfusion samples")
            findings.append("Test for free hemoglobin")
        elif reaction.reaction_type == ReactionType.TRALI:
            findings.append("Check donor HLA/HNA antibodies")
            findings.append("Review chest X-ray")
            findings.append("Check fluid balance")

        return {
            "reaction_id": reaction.reaction_id,
            "investigation_checklist": checklist,
            "findings": findings,
            "root_cause": "pending investigation" if findings else "unknown",
            "preventive_actions": "Update protocols as needed",
        }

    def batch_reaction_report(self) -> Dict[str, Any]:
        """Aggregate adverse reaction statistics."""
        if not self._reactions:
            return {"status": "no_reactions"}

        by_type = {}
        by_severity = {}
        for r in self._reactions:
            by_type[r.reaction_type.value] = by_type.get(r.reaction_type.value, 0) + 1
            by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1

        return {
            "total_reactions": len(self._reactions),
            "by_type": by_type,
            "by_severity": by_severity,
            "severe_reaction_rate": round(
                sum(1 for r in self._reactions if r.severity.value in ["severe", "life_threatening", "fatal"])
                / len(self._reactions) * 100, 2
            ),
        }
