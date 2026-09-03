"""
Unit Test Suite for Blood Bank Transfusion Safety Agent
========================================================
Comprehensive verification across:
  - ABO/Rh(D) component compatibility (pRBC vs FFP vs Platelets)
  - Unexpected alloantibody conflict detection & antigen-negative screening
  - Special blood processing requirements (Irradiation, CMV-, Washed)
  - Compatible donor phenotype frequency calculation
  - Massive Transfusion Protocol (MTP) 1:1:1 ratio compliance & deficits
  - AABB / FDA cold chain storage excursion & quarantine rules
  - Acute adverse reaction triage (AHTR, TRALI, TACO, Anaphylaxis, Sepsis, FNHTR)
  - CLI command execution and JSON serialization
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

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
from cli import main


class TestCrossmatchCompatibility(unittest.TestCase):
    """Test ABO/Rh and alloantibody crossmatch compatibility rules."""

    def test_rbc_o_negative_recipient_strict(self):
        patient = PatientProfile("P1", "Patient O-", "O-")
        unit_o_neg = BloodUnit("U1", BloodProductType.PRBC, "O-")
        unit_o_pos = BloodUnit("U2", BloodProductType.PRBC, "O+")
        unit_a_neg = BloodUnit("U3", BloodProductType.PRBC, "A-")

        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_o_neg)["compatible"])
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_o_pos)["compatible"])
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_a_neg)["compatible"])

    def test_rbc_ab_positive_universal_recipient(self):
        patient = PatientProfile("P2", "Patient AB+", "AB+")
        all_types = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
        for t in all_types:
            unit = BloodUnit(f"U_{t}", BloodProductType.PRBC, t)
            self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit)["compatible"])

    def test_plasma_ab_universal_donor(self):
        # AB Plasma can be given to O, A, B, AB
        unit_ab_plasma = BloodUnit("U_PL_AB", BloodProductType.FFP, "AB")
        for p_type in ["O", "A", "B", "AB"]:
            patient = PatientProfile("P_PL", "Pt", p_type)
            self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_ab_plasma)["compatible"])

    def test_plasma_ab_recipient_restriction(self):
        # AB patient can only receive AB plasma
        patient_ab = PatientProfile("P_AB", "Pt", "AB")
        unit_o_plasma = BloodUnit("U_O", BloodProductType.FFP, "O")
        unit_a_plasma = BloodUnit("U_A", BloodProductType.FFP, "A")
        unit_ab_plasma = BloodUnit("U_AB", BloodProductType.FFP, "AB")

        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient_ab, unit_o_plasma)["compatible"])
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient_ab, unit_a_plasma)["compatible"])
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient_ab, unit_ab_plasma)["compatible"])

    def test_alloantibody_conflict_rejection(self):
        patient = PatientProfile("P3", "Pt", "A+", identified_antibodies=["Anti-K", "Anti-Fya"])
        unit_k_pos = BloodUnit("U_K_pos", BloodProductType.PRBC, "A+", antigen_phenotype={"K": "+", "Fya": "-"})
        unit_fya_pos = BloodUnit("U_Fya_pos", BloodProductType.PRBC, "A+", antigen_phenotype={"K": "-", "Fya": "+"})
        unit_compat = BloodUnit("U_compat", BloodProductType.PRBC, "A+", antigen_phenotype={"K": "-", "Fya": "-"})

        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_k_pos)["compatible"])
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_fya_pos)["compatible"])
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_compat)["compatible"])

    def test_special_requirements_irradiation(self):
        patient = PatientProfile("P4", "Pt", "B+", special_requirements=["Irradiated"])
        unit_unirradiated = BloodUnit("U1", BloodProductType.PRBC, "B+", is_irradiated=False)
        unit_irradiated = BloodUnit("U2", BloodProductType.PRBC, "B+", is_irradiated=True)

        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_unirradiated)["compatible"])
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_irradiated)["compatible"])

    def test_special_requirements_cmv_negative(self):
        patient = PatientProfile("P5", "Pt", "O+", special_requirements=["CMV-Negative"])
        unit_cmv_pos = BloodUnit("U1", BloodProductType.PRBC, "O+", is_cmv_negative=False)
        unit_cmv_neg = BloodUnit("U2", BloodProductType.PRBC, "O+", is_cmv_negative=True)

        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_cmv_pos)["compatible"])
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_cmv_neg)["compatible"])

    def test_quarantined_unit_rejection(self):
        patient = PatientProfile("P6", "Pt", "O+")
        unit_quarantined = BloodUnit("U_Q", BloodProductType.PRBC, "O-", is_quarantined=True)
        res = CrossmatchEngine.crossmatch_unit(patient, unit_quarantined)
        self.assertFalse(res["compatible"])
        self.assertIn("Quarantined", res["recommendation"])


class TestCompatibleDonorFrequency(unittest.TestCase):
    """Test population genetics calculation of compatible donor frequencies."""

    def test_frequency_common_type(self):
        res = CrossmatchEngine.calculate_compatible_donor_frequency("O+", [])
        self.assertGreater(res["overall_compatible_donor_percentage"], 40.0)
        self.assertEqual(res["estimated_units_to_screen_for_one_compatible"], 3)

    def test_frequency_rare_multiple_antibodies(self):
        # Patient with Anti-e (98% prevalence) and Anti-k (99.8% prevalence)
        res = CrossmatchEngine.calculate_compatible_donor_frequency("A-", ["Anti-e", "Anti-K"])
        self.assertLess(res["overall_compatible_donor_percentage"], 1.0)
        self.assertGreater(res["estimated_units_to_screen_for_one_compatible"], 100)


class TestMassiveTransfusionProtocol(unittest.TestCase):
    """Test MTP 1:1:1 ratio compliance tracking."""

    def test_balanced_mtp_ratio(self):
        mtp = MTPTracker("MTP-1", "P100", issued_prbc=6, issued_ffp=6, issued_platelets=6)
        status = mtp.get_status()
        self.assertEqual(status["ratio_compliance_pct"], 100.0)
        self.assertIn("Optimal", status["coagulopathy_risk_status"])

    def test_ffp_deficit_detection(self):
        mtp = MTPTracker("MTP-2", "P100", issued_prbc=8, issued_ffp=2, issued_platelets=8)
        status = mtp.get_status()
        self.assertLess(status["ratio_compliance_pct"], 50.0)
        self.assertIn("FFP Deficit", status["coagulopathy_risk_status"])
        self.assertEqual(status["gaps"]["ffp_deficit_units"], 6)

    def test_platelet_deficit_detection(self):
        mtp = MTPTracker("MTP-3", "P100", issued_prbc=6, issued_ffp=6, issued_platelets=0)
        status = mtp.get_status()
        self.assertEqual(status["ratio_compliance_pct"], 0.0)
        self.assertIn("Platelet Deficit", status["coagulopathy_risk_status"])


class TestColdChainMonitor(unittest.TestCase):
    """Test AABB blood storage temperature monitoring and excursion quarantine."""

    def test_normal_rbc_storage(self):
        mon = ColdChainMonitor(BloodProductType.PRBC)
        for t, temp in [(0, 4.0), (10, 4.5), (20, 5.0), (30, 4.2)]:
            mon.record_reading(TempReading(t, temp, "s1"))
        res = mon.evaluate_compliance()
        self.assertFalse(res["quarantine_required"])
        self.assertEqual(res["cumulative_out_of_storage_minutes"], 0.0)

    def test_rbc_excursion_within_safe_limit(self):
        mon = ColdChainMonitor(BloodProductType.PRBC)
        # Excursion from min 10 to min 25 (15 min at 7.5°C <= 30 min limit)
        readings = [(0, 4.0), (10, 7.5), (25, 7.8), (26, 4.5), (40, 4.0)]
        for t, temp in readings:
            mon.record_reading(TempReading(t, temp, "s1"))
        res = mon.evaluate_compliance()
        self.assertFalse(res["quarantine_required"])
        self.assertGreater(res["cumulative_out_of_storage_minutes"], 0.0)

    def test_rbc_excursion_exceeding_quarantine_threshold(self):
        mon = ColdChainMonitor(BloodProductType.PRBC)
        # Excursion for 45 minutes (> 30 min limit)
        readings = [(0, 4.0), (10, 8.5), (55, 8.5), (56, 4.0)]
        for t, temp in readings:
            mon.record_reading(TempReading(t, temp, "s1"))
        res = mon.evaluate_compliance()
        self.assertTrue(res["quarantine_required"])
        self.assertIn("QUARANTINE", res["decision"])


class TestTransfusionReactionSafety(unittest.TestCase):
    """Test acute adverse reaction clinical triage and diagnostic logic."""

    def test_ahtr_adjudication(self):
        res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=1.5,
            onset_minutes=15,
            hypotension=True,
            hemoglobinuria=True,
            dat_positive=True,
        )
        self.assertEqual(res["adjudicated_reaction"], ReactionType.AHTR.value)
        self.assertEqual(res["severity_grade"], ReactionSeverity.GRADE_4_LIFE_THREATENING.value)
        self.assertTrue(res["fda_cber_reporting_mandatory"])

    def test_trali_vs_taco_differentiation(self):
        # TRALI: Dyspnea without fluid overload
        trali_res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=0.5,
            onset_minutes=30,
            dyspnea=True,
            jvd_or_fluid_overload=False,
        )
        self.assertEqual(trali_res["adjudicated_reaction"], ReactionType.TRALI.value)
        self.assertIn("AVOID aggressive diuretics", str(trali_res["immediate_actions"]))

        # TACO: Dyspnea with JVD/fluid overload
        taco_res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=0.0,
            onset_minutes=45,
            dyspnea=True,
            jvd_or_fluid_overload=True,
        )
        self.assertEqual(taco_res["adjudicated_reaction"], ReactionType.TACO.value)
        self.assertIn("Loop Diuretics", str(taco_res["immediate_actions"]))

    def test_anaphylaxis_adjudication(self):
        res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=0.0,
            onset_minutes=5,
            urticaria=True,
            wheezing_or_stridor=True,
            hypotension=True,
        )
        self.assertEqual(res["adjudicated_reaction"], ReactionType.ANAPHYLACTIC.value)
        self.assertIn("Epinephrine", str(res["immediate_actions"]))

    def test_sepsis_bacterial_contamination(self):
        res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=3.0,
            onset_minutes=10,
            hypotension=True,
            bacterial_gram_positive=True,
        )
        self.assertEqual(res["adjudicated_reaction"], ReactionType.SEPTIC.value)
        self.assertIn("broad-spectrum empiric IV antibiotics", str(res["immediate_actions"]))

    def test_mild_urticarial_reaction(self):
        res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=0.2,
            onset_minutes=30,
            urticaria=True,
        )
        self.assertEqual(res["adjudicated_reaction"], ReactionType.ALLERGIC_MILD.value)
        self.assertEqual(res["severity_grade"], ReactionSeverity.GRADE_1_MILD.value)

    def test_isolated_fnhtr(self):
        res = TransfusionSafetyManager.adjudicate_reaction(
            temp_rise_c=1.2,
            onset_minutes=40,
        )
        self.assertEqual(res["adjudicated_reaction"], ReactionType.FNHTR.value)


class TestCLIExecution(unittest.TestCase):
    """Test CLI commands and JSON output format."""

    def test_cli_crossmatch_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["crossmatch", "--patient-abo", "A+", "--donor-abo", "O-", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["compatible"])

    def test_cli_donor_frequency_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["donor-frequency", "--patient-abo", "O+", "--antibodies", "Anti-K", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("overall_compatible_donor_percentage", data)

    def test_cli_mtp_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["mtp-status", "--prbc", "4", "--ffp", "4", "--platelets", "4", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ratio_compliance_pct"], 100.0)

    def test_cli_cold_chain_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["cold-chain", "--product-type", "pRBC", "--log-stream", "0:4.0,20:8.0,75:8.0", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["quarantine_required"])

    def test_cli_reaction_triage_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["reaction-triage", "--dyspnea", "--fluid-overload", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["adjudicated_reaction"], ReactionType.TACO.value)

    def test_cli_batch(self):
        # Verify batch processing of sample.csv
        sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample.csv")
        if not os.path.exists(sample_path):
            sample_path = "sample.csv"
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                ret = main(["batch", "-i", sample_path, "-o", tmp_path])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertGreaterEqual(len(lines), 16)  # Header + 15 rows
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestAdditionalTransfusionScenarios(unittest.TestCase):
    """Test additional component and temperature scenarios."""

    def test_platelet_cold_chain_excursion(self):
        mon = ColdChainMonitor(BloodProductType.PLATELETS)
        # Platelets must be 20-24°C; test excursion at 15°C for 70 min (> 60 min max)
        mon.record_reading(TempReading(0, 22.0, "s1"))
        mon.record_reading(TempReading(10, 15.0, "s1"))
        mon.record_reading(TempReading(85, 15.0, "s1"))
        res = mon.evaluate_compliance()
        self.assertTrue(res["quarantine_required"])

    def test_washed_red_cells_requirement(self):
        patient = PatientProfile("P_WASH", "Pt", "A+", special_requirements=["Washed"])
        unit_unwashed = BloodUnit("U_unwashed", BloodProductType.PRBC, "A+", is_washed=False)
        unit_washed = BloodUnit("U_washed", BloodProductType.PRBC, "A+", is_washed=True)
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient, unit_unwashed)["compatible"])
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient, unit_washed)["compatible"])

    def test_whole_blood_compatibility(self):
        # Whole blood contains both donor RBCs and donor plasma, so ABO/Rh must match exactly
        patient_o = PatientProfile("P_O", "Pt", "O+")
        unit_wb_o = BloodUnit("U_WB_O", BloodProductType.WHOLE_BLOOD, "O+")
        unit_wb_a = BloodUnit("U_WB_A", BloodProductType.WHOLE_BLOOD, "A+")
        self.assertTrue(CrossmatchEngine.crossmatch_unit(patient_o, unit_wb_o)["compatible"])
        self.assertFalse(CrossmatchEngine.crossmatch_unit(patient_o, unit_wb_a)["compatible"])


if __name__ == "__main__":
    unittest.main()
