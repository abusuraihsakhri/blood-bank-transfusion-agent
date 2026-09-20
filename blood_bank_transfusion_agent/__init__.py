"""Public package exports for the blood-bank transfusion reference tools."""

from blood_bank_transfusion import (
    BloodProductType,
    BloodUnit,
    ColdChainMonitor,
    CrossmatchEngine,
    MTPTracker,
    PatientProfile,
    ReactionSeverity,
    ReactionType,
    TempReading,
    TransfusionSafetyManager,
)

__version__ = "2.1.0"

__all__ = [
    "BloodProductType",
    "BloodUnit",
    "ColdChainMonitor",
    "CrossmatchEngine",
    "MTPTracker",
    "PatientProfile",
    "ReactionSeverity",
    "ReactionType",
    "TempReading",
    "TransfusionSafetyManager",
]
