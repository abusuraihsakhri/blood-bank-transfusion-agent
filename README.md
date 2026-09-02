# Blood Bank Transfusion Agent

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Blood Bank Transfusion Agent** is an advanced analytical and computational platform implementing ABO/Rh Compatibility, Antibody Screen & Crossmatch Safety.

Blood Bank Crossmatch Testing: compatibility determination, antigen matching, antibody screening.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`BloodProductType`** — dedicated module for blood product type evaluation and state verification.
- **`ReactionType`** — dedicated module for reaction type evaluation and state verification.
- **`ReactionSeverity`** — dedicated module for reaction severity evaluation and state verification.
- **`PatientProfile`** — dedicated module for patient profile evaluation and state verification.
- **`BloodUnit`** — dedicated module for blood unit evaluation and state verification.
- **`CrossmatchEngine`**: Evaluates immunologic compatibility for RBC, FFP, Platelets, and Cryoprecipitate.

---

## 📐 Mathematical Formulation & Logic

```text
  score = match / total if total else 0.0
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --patient-id <value> --patient-name <value> --patient-abo <value> --antibodies <value>
```

### Parameter Reference
- `--patient-id`: Specifies input measurement or parameter value.
- `--patient-name`: Specifies input measurement or parameter value.
- `--patient-abo`: Specifies input measurement or parameter value.
- `--antibodies`: Specifies input measurement or parameter value.
- `--special-reqs`: Specifies input measurement or parameter value.
- `--unit-id`: Specifies input measurement or parameter value.
- `--product-type`: Specifies input measurement or parameter value.
- `--donor-abo`: Specifies input measurement or parameter value.
- `--donor-antigens`: Specifies input measurement or parameter value.
- `--irradiated`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `suite_name` | Parameter / observation metric | Required |
| `system_slug` | Parameter / observation metric | Required |
| `standard_reference` | Parameter / observation metric | Required |
| `test_cases` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t blood-bank-transfusion-agent .
docker run -p 8000:8000 blood-bank-transfusion-agent
```
