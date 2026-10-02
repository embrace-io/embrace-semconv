"""Prepare one field-test round: freeze the skill, render the prompts, and (with --setup) create
the local worktrees and empty repos. See tests/README.md, "Field tests".

Usage: new_round.py N --workspace DIR --clones DIR --github-owner OWNER [--setup]
- --workspace: where the round's snapshot, worktrees, prompts, scratch and results go.
- --clones: the directory holding a clone of each repo targets.json names, under the repo's name
  (open-telemetry/opentelemetry-android in DIR/opentelemetry-android).
- --github-owner: the GitHub user or org that owns T2c's private test repo.
Snapshots the live skill, WITHOUT tests/, to <workspace>/skill-rN/<skill>, so agents test a fixed
copy and never see the harness; refuses to overwrite one. Renders field/prompts/*.txt into
<workspace>/rN/prompts/, and makes rN/scratch/<test>/ and rN/results/. --setup runs
`git worktree add` for each test with a repo (a new skilltest-rN/<branch> at its base) and
`git init -b main` for each new-repo test. It prints, but never runs, the outward-facing step:
creating the private GitHub repo T2c pushes to.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("round", type=int)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--clones", required=True)
    parser.add_argument("--github-owner", required=True)
    parser.add_argument("--setup", action="store_true")
    args = parser.parse_args()
    round_id = f"r{args.round}"
    workspace = os.path.abspath(os.path.expanduser(args.workspace))
    clones = os.path.abspath(os.path.expanduser(args.clones))
    with open(os.path.join(HERE, "targets.json")) as f:
        targets = json.load(f)
    test_repo = f"semconv-skill-test-{round_id}"
    live_repo = subprocess.run(["git", "-C", SKILL, "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True).stdout.strip() or SKILL

    snapshot = os.path.join(workspace, f"skill-{round_id}", os.path.basename(SKILL))
    if os.path.exists(snapshot):
        raise SystemExit(f"{snapshot} exists; not overwriting")
    shutil.copytree(SKILL, snapshot, ignore=shutil.ignore_patterns("tests"))
    print(f"snapshot: {snapshot}")

    base = os.path.join(workspace, round_id)
    values = {"{{workspace}}": workspace, "{{round}}": round_id, "{{test_repo}}": test_repo,
              "{{github_owner}}": args.github_owner, "{{live_skill_repo}}": live_repo}
    os.makedirs(os.path.join(base, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(base, "results"), exist_ok=True)
    for name in sorted(os.listdir(os.path.join(HERE, "prompts"))):
        with open(os.path.join(HERE, "prompts", name)) as f:
            text = f.read()
        for key, value in values.items():
            text = text.replace(key, value)
        if "{{" in text:
            raise SystemExit(f"{name}: unresolved placeholder")
        with open(os.path.join(base, "prompts", name), "w") as f:
            f.write(text)
        os.makedirs(os.path.join(base, "scratch", name[:-4]), exist_ok=True)
    print(f"prompts: {os.path.join(base, 'prompts')}")

    for spec in targets["tests"].values():
        if "worktree" not in spec:
            continue
        dest = os.path.join(base, spec["worktree"])
        if spec.get("new_repo"):
            command = ["git", "init", "-b", "main", dest]
        else:
            clone = os.path.join(clones, spec["repo"].split("/")[1])
            command = ["git", "-C", clone, "worktree", "add", "-b",
                       f"skilltest-{round_id}/{spec['branch']}", dest, spec["base"]]
        if args.setup:
            subprocess.run(command, check=True)
        else:
            print("would run: " + " ".join(command))
    print("then create the private repo T2c pushes to (outward-facing, so by hand):\n"
          f"  gh repo create {args.github_owner}/{test_repo} --private")
    return 0


if __name__ == "__main__":
    sys.exit(main())
