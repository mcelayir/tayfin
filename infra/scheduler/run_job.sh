#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to run a Typer job CLI and optionally retry once on failure.
JOB_CMD="$@"
if [ -z "${JOB_CMD}" ]; then
  echo "Usage: run_job.sh <command...>"
  exit 2
fi

echo "Running job: ${JOB_CMD}"
${JOB_CMD}
EXIT_CODE=$?
if [ ${EXIT_CODE} -ne 0 ]; then
  echo "Job failed with ${EXIT_CODE}, exiting"
  exit ${EXIT_CODE}
fi

echo "Job completed"
