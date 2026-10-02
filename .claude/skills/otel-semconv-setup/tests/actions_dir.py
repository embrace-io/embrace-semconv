"""Check the Makefile's ACTIONS_DIR default: in a git repo it is the repo root's .github/actions,
however deep the project sits, and outside git it falls back to the project's own .github/actions.

Usage: actions_dir.py [--work DIR]
Each case renders a codegen project, then runs `make -n install-weaver` and checks that the
install script it would run exists. Needs git and GNU make; no weaver or network.
"""
import os
import re
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, run, work_dir


def render(work, dest, name):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    return run(work, f"actions-dir-{name}-render",
               [sys.executable, RENDER, dest, "codegen,attributes",
                os.path.join(FIXTURES, "tokens", "core-codegen.json")])


def script_path(project, env=None):
    """The install script `make -n install-weaver` would run in PROJECT, or None."""
    result = subprocess.run(["make", "-C", project, "-n", "install-weaver"], capture_output=True,
                            text=True, env=env)
    match = re.search(r'bash "([^"]+/setup-weaver/install-weaver\.sh)"', result.stdout)
    if not match:
        print(result.stdout + result.stderr)
        return None
    path = match.group(1)
    return path if os.path.isabs(path) else os.path.join(project, path)


def main():
    args = work_dir(__doc__)
    base = os.path.join(args.work, "actions-dir")
    problems = []

    # A project three levels down in a git repo, with the actions at the repo root.
    repo = os.path.join(base, "repo")
    if not render(args.work, repo, "subdirectory"):
        return 1
    subprocess.run(["git", "init", "-q", repo], check=True)
    project = os.path.join(repo, "packages", "sdk", "semconv")
    os.makedirs(project)
    for name in ("Makefile", "versions.env"):
        shutil.move(os.path.join(repo, name), os.path.join(project, name))
    path = script_path(project)
    expected = os.path.realpath(os.path.join(repo, ".github", "actions", "setup-weaver",
                                             "install-weaver.sh"))
    if not path or os.path.realpath(path) != expected or not os.path.isfile(path):
        problems.append(f"subdirectory project: install-weaver runs {path}, expected {expected}")

    # A project outside any git checkout: the fallback, its own .github/actions. The ceiling stops
    # git from finding a repo that happens to contain the work directory.
    alone = os.path.join(base, "no-git", "project")
    if not render(args.work, alone, "no-git"):
        return 1
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=os.path.dirname(alone))
    path = script_path(alone, env)
    expected = os.path.realpath(os.path.join(alone, ".github", "actions", "setup-weaver",
                                             "install-weaver.sh"))
    if not path or os.path.realpath(path) != expected or not os.path.isfile(path):
        problems.append(f"project outside git: install-weaver runs {path}, expected {expected}")

    for problem in problems:
        print("ACTIONS_DIR PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": actions-dir (subdirectory and no-git)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
