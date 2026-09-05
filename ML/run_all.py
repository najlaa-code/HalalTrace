"""
Runs every pipeline back to back and prints a final comparison table.

  - cip_pipeline.py        turbidity/temp (SYNTHETIC placeholder data)  -> PASS/FAIL
  - potability_pipeline.py water chemistry (real dataset)               -> potable/not
  - tep_pipeline.py        TEP process variables (real dataset)         -> fault/no-fault
  - tempreg_pipeline.py    PID temperature control (real dataset)       -> in-spec/out-of-spec

These are four independent pipelines, not one merged model -- each has
its own sensors, its own label space, and its own saved model under
results/. Nothing here averages or combines their features; run_all.py
is purely a convenience runner + summary.

Output: results/summary.json, results/<name>_*.joblib per pipeline
"""

import json
import traceback

from common.paths import RESULTS_DIR

PIPELINES = [
    ("cip", "cip_pipeline"),
    ("potability", "potability_pipeline"),
    ("tep", "tep_pipeline"),
    ("tempreg", "tempreg_pipeline"),
]


def main():
    summary = {}
    for name, module_name in PIPELINES:
        print(f"\n{'=' * 70}\nRunning {name} pipeline ({module_name}.py)\n{'=' * 70}")
        try:
            module = __import__(module_name)
            report = module.main()
            summary[name] = {"status": "ok", "report": report}
        except Exception as exc:
            print(f"!! {name} pipeline failed: {exc}")
            traceback.print_exc()
            summary[name] = {"status": "failed", "error": str(exc)}

    print(f"\n{'=' * 70}\nSummary\n{'=' * 70}")
    for name, result in summary.items():
        if result["status"] == "ok":
            report = result["report"]
            best = report.get("best_model", "?")
            f1 = report.get("metrics", {}).get(best, {}).get("f1", float("nan"))
            print(f"{name:>12}: OK   best={best:<20} f1={f1:.3f}  n_features={report.get('n_features')}")
        else:
            print(f"{name:>12}: FAILED  ({result['error']})")

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved summary to {RESULTS_DIR / 'summary.json'}")

    return summary


if __name__ == "__main__":
    main()
