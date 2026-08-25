"""
Distributed Component Hierarchy & Executive Coordinator for TransfusionGuard: Autonomous Blood Bank Compatibility & Crossmatch Safety Agent.
Domain: Transfusion Medicine
"""
import uuid
from typing import Dict, Any, List, Optional
from .models import ClinicalCasePayload, AgentAlert, UrgencyLevel, ClinicalIntegrityStatus
from .engine import ClinicalDomainEngine


class ABOTypeVerifierAgent:
    """Sub-Agent 1: Primary Metric & Baseline Quality Auditor."""
    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        alerts = []
        res = ClinicalDomainEngine.evaluate_primary_index(case.primary_metric)
        if res:
            alerts.append(AgentAlert(
                alert_id=str(uuid.uuid4())[:8],
                sub_agent="ABOTypeVerifierAgent",
                urgency=UrgencyLevel.WARNING,
                title=res["title"],
                clinical_finding=res["finding"],
                actionable_recommendation=res["recommendation"],
            ))
        return alerts


class AntibodyScreenReconcilerAgent:
    """Sub-Agent 2: STAT Kinetics & Closed-Loop Escalation Auditor."""
    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        alerts = []
        res = ClinicalDomainEngine.evaluate_secondary_kinetics(case.secondary_metric, case.is_stat)
        if res:
            alerts.append(AgentAlert(
                alert_id=str(uuid.uuid4())[:8],
                sub_agent="AntibodyScreenReconcilerAgent",
                urgency=UrgencyLevel.STAT_CRITICAL if case.is_stat else UrgencyLevel.WARNING,
                title=res["title"],
                clinical_finding=res["finding"],
                actionable_recommendation=res["recommendation"],
            ))
        return alerts


class CrossmatchAuditorAgent:
    """Sub-Agent 3: Biomarker & Concordance Triager."""
    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        alerts = []
        res = ClinicalDomainEngine.evaluate_biomarker_concordance(case.status_flag, case.biomarkers)
        if res:
            alerts.append(AgentAlert(
                alert_id=str(uuid.uuid4())[:8],
                sub_agent="CrossmatchAuditorAgent",
                urgency=UrgencyLevel.ADVISORY,
                title=res["title"],
                clinical_finding=res["finding"],
                actionable_recommendation=res["recommendation"],
            ))
        return alerts


class BloodBankCoordinator:
    """Executive Coordinator & Air-Gapped Supervisory Interface."""
    def __init__(self):
        self.agent_1 = ABOTypeVerifierAgent()
        self.agent_2 = AntibodyScreenReconcilerAgent()
        self.agent_3 = CrossmatchAuditorAgent()
        self.case_registry: Dict[str, Dict[str, Any]] = {}

    def process_case(self, case: ClinicalCasePayload) -> Dict[str, Any]:
        all_alerts: List[AgentAlert] = []
        all_alerts.extend(self.agent_1.audit(case))
        all_alerts.extend(self.agent_2.audit(case))
        all_alerts.extend(self.agent_3.audit(case))

        stat_count = sum(1 for a in all_alerts if a.urgency == UrgencyLevel.STAT_CRITICAL)
        warn_count = sum(1 for a in all_alerts if a.urgency == UrgencyLevel.WARNING)

        if stat_count > 0:
            status = ClinicalIntegrityStatus.CRITICAL_ACTION_REQUIRED
        elif warn_count > 0 or all_alerts:
            status = ClinicalIntegrityStatus.DISCORDANCE_DETECTED
        else:
            status = ClinicalIntegrityStatus.CONCORDANT_NORMAL

        dossier = {
            "system": "blood-bank-transfusion-agent",
            "domain": "Transfusion Medicine",
            "case_id": case.case_id,
            "patient_synthetic_id": case.patient_synthetic_id,
            "overall_status": status.value,
            "total_alerts": len(all_alerts),
            "stat_critical_alerts": stat_count,
            "warning_alerts": warn_count,
            "alerts": [a.to_dict() for a in all_alerts],
            "guideline_standard": "AABB Technical Manual 20th Edition",
            "consensus_summary": f"Multi-agent supervision completed across 3 sub-agents with status [{status.value}].",
        }

        self.case_registry[case.case_id] = dossier
        return dossier

    def query_supervisory_chat(self, user_query: str) -> str:
        q = user_query.strip().lower()
        if "status" in q or "summary" in q:
            return f"TransfusionGuard: Autonomous Blood Bank Compatibility & Crossmatch Safety Agent currently tracking {len(self.case_registry)} cases in on-premises memory."
        elif "guideline" in q or "standard" in q:
            return "Active clinical surveillance operates under AABB Technical Manual 20th Edition validated protocols."
        else:
            return f"TransfusionGuard: Autonomous Blood Bank Compatibility & Crossmatch Safety Agent executive agent online. Zero-PHI air-gapped monitoring active."
