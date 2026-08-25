# Blood Bank Transfusion Safety Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Tests: 30 Passing](https://img.shields.io/badge/Tests-30%20Passing-success.svg)](test_blood_bank_transfusion.py)
[![Domain: Transfusion Medicine & Hemovigilance](https://img.shields.io/badge/Domain-Transfusion%20Medicine-blueviolet.svg)](#)

A clinical decision support, immunogenetics compatibility, and hemovigilance platform adhering to **AABB (Association for the Advancement of Blood & Biotherapies)**, **FDA CBER**, and **CAP (College of American Pathologists)** standards.

---

## Core Capabilities

1. **ABO/Rh(D) Component-Specific Compatibility & Crossmatch**
   - Distinct immunologic compatibility rules for Packed Red Blood Cells (pRBC), Fresh Frozen Plasma (FFP), Platelets, and Cryoprecipitate.
   - Crossmatch verification enforcing negative phenotypes for patient unexpected red cell alloantibodies (e.g. Anti-K, Anti-Fya, Anti-Jka, Anti-E).
   - Verification of special processing requirements (Irradiation to prevent TA-GVHD, CMV seronegativity for immunosuppressed/neonatal patients, Washing for IgA deficiency / recurrent allergic reactions).

2. **Population Genetics Compatible Donor Frequency Estimation**
   - Probability modeling across multi-antigen phenotypes:
     $$P(\text{Compatible}) = P(\text{ABO/Rh}) \times \prod_{i} (1 - \text{Freq}(\text{Antigen}_i))$$
   - Units-to-screen estimation for rare blood inventory allocation.

3. **Massive Transfusion Protocol (MTP) 1:1:1 Ratio Tracking**
   - Real-time balanced resuscitation tracking (pRBC : FFP : Platelets).
   - Automated deficit detection and dilutional coagulopathy risk mitigation.

4. **AABB Cold Chain Excursion Monitoring**
   - Ingestion of continuous temperature sensor streams.
   - Validation against AABB standards:
     - **pRBC**: 1.0°C – 6.0°C (Max cumulative out-of-storage excursion: 30 minutes / 10°C rule).
     - **FFP / Cryo**: $\le -18.0^\circ\text{C}$.
     - **Platelets**: 20.0°C – 24.0°C with continuous agitation.
   - Automated quarantine triggers on excursion limit violations.

5. **Hemovigilance & Adverse Transfusion Reaction Triage**
   - Differential diagnosis: Acute Hemolytic (AHTR), TRALI, TACO, Anaphylactic, Sepsis, and Febrile Non-Hemolytic (FNHTR).
   - Clinical action pathways and direct antiglobulin test (DAT / Coombs) workup protocol.

---

## Installation

```bash
git clone https://github.com/example/blood-bank-transfusion-agent.git
cd blood-bank-transfusion-agent
```

*Requires Python 3.10+ with zero external third-party dependencies (pure standard library).*

---

## Command-Line Interface (CLI)

```bash
# 1. Crossmatch patient with donor unit
python cli.py crossmatch --patient-abo "A+" --donor-abo "O-" --antibodies "Anti-K" --donor-antigens "K:-,Fya:+"

# 2. Estimate compatible donor phenotype frequency
python cli.py donor-frequency --patient-abo "O-" --antibodies "Anti-K,Anti-E,Anti-Fya"

# 3. Monitor MTP resuscitation ratios
python cli.py mtp-status --prbc 6 --ffp 4 --platelets 1

# 4. Ingest and evaluate cold-chain temperature excursion stream
python cli.py cold-chain --product-type pRBC --log-stream "0:4.0,20:8.5,55:8.5,60:4.0"

# 5. Triage an acute transfusion reaction
python cli.py reaction-triage --dyspnea --fluid-overload
```

---

## Python API Usage

```python
from blood_bank_transfusion import (
    PatientProfile,
    BloodUnit,
    BloodProductType,
    CrossmatchEngine,
    MTPTracker,
    ColdChainMonitor,
    TempReading,
    TransfusionSafetyManager,
)

# Patient crossmatch
patient = PatientProfile("P100", "Jane Doe", "A+", identified_antibodies=["Anti-K"])
unit = BloodUnit("U500", BloodProductType.PRBC, "O+", antigen_phenotype={"K": "-", "Fya": "+"})

result = CrossmatchEngine.crossmatch_unit(patient, unit)
print("Compatible:", result["compatible"])
print("Recommendation:", result["recommendation"])

# MTP tracking
mtp = MTPTracker("MTP-01", "P100", issued_prbc=6, issued_ffp=6, issued_platelets=6)
status = mtp.get_status()
print(f"MTP Compliance: {status['ratio_compliance_pct']}% ({status['coagulopathy_risk_status']})")
```

---

## Test Suite

Run the full unit test suite:

```bash
python -m unittest test_blood_bank_transfusion.py
```

All 30 unit tests cover:
- ABO/Rh compatibility across pRBC, FFP, and Platelets
- Alloantibody and antigen phenotype clash detection
- Special requirement checks (Irradiated, CMV-, Washed, Quarantined)
- Population genetics compatible donor frequency calculations
- MTP ratio compliance and component deficit alerts
- Cold-chain excursion duration accumulation and quarantine decisions
- Adverse reaction clinical decision support (AHTR, TRALI, TACO, FNHTR)

---

## License

MIT License. See `LICENSE` for details.
