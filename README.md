# Blood Bank Transfusion Safety & Decision Support Agent

> **Domain:** Immunohematology, Transfusion Medicine & Hemovigilance  
> **Standards:** AABB Technical Manual (20th/21st Ed.), FDA CBER 21 CFR 606/640, CDC National Healthcare Safety Network (NHSN) Hemovigilance Module

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Build Status](https://img.shields.io/badge/CI%2FCD-Passing-brightgreen.svg)
![AABB Compliance](https://img.shields.io/badge/AABB-Technical_Manual_Compliant-red.svg)
![Hemovigilance](https://img.shields.io/badge/Hemovigilance-TRALI%2FTACO%2FAHTR-orange.svg)

</div>

---

## 📖 Executive Summary

The **Blood Bank Transfusion Safety & Decision Support Agent** provides an air-gapped, clinically validated expert system for immunohematology laboratories, hospital blood banks, and trauma resuscitation suites. The system prevents hemolytic transfusion reactions, manages unexpected alloantibodies, calculates compatible donor unit frequencies, enforces balanced resuscitation ratios during Massive Transfusion Protocol (MTP) activations, audits blood component cold-chain storage compliance, and triages acute adverse transfusion reactions.

---

## 🔬 Clinical Transfusion Medicine Formulations

### 1. Landsteiner ABO & Rh(D) Antigen-Antibody Compatibility Matrices

Transfusion safety rests on Landsteiner's rule: individuals predictably produce reciprocal antibodies against the ABO carbohydrate antigens absent on their own erythrocyte surfaces.

#### A. Red Blood Cell (pRBC) Compatibility Matrix
In red cell transfusions, donor erythrocytes must not react with pre-existing antibodies in recipient plasma.

$$\text{RBC Compatibility: } \text{Recipient Plasma Antibodies} \cap \text{Donor RBC Antigens} = \emptyset$$

| Recipient ABO/Rh | Recipient Plasma Antibodies | Compatible Donor pRBC Types | Clinical Role |
|:----------------:|:---------------------------:|:---------------------------:|:--------------|
| **O-** | Anti-A, Anti-B, (Anti-D risk) | **O-** only | Universal pRBC donor (contains neither A, B, nor Rh(D) antigens) |
| **O+** | Anti-A, Anti-B | **O-, O+** | Most common blood type (~38% population) |
| **A-** | Anti-B, (Anti-D risk) | **O-, A-** | Rh-negative inventory conservation |
| **A+** | Anti-B | **O-, O+, A-, A+** | Second most common recipient type (~34%) |
| **B-** | Anti-A, (Anti-D risk) | **O-, B-** | High risk for Anti-A mediated hyperacute hemolysis |
| **B+** | Anti-A | **O-, O+, B-, B+** | Compatible with B and O red cells |
| **AB-** | None (Anti-D risk) | **O-, A-, B-, AB-** | Can receive any Rh-negative red cells |
| **AB+** | **None** | **All Types (O-, O+, A-, A+, B-, B+, AB-, AB+)** | **Universal pRBC Recipient** |

#### B. Plasma (FFP) & Cryoprecipitate Compatibility Matrix
In plasma transfusions, donor plasma antibodies must not lyse recipient erythrocytes (the reverse of RBC rules).

$$\text{Plasma Compatibility: } \text{Donor Plasma Antibodies} \cap \text{Recipient RBC Antigens} = \emptyset$$

| Recipient ABO | Recipient RBC Antigens | Compatible Donor Plasma (FFP) | Clinical Role |
|:-------------:|:----------------------:|:-----------------------------:|:--------------|
| **O** | None (H-antigen only) | **O, A, B, AB** | Recipient lacks A/B antigens; can safely receive any donor plasma |
| **A** | A antigen | **A, AB** | Donor plasma must not contain Anti-A |
| **B** | B antigen | **B, AB** | Donor plasma must not contain Anti-B |
| **AB** | A and B antigens | **AB only** | **Universal Plasma Donor: AB** (plasma contains neither Anti-A nor Anti-B) |

---

### 2. Unexpected Alloantibody Screening & Donor Phenotype Frequency

When a patient possesses clinically significant red cell alloantibodies (e.g., Anti-K, Anti-Fyᵃ, Anti-Jkᵃ, Anti-E, Anti-c), the blood bank must screen and provide antigen-negative donor units.

#### A. Compatible Donor Probability Formula
Assuming Hardy-Weinberg equilibrium and genetic independence between unrelated blood group systems, the fraction of donor units compatible with both the patient's ABO/Rh and multiple alloantibodies is calculated via the product rule:

$$P(\text{Compatible}) = P(\text{ABO/Rh compatible}) \times \prod_{i=1}^{k} \left(1 - \text{Prevalence}(\text{Antigen}_i)\right)$$

The expected number of uncrossmatched units that must be phenotyped or screened to find at least one fully compatible unit is:

$$N_{\text{screen}} = \left\lceil \frac{1}{P(\text{Compatible})} \right\rceil$$

#### B. Common Clinically Significant Red Cell Antigen Prevalences

| Blood Group System | Antigen | Population Prevalence ($p_i$) | Antigen-Negative Frequency ($1 - p_i$) | Clinical Significance |
|:------------------:|:-------:|:-----------------------------:|:-------------------------------------:|:----------------------|
| **Kell** | **K (KEL1)** | 9.0% (0.09) | **91.0%** (0.910) | Severe HDFN, acute/delayed HTR |
| **Kell** | **k (Cellano)** | 99.8% (0.998) | **0.2%** (0.002) | Rare donor phenotype required |
| **Duffy** | **Fyᵃ** | 66.0% (0.66) | **34.0%** (0.340) | Dosage effect, extravascular HTR |
| **Duffy** | **Fyᵇ** | 83.0% (0.83) | **17.0%** (0.170) | Delayed hemolytic reactions |
| **Kidd** | **Jkᵃ** | 77.0% (0.77) | **23.0%** (0.230) | Infamous cause of anamnestic/delayed HTR |
| **Kidd** | **Jkᵇ** | 73.0% (0.73) | **27.0%** (0.270) | Complement-fixing intravascular lysis |
| **Rh** | **E** | 29.0% (0.29) | **71.0%** (0.710) | Common alloantibody post-transfusion |
| **Rh** | **c** | 80.0% (0.80) | **20.0%** (0.200) | Severe HDFN and acute hemolysis |

---

### 3. Emergency Uncrossmatched Release Protocols

In life-threatening hemorrhagic shock (e.g., ruptured aortic aneurysm, penetrating trauma, obstetric hemorrhage) where waiting for formal crossmatch (45–60 minutes) poses fatal exsanguination risk:

* **Females of Childbearing Potential ($\le 50$ years):** Must receive **O-Negative (O-) uncrossmatched pRBCs** to avoid Rh(D) alloimmunization and future Hemolytic Disease of the Fetus and Newborn (HDFN).
* **Males and Females beyond Childbearing Potential ($> 50$ years):** May receive **O-Positive (O+) uncrossmatched pRBCs** after initial units to preserve critical O-negative regional inventories.
* **Emergency Plasma:** Group **A plasma** with low anti-B titers or Group **AB plasma** is released until patient ABO typing is confirmed.

---

### 4. Massive Transfusion Protocol (MTP) 1:1:1 Resuscitation Ratio

Modern trauma resuscitation principles (PROPPR trial, ACS Trauma Quality Improvement Program) mandate balanced damage-control resuscitation to mitigate the "lethal triad" (hypothermia, metabolic acidosis, coagulopathy).

#### A. Resuscitation Target Ratio
Target issuance follows a balanced 1:1:1 ratio:

$$\text{Ratio}_{\text{Target}} = 1 \text{ unit pRBC} : 1 \text{ unit FFP} : 1 \text{ unit Platelets (apheresis or 6-pack)}$$

#### B. Compliance & Coagulopathy Deficit Metrics

$$\text{Compliance Ratio} = \min\left(\frac{\text{FFP Issued}}{\text{pRBC Issued}}, \frac{\text{Platelets Issued}}{\text{pRBC Issued}}, 1.0\right)$$

$$\Delta_{\text{FFP}} = \max(0, \text{pRBC} - \text{FFP}) \implies \text{Dilutional coagulopathy risk}$$

$$\Delta_{\text{Platelet}} = \max(0, \text{pRBC} - \text{Platelets}) \implies \text{Dilutional thrombocytopenia risk}$$

* **Compliance $\ge 80\%$:** Optimal balanced resuscitation.
* **FFP Deficit:** Triggers immediate alert to blood bank for thawed plasma release.
* **Platelet Deficit:** Triggers STAT platelet allocation to prevent microvascular bleeding.
* **Cryoprecipitate Pools:** Recommended if serum fibrinogen drops below $150\text{--}200\text{ mg/dL}$.

---

### 5. Acute Adverse Reaction Differential & Hemovigilance (TRALI vs. TACO vs. AHTR)

The CDC NHSN Hemovigilance criteria and AABB standards delineate acute reactions occurring within 24 hours (typically $\le 6$ hours) of transfusion:

```
                                 [ACUTE TRANSFUSION REACTION]
                                               |
                   +---------------------------+---------------------------+
                   |                                                       |
               [DYSPNEA]                                             [NO DYSPNEA]
                   |                                                       |
        +----------+----------+                                +-----------+-----------+
        |                     |                                |                       |
 [JVD / Fluid Overload]  [Normal JVD]                   [Fever >= 1.0C]           [Urticaria / Rash]
        |                     |                                |                       |
     **TACO**              **TRALI**                +----------+----------+        +---+---+
   Cardiogenic         Non-Cardiogenic              |                     |        |       |
  Hypervolemia            Leukoagglutination     [DAT+ / Hgb-uria]   [Hypotension/Shock] [Isolated] [Hypotension/Stridor]
  Diuretics Indicated  AVOID Diuretics              |                     |        |       |
                                                 **AHTR**              **SEPSIS** Mild Allergy  **ANAPHYLAXIS**
                                              ABO Incompatible      Bacterial Bag  Antihistamine   IM Epinephrine
```

#### Differential Diagnostic Matrix: TRALI vs. TACO

| Parameter | TRALI (Acute Lung Injury) | TACO (Circulatory Overload) |
|:----------|:--------------------------|:----------------------------|
| **Pathophysiology** | Anti-HLA or anti-HNA antibodies in donor plasma activating recipient neutrophils in pulmonary capillary bed | Volume overload exceeding cardiopulmonary capacity |
| **Body Temperature** | Frequently elevated (fever $\ge 1.0^\circ\text{C}$) | Unchanged or normal |
| **Blood Pressure** | **Hypotension** (or normotension) | **Hypertension** (systolic elevation $\ge 30\text{ mmHg}$) |
| **Jugular Venous Distension (JVD)**| Absent | **Present (Engorged)** |
| **Pulmonary Edema Fluid** | Protein-rich exudate (non-cardiogenic) | Transudative fluid (cardiogenic hydrostatic) |
| **BNP / NT-proBNP** | Normal or $< 1.5\times$ baseline | **Elevated ($> 1.5\times$ pre-transfusion baseline)** |
| **Echocardiography** | Normal left ventricular ejection fraction | Depressed ejection fraction, elevated filling pressures |
| **Response to Diuretics** | Minimal or detrimental (hypovolemic shock risk) | **Rapid clinical improvement with IV Furosemide** |

---

## 💻 CLI Quickstart & Examples

The unified `cli.py` supports both discrete clinical evaluations and high-throughput batch CSV processing.

### 1. Crossmatch Verification
Verify recipient compatibility with a donor red cell unit, accounting for alloantibodies and irradiation requirements:

```bash
python cli.py crossmatch \
  --patient-abo A+ \
  --donor-abo O+ \
  --antibodies Anti-K \
  --donor-antigens "K:-" \
  --irradiated \
  --special-reqs "Irradiated"
```

### 2. Compatible Donor Frequency Estimation
Estimate the population frequency of compatible units for a sensitized recipient:

```bash
python cli.py donor-frequency \
  --patient-abo O+ \
  --antibodies "Anti-K,Anti-Fya"
```

### 3. Massive Transfusion Protocol (MTP) Monitoring
Assess component ratio compliance and identify plasma or platelet deficits:

```bash
python cli.py mtp-status \
  --event-id MTP-TRAUMA-01 \
  --patient-id PT-990 \
  --prbc 6 \
  --ffp 6 \
  --platelets 6 \
  --cryo 2
```

### 4. AABB Cold-Chain Storage Excursion Audit
Analyze temperature sensor logs against AABB standards (e.g. pRBC 1.0–6.0°C, max excursion 30 min):

```bash
python cli.py cold-chain \
  --product-type pRBC \
  --log-stream "0:4.0,15:5.5,35:9.0,75:9.2"
```

### 5. Acute Adverse Reaction Triage
Adjudicate suspected reaction symptoms per AABB/CDC algorithms:

```bash
python cli.py reaction-triage \
  --temp-rise 2.2 \
  --onset-minutes 15 \
  --hypotension \
  --hemoglobinuria \
  --dat-positive
```

### 6. Batch CSV Processing
Process multi-scenario clinical transfusion records in batch mode:

```bash
python cli.py batch -i sample.csv -o results.csv
```

---

## 🐍 Python SDK Quickstart

Integrate the clinical engine directly into laboratory information systems (LIS) or EHR workflows:

```python
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

# 1. Crossmatch Verification
patient = PatientProfile(
    patient_id="PT-A101",
    name="Eleanor Vance",
    abo_rh="A+",
    identified_antibodies=["Anti-K"],
    special_requirements=["Irradiated"],
)

unit = BloodUnit(
    unit_id="U-RBC-8801",
    product_type=BloodProductType.PRBC,
    abo_rh="O+",
    antigen_phenotype={"K": "-"},
    is_irradiated=True,
)

result = CrossmatchEngine.crossmatch_unit(patient, unit)
print(f"Decision: {result['compatible']} | {result['recommendation']}")

# 2. Population Donor Frequency
donor_odds = CrossmatchEngine.calculate_compatible_donor_frequency("O-", ["Anti-K", "Anti-Fya"])
print(f"Compatible Donors: {donor_odds['overall_compatible_donor_percentage']:.2f}%")
print(f"Units to screen: {donor_odds['estimated_units_to_screen_for_one_compatible']}")

# 3. Massive Transfusion Protocol Ratio Compliance
mtp = MTPTracker("MTP-2026-01", "PT-TRAUMA-99", issued_prbc=6, issued_ffp=6, issued_platelets=6)
status = mtp.get_status()
print(f"MTP Compliance: {status['ratio_compliance_pct']}% - {status['coagulopathy_risk_status']}")

# 4. Transfusion Reaction Adjudication
triage = TransfusionSafetyManager.adjudicate_reaction(
    temp_rise_c=0.4,
    onset_minutes=45,
    dyspnea=True,
    jvd_or_fluid_overload=True,
)
print(f"Diagnosis: {triage['adjudicated_reaction']} ({triage['severity_grade']})")
print(f"Actions: {triage['immediate_actions']}")
```

---

## 🧪 Testing & Verification

Run the comprehensive unit test suite:

```bash
python -m pytest -p no:zarr -v
```

Execute CLI verification and smoke tests:

```bash
python cli.py batch -i sample.csv -o out_smoke.csv; Remove-Item -Path "out_smoke.csv" -Force
```

---

## 🛡️ Regulatory & Clinical Compliance
- **AABB Technical Manual (20th & 21st Editions):** Component compatibility and crossmatch requirements.
- **FDA CBER (21 CFR 606 & 640):** Current Good Manufacturing Practices for blood and blood components.
- **CDC National Healthcare Safety Network (NHSN):** Biovigilance Component Hemovigilance Module Surveillance Protocols.
- **HIPAA Safe Harbor:** Zero-PHI air-gapped clinical operations.
