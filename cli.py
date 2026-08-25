#!/usr/bin/env python3
"""
Command-Line Interface for Blood Bank Transfusion Safety Agent
==============================================================
Provides interactive & scriptable commands for:
  - Crossmatch verification (RBC, FFP, Platelets)
  - Compatible donor frequency calculation
  - Massive Transfusion Protocol (MTP) 1:1:1 ratio compliance
  - AABB cold-chain storage excursion monitoring
  - Acute transfusion reaction triage & hemovigilance
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from blood_bank_transfusion import (
    BloodProductType,
    BloodUnit,
    ColdChainMonitor,
    CrossmatchEngine,
    MTPTracker,
    PatientProfile,
    TempReading,
    TransfusionSafetyManager,
)


def cmd_crossmatch(args: argparse.Namespace) -> int:
    antibodies = [a.strip() for a in args.antibodies.split(",") if a.strip()] if args.antibodies else []
    special_reqs = [r.strip() for r in args.special_reqs.split(",") if r.strip()] if args.special_reqs else []

    patient = PatientProfile(
        patient_id=args.patient_id,
        name=args.patient_name,
        abo_rh=args.patient_abo,
        identified_antibodies=antibodies,
        special_requirements=special_reqs,
    )

    antigen_phenotype = {}
    if args.donor_antigens:
        for item in args.donor_antigens.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                antigen_phenotype[k.strip()] = v.strip()

    unit = BloodUnit(
        unit_id=args.unit_id,
        product_type=BloodProductType(args.product_type),
        abo_rh=args.donor_abo,
        antigen_phenotype=antigen_phenotype,
        is_irradiated=args.irradiated,
        is_cmv_negative=args.cmv_negative,
        is_washed=args.washed,
        is_quarantined=args.quarantined,
    )

    res = CrossmatchEngine.crossmatch_unit(patient, unit)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("=" * 65)
        print("  TRANSFUSION COMPATIBILITY & CROSSMATCH REPORT")
        print("=" * 65)
        print(f"Patient ID             : {patient.patient_id} ({patient.abo_rh})")
        print(f"Donor Unit ID          : {unit.unit_id} ({unit.abo_rh} {unit.product_type.value})")
        print(f"Compatibility Decision : {'COMPATIBLE (Issue Approved)' if res['compatible'] else 'INCOMPATIBLE (HOLD)'}")
        print(f"Recommendation         : {res['recommendation']}")
        if res["reasons_incompatible"]:
            print("-" * 65)
            print("Incompatibility Reasons:")
            for r in res["reasons_incompatible"]:
                print(f"  [X] {r}")
        print("=" * 65)
    return 0


def cmd_donor_frequency(args: argparse.Namespace) -> int:
    antibodies = [a.strip() for a in args.antibodies.split(",") if a.strip()] if args.antibodies else []
    res = CrossmatchEngine.calculate_compatible_donor_frequency(args.patient_abo, antibodies)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("=" * 65)
        print("  COMPATIBLE DONOR PHENOTYPE FREQUENCY ESTIMATE")
        print("=" * 65)
        print(f"Patient ABO/Rh         : {res['patient_abo_rh']}")
        print(f"ABO Compatible Fraction: {res['abo_compatible_fraction'] * 100:.1f}%")
        print(f"Antigen-Neg Fraction   : {res['antigen_negative_fraction'] * 100:.2f}%")
        print(f"Overall Match Rate     : {res['overall_compatible_donor_percentage']:.4f}% (~1 in {res['estimated_units_to_screen_for_one_compatible']:,} units)")
        print("-" * 65)
        print(f"{'Antigen':<12} {'Prevalence':<14} {'Antigen-Negative Fraction':<25}")
        print("-" * 65)
        for ag in res["antigens_evaluated"]:
            print(f"{ag['antigen']:<12} {ag['prevalence']*100:.1f}%{'':<8} {ag['antigen_neg_frequency']*100:.1f}%")
        print("=" * 65)
    return 0


def cmd_mtp_status(args: argparse.Namespace) -> int:
    mtp = MTPTracker(
        event_id=args.event_id,
        patient_id=args.patient_id,
        issued_prbc=args.prbc,
        issued_ffp=args.ffp,
        issued_platelets=args.platelets,
        issued_cryo_pools=args.cryo,
    )
    status = mtp.get_status()

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("=" * 65)
        print("  MASSIVE TRANSFUSION PROTOCOL (MTP) STATUS")
        print("=" * 65)
        print(f"Event ID / Patient     : {status['event_id']} / {status['patient_id']}")
        print(f"Units Issued (RBC:FFP:PLT): {status['current_ratio']}")
        print(f"Ratio Compliance       : {status['ratio_compliance_pct']:.1f}%")
        print(f"Coagulopathy Status    : {status['coagulopathy_risk_status']}")
        print(f"Action Recommendation  : {status['recommendation']}")
        print("=" * 65)
    return 0


def cmd_cold_chain(args: argparse.Namespace) -> int:
    product = BloodProductType(args.product_type)
    monitor = ColdChainMonitor(product)

    # Ingest time, temp pairs e.g. "0:4.0,15:5.5,35:8.2,50:8.5,65:4.2"
    if args.log_stream:
        for entry in args.log_stream.split(","):
            if ":" in entry:
                t_str, temp_str = entry.split(":", 1)
                monitor.record_reading(TempReading(float(t_str), float(temp_str), "sensor-01"))

    eval_res = monitor.evaluate_compliance()
    if args.json:
        print(json.dumps(eval_res, indent=2))
    else:
        print("=" * 65)
        print("  AABB COLD CHAIN STORAGE EXCURSION REPORT")
        print("=" * 65)
        print(f"Product Type           : {eval_res['product_type']}")
        print(f"Acceptable Temp Range  : {eval_res['acceptable_temperature_range_c'][0]}°C to {eval_res['acceptable_temperature_range_c'][1]}°C")
        print(f"Out-of-Storage Time    : {eval_res['cumulative_out_of_storage_minutes']} min (Max: {eval_res['max_allowed_excursion_minutes']} min)")
        print(f"Quarantine Required?   : {'YES (Excursion Exceeded)' if eval_res['quarantine_required'] else 'NO (Safe)'}")
        print(f"Decision               : {eval_res['decision']}")
        print("=" * 65)
    return 0


def cmd_reaction_triage(args: argparse.Namespace) -> int:
    res = TransfusionSafetyManager.adjudicate_reaction(
        temp_rise_c=args.temp_rise,
        onset_minutes=args.onset_minutes,
        hypotension=args.hypotension,
        dyspnea=args.dyspnea,
        hemoglobinuria=args.hemoglobinuria,
        urticaria=args.urticaria,
        wheezing_or_stridor=args.wheezing,
        dat_positive=args.dat_positive,
        bacterial_gram_positive=args.gram_positive,
        jvd_or_fluid_overload=args.fluid_overload,
    )

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("=" * 70)
        print("  ACUTE TRANSFUSION REACTION ADJUDICATION")
        print("=" * 70)
        print(f"Diagnosis              : {res['adjudicated_reaction']}")
        print(f"Severity Classification: {res['severity_grade']}")
        print(f"FDA/CBER Mandatory     : {'YES' if res['fda_cber_reporting_mandatory'] else 'NO'}")
        print("-" * 70)
        print("Immediate Clinical Actions:")
        for act in res["immediate_actions"]:
            print(f"  [*] {act}")
        print("-" * 70)
        print("Laboratory Investigation Workup:")
        for w in res["investigation_workup"]:
            print(f"  [-] {w}")
        print("=" * 70)
    return 0


def cmd_interactive() -> int:
    print("Blood Bank Transfusion Safety Interactive CLI")
    print("Commands: crossmatch, donor-freq, mtp, cold-chain, triage, exit\n")
    while True:
        try:
            line = input("bloodbank> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        if line.lower() == "mtp":
            mtp = MTPTracker("MTP-DEMO", "P100", issued_prbc=6, issued_ffp=4, issued_platelets=2)
            print(json.dumps(mtp.get_status(), indent=2))
        elif line.lower() == "crossmatch":
            p = PatientProfile("P01", "John Doe", "A+", identified_antibodies=["Anti-K"])
            u = BloodUnit("U01", BloodProductType.PRBC, "A+", antigen_phenotype={"K": "+"})
            print(json.dumps(CrossmatchEngine.crossmatch_unit(p, u), indent=2))
        else:
            print(f"Command not recognized: {line}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blood_bank_transfusion_cli",
        description="Blood Bank & Transfusion Safety Management Platform",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: crossmatch
    p_cm = subparsers.add_parser("crossmatch", help="Perform patient-unit crossmatch check")
    p_cm.add_argument("--patient-id", type=str, default="P-001")
    p_cm.add_argument("--patient-name", type=str, default="Anonymous Patient")
    p_cm.add_argument("--patient-abo", type=str, required=True, help="Patient ABO/Rh (e.g. O+, A-)")
    p_cm.add_argument("--antibodies", type=str, default="", help="Comma-separated alloantibodies (e.g. Anti-K,Anti-Fya)")
    p_cm.add_argument("--special-reqs", type=str, default="", help="Special requirements (e.g. Irradiated,CMV-Negative)")
    p_cm.add_argument("--unit-id", type=str, default="U-9001")
    p_cm.add_argument("--product-type", type=str, default="pRBC", choices=["pRBC", "FFP", "Platelets", "Cryoprecipitate", "WholeBlood"])
    p_cm.add_argument("--donor-abo", type=str, required=True, help="Donor unit ABO/Rh (e.g. O-, A+)")
    p_cm.add_argument("--donor-antigens", type=str, default="", help="Donor antigens (e.g. K:-,Fya:+,D:+)")
    p_cm.add_argument("--irradiated", action="store_true", help="Unit is irradiated")
    p_cm.add_argument("--cmv-negative", action="store_true", help="Unit is CMV seronegative")
    p_cm.add_argument("--washed", action="store_true", help="Unit is washed")
    p_cm.add_argument("--quarantined", action="store_true", help="Unit is quarantined")
    p_cm.add_argument("--json", action="store_true", help="Output JSON")

    # Subcommand: donor-frequency
    p_df = subparsers.add_parser("donor-frequency", help="Calculate compatible donor phenotype frequency")
    p_df.add_argument("--patient-abo", type=str, required=True, help="Patient ABO/Rh (e.g. O-, A+)")
    p_df.add_argument("--antibodies", type=str, default="", help="Comma-separated antibodies (e.g. Anti-K,Anti-E)")
    p_df.add_argument("--json", action="store_true", help="Output JSON")

    # Subcommand: mtp-status
    p_mtp = subparsers.add_parser("mtp-status", help="Monitor Massive Transfusion Protocol balanced ratios")
    p_mtp.add_argument("--event-id", type=str, default="MTP-2026-001")
    p_mtp.add_argument("--patient-id", type=str, default="P-TRAUMA-01")
    p_mtp.add_argument("--prbc", type=int, default=6, help="pRBC units issued")
    p_mtp.add_argument("--ffp", type=int, default=6, help="FFP units issued")
    p_mtp.add_argument("--platelets", type=int, default=1, help="Platelet units issued")
    p_mtp.add_argument("--cryo", type=int, default=0, help="Cryoprecipitate pools issued")
    p_mtp.add_argument("--json", action="store_true", help="Output JSON")

    # Subcommand: cold-chain
    p_cc = subparsers.add_parser("cold-chain", help="Evaluate AABB cold chain temperature excursion log")
    p_cc.add_argument("--product-type", type=str, default="pRBC", choices=["pRBC", "FFP", "Platelets"])
    p_cc.add_argument("--log-stream", type=str, required=True, help="Timestamp:Temp pairs (e.g. 0:4.0,20:7.5,45:8.0,60:4.0)")
    p_cc.add_argument("--json", action="store_true", help="Output JSON")

    # Subcommand: reaction-triage
    p_rx = subparsers.add_parser("reaction-triage", help="Triage and investigate acute adverse transfusion reactions")
    p_rx.add_argument("--temp-rise", type=float, default=0.0, help="Temperature rise above baseline (°C)")
    p_rx.add_argument("--onset-minutes", type=int, default=15, help="Onset time after starting transfusion (minutes)")
    p_rx.add_argument("--hypotension", action="store_true", help="Systolic BP drop >= 30 mmHg or shock")
    p_rx.add_argument("--dyspnea", action="store_true", help="Acute respiratory distress or hypoxemia")
    p_rx.add_argument("--hemoglobinuria", action="store_true", help="Red/dark urine or hemoglobinemia")
    p_rx.add_argument("--urticaria", action="store_true", help="Hives, pruritus, rash")
    p_rx.add_argument("--wheezing", action="store_true", help="Stridor, bronchospasm, laryngeal edema")
    p_rx.add_argument("--dat-positive", action="store_true", help="Positive Direct Antiglobulin Test (DAT)")
    p_rx.add_argument("--gram-positive", action="store_true", help="Gram stain positive in unit bag")
    p_rx.add_argument("--fluid-overload", action="store_true", help="JVD, peripheral edema, elevated BNP")
    p_rx.add_argument("--json", action="store_true", help="Output JSON")

    # Subcommand: interactive
    subparsers.add_parser("interactive", help="Interactive REPL session")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "crossmatch":
        return cmd_crossmatch(args)
    elif args.command == "donor-frequency":
        return cmd_donor_frequency(args)
    elif args.command == "mtp-status":
        return cmd_mtp_status(args)
    elif args.command == "cold-chain":
        return cmd_cold_chain(args)
    elif args.command == "reaction-triage":
        return cmd_reaction_triage(args)
    elif args.command == "interactive":
        return cmd_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
