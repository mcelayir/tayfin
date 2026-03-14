#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run a Typer job CLI with one optional retry and simple JSON logs.
JOB_CMD=("$@")
if [ ${#JOB_CMD[@]} -eq 0 ]; then
  echo "Usage: run_job.sh <command...>"
  exit 2
fi

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

run_attempt() {
  local attempt=$1
  echo "$(ts) {\"event\": \"job_start\", \"cmd\": \"${JOB_CMD[*]}\", \"attempt\": ${attempt}}"
  "${JOB_CMD[@]}"
  local rc=$?
  echo "$(ts) {\"event\": \"job_end\", \"cmd\": \"${JOB_CMD[*]}\", \"attempt\": ${attempt}, \"exit_code\": ${rc}}"
  return ${rc}
}

echo "Running job: ${JOB_CMD[*]}"
run_attempt 1 || {
  rc=$?
  echo "$(ts) {\"event\": \"job_failed\", \"cmd\": \"${JOB_CMD[*]}\", \"attempt\": 1, \"exit_code\": ${rc}, \"action\": \"retry\"}"
  sleep 5
  run_attempt 2 || {
    rc2=$?
    echo "$(ts) {\"event\": \"job_failed\", \"cmd\": \"${JOB_CMD[*]}\", \"attempt\": 2, \"exit_code\": ${rc2}, \"action\": \"exit\"}"
    exit ${rc2}
  }
}

echo "Job completed"
