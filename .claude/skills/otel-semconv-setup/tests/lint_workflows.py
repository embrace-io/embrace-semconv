"""Run the workflow checks that repos adopting the layout gate merges on, on the layout's
rendered workflows and actions, and fail on any finding.

Usage: lint_workflows.py [--uv UV] [--work DIR]
The semantic-conventions-client-side ruleset blocks a merge on every zizmor alert, and runs
zizmor through open-telemetry/shared-workflows: the latest release, with online audits, and the
`pedantic` persona on its registry branch (`regular` on main). This runs `pedantic`, which reports
everything `regular` does and more: `uv tool run zizmor@latest`, online when `gh auth token`
gives a token (offline otherwise, which it says). "latest" rather than a pin, because the point is
to see what those repos' next zizmor run will see: zizmor 1.30 added the audit that flags
`uses: ./...`. Renders are made with render_layout.py, so no weaver is needed.
"""
import os
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, run, work_dir

# Every feature and every collection, with and without the private sections.
COLLECTIONS = "attributes,attribute-groups,events,metrics,spans,entities"
RENDERS = {
    "all-private": "registry,docs,release,codegen,renovate,private," + COLLECTIONS,
    "all-public": "registry,docs,release,codegen,renovate," + COLLECTIONS,
}


def main():
    args = work_dir(__doc__, options=("--uv",))
    uv = args.uv or "uv"
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    env = dict(os.environ)
    zizmor = [uv, "tool", "run", "zizmor@latest", "--persona", "pedantic", "--format", "plain"]
    if token:
        env["GH_TOKEN"] = token
    else:
        zizmor.append("--offline")
        print("note: no `gh auth token`, so zizmor runs offline (no online audits)")
    version = subprocess.run([uv, "tool", "run", "zizmor@latest", "--version"],
                             capture_output=True, text=True).stdout.strip()
    print(f"using {version}")
    ok = True
    for name, chosen in RENDERS.items():
        dest = os.path.join(args.work, "lint", name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        if not run(args.work, f"lint-{name}-render",
                   [sys.executable, RENDER, dest, chosen,
                    os.path.join(FIXTURES, "tokens", "private-all.json")]):
            return 1
        result = subprocess.run(zizmor + [os.path.join(dest, ".github")], env=env,
                                capture_output=True, text=True)
        passed = result.returncode == 0
        print(("ok" if passed else "FAILED") + f": zizmor on {name}")
        if not passed:
            print(result.stdout + result.stderr)
        ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
