"""Paths and helpers shared by the skill's test scripts. Not part of the skill's instructions."""
import argparse
import os
import subprocess

TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(TESTS)
ASSETS = os.path.join(SKILL, "assets")
FIXTURES = os.path.join(TESTS, "fixtures")
RENDER = os.path.join(TESTS, "render_layout.py")


def work_dir(description, flags=(), options=()):
    """Parse --work DIR (default tests/.work, which .gitignore keeps out of git), any FLAGS
    (on/off options), any OPTIONS (each taking a value), and scenario names."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("names", nargs="*", help="scenarios to run (default: all)")
    parser.add_argument("--work", default=os.path.join(TESTS, ".work"),
                        help="where to build scratch projects and logs")
    for flag in flags:
        parser.add_argument(flag, action="store_true")
    for option in options:
        parser.add_argument(option)
    args = parser.parse_args()
    os.makedirs(args.work, exist_ok=True)
    return args


def run(work, label, args, cwd=None):
    """Run a command, log its output to WORK/logs/LABEL.log, print ok/FAILED, return success."""
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    logs = os.path.join(work, "logs")
    os.makedirs(logs, exist_ok=True)
    log = os.path.join(logs, f"{label}.log")
    with open(log, "w") as f:
        f.write(result.stdout + result.stderr)
    print(("ok" if result.returncode == 0 else "FAILED") + f": {label} (log: {log})")
    return result.returncode == 0


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
