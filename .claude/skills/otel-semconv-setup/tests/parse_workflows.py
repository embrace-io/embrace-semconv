# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Parse every workflow and action file the other scripts rendered, and check that each CI gate job
needs exactly the other jobs. zizmor (lint_workflows.py) checks neither.

Usage: uv run tests/parse_workflows.py [WORK_DIR]   (default: tests/.work)
Run matrix.py and codegen.py first; they render the projects this reads.
"""
import glob
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, ".work")
    paths = sorted(p for pattern in ("*.yml", "*.yaml")
                   for p in glob.glob(os.path.join(work, "*", "*", ".github", "**", pattern),
                                      recursive=True))
    if not paths:
        raise SystemExit(f"no rendered workflows under {work}: run matrix.py and codegen.py first")
    failed = False
    for path in paths:
        rel = os.path.relpath(path, work)
        try:
            with open(path) as f:
                doc = yaml.safe_load(f)
        except yaml.YAMLError as error:
            failed = True
            print(f"FAILED {rel}: {error}")
            continue
        jobs = doc.get("jobs") if isinstance(doc, dict) else None
        if jobs and os.path.basename(path) == "ci-validation.yaml":
            for job_id, job in jobs.items():
                if job.get("needs") and "always()" in str(job.get("if", "")):
                    needs = sorted(job["needs"] if isinstance(job["needs"], list) else [job["needs"]])
                    expected = sorted(set(jobs) - {job_id})
                    if needs != expected:
                        failed = True
                        print(f"FAILED {rel}: gate {job_id} needs {needs}, jobs are {expected}")
        print(f"ok {rel}" + (f" jobs={','.join(jobs)}" if jobs else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
