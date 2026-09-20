# Blood Bank Transfusion Agent

A Python reference implementation for several transfusion-medicine calculations and rule-based demonstrations:

- ABO/Rh component compatibility and alloantigen checks
- Compatible donor-frequency estimates
- Massive transfusion component-ratio tracking
- Blood-component temperature-excursion checks
- Rule-based adverse-reaction triage examples
- CSV batch processing through the command-line interface

> **Important:** This repository is a software demonstration and reference implementation. It is not a validated medical device and must not replace a transfusion service's approved procedures, qualified specialist review, or applicable regulatory requirements.

## Browser application

The repository includes a static browser interface (`index.html`, `styles.css`, `app.js`). It runs the same Python rule engine client-side with Pyodide. No application server is required, and data entered into the interface is processed in the browser.

The live GitHub Pages link is added here only after deployment has been verified.

## Command line

Requires Python 3.10 or later.

```bash
python cli.py crossmatch --patient-abo A+ --donor-abo O- --json
python cli.py donor-frequency --patient-abo O+ --antibodies "Anti-K,Anti-Fya" --json
python cli.py mtp-status --prbc 6 --ffp 6 --platelets 6 --json
python cli.py cold-chain --product-type pRBC --log-stream "0:4.0,10:8.5,55:8.5,56:4.0" --json
python cli.py reaction-triage --dyspnea --fluid-overload --json
python cli.py batch -i sample.csv -o results.csv
```

The installed console command delegates to the same CLI:

```bash
pip install -e .
blood-bank-transfusion-agent crossmatch --patient-abo A+ --donor-abo O- --json
```

## Python API

```python
from blood_bank_transfusion import (
    BloodProductType,
    BloodUnit,
    CrossmatchEngine,
    PatientProfile,
)

patient = PatientProfile(
    patient_id="PT-001",
    name="Example",
    abo_rh="A+",
    identified_antibodies=["Anti-K"],
)
unit = BloodUnit(
    unit_id="U-001",
    product_type=BloodProductType.PRBC,
    abo_rh="O+",
    antigen_phenotype={"K": "-"},
)

result = CrossmatchEngine.crossmatch_unit(patient, unit)
print(result)
```

## Clinical-model limitations

The implementation deliberately uses simplified rules. In particular, donor-frequency estimates use fixed population assumptions; cold-chain thresholds are model configuration rather than a substitute for a validated storage/transport process; reaction triage is not a diagnosis; and whole-blood compatibility defaults to ABO/Rh-identical use. Low-titer group O whole blood exceptions require defined local policy and are not automatically assumed by the model.

## Development

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest -q
python -m py_compile blood_bank_transfusion.py cli.py
node --check app.js
```

GitHub Actions runs the test suite on Python 3.10, 3.11, and 3.12. A separate workflow deploys the static browser application to GitHub Pages from `master`.

## Privacy

The command-line program processes local files. The browser application processes entered data in the current browser session. It downloads Pyodide from jsDelivr and loads the repository's Python source from the deployed site; it does not send case inputs to an application backend.

Avoid entering real patient identifiers into demonstration tools.

## License

MIT. See [LICENSE](LICENSE).
