"""
Automated promotion gate: compares the latest run's test F1 against the
current Production-stage model's test F1, and only promotes if it's better.
This keeps a bad retrain from silently replacing a working gatekeeper model.

Usage:
    python mlflow/promote_model.py --model-name codesentinel-vuln-classifier
"""
from __future__ import annotations

import argparse

import mlflow
from mlflow.tracking import MlflowClient


def get_stage_f1(client: MlflowClient, model_name: str, stage: str) -> float | None:
    versions = client.get_latest_versions(model_name, stages=[stage])
    if not versions:
        return None
    run = client.get_run(versions[0].run_id)
    return run.data.metrics.get("test_f1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="codesentinel-vuln-classifier")
    parser.add_argument("--tracking-uri", default="mlflow/mlruns")
    parser.add_argument("--min-improvement", type=float, default=0.0,
                         help="Require the new model to beat production by at least this much F1.")
    args = parser.parse_args()

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()

    latest_versions = client.get_latest_versions(args.model_name, stages=["None", "Staging"])
    if not latest_versions:
        print("No un-promoted model versions found. Nothing to do.")
        return
    candidate = max(latest_versions, key=lambda v: int(v.version))
    candidate_run = client.get_run(candidate.run_id)
    candidate_f1 = candidate_run.data.metrics.get("test_f1")

    if candidate_f1 is None:
        print(f"Candidate version {candidate.version} has no test_f1 metric logged — refusing to promote.")
        return

    production_f1 = get_stage_f1(client, args.model_name, "Production")

    print(f"Candidate version {candidate.version}: test_f1={candidate_f1:.4f}")
    print(f"Current production: test_f1={production_f1}")

    if production_f1 is None or candidate_f1 >= production_f1 + args.min_improvement:
        client.transition_model_version_stage(
            name=args.model_name,
            version=candidate.version,
            stage="Production",
            archive_existing_versions=True,
        )
        print(f"Promoted version {candidate.version} to Production.")
    else:
        client.transition_model_version_stage(
            name=args.model_name,
            version=candidate.version,
            stage="Staging",
        )
        print(f"Candidate did not beat production (+{args.min_improvement} margin). "
              f"Moved to Staging instead.")


if __name__ == "__main__":
    main()
