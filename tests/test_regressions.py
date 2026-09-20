import io
import json
from contextlib import redirect_stdout

from blood_bank_transfusion import BloodProductType, BloodUnit, CrossmatchEngine, PatientProfile
from crossmatch_engine import CrossmatchEngine as LegacyCrossmatchEngine
from blood_bank_transfusion_agent.cli import main as package_cli_main
from transfusion_safety import TransfusionSafetyManager as LegacySafetyManager


def test_whole_blood_is_abo_rh_identical_by_default():
    patient = PatientProfile("P1", "Pt", "A+")
    unit = BloodUnit("WB1", BloodProductType.WHOLE_BLOOD, "O+")
    result = CrossmatchEngine.crossmatch_unit(patient, unit)
    assert result["compatible"] is False
    assert any("Whole blood" in reason for reason in result["reasons_incompatible"])


def test_legacy_crossmatch_uses_recipient_compatible_donors():
    engine = LegacyCrossmatchEngine()
    result = engine.check_abo_rh_compatibility("A+", "O+")
    assert result["compatible"] is True


def test_legacy_pretransfusion_identity_missing_fails_closed():
    manager = LegacySafetyManager()
    result = manager.pre_transfusion_check(
        "P1",
        "U1",
        {"blood_type": "A+", "consent_signed": True},
        {"blood_type": "A+", "crossmatch_result": "compatible", "antibody_screen_complete": True},
    )
    assert result["all_checks_passed"] is False
    assert result["checks"]["patient_identity"] is False


def test_packaged_cli_delegates_to_canonical_cli():
    buf = io.StringIO()
    with redirect_stdout(buf):
        status = package_cli_main(["crossmatch", "--patient-abo", "A+", "--donor-abo", "O-", "--json"])
    assert status == 0
    result = json.loads(buf.getvalue())
    assert result["compatible"] is True
