"""Probe: where does npm enforce a workspace root's devEngines? Evidence for the devEngines bullet in
reference/templates.md ("Platform integration").

Usage: devengines_probe.py WORKSPACE_ROOT WORKSPACE_DIR
Run it with a Node/npm that does NOT satisfy the root's devEngines. Result with npm 11.6.2 on
Node 24.13.0, as templates.md says: refused at the root and with the working directory inside
the workspace; not refused with `npm --prefix <workspace>`, which resolves the workspace's own
package.json.
"""
import subprocess
import sys


def main():
    root, workspace = sys.argv[1], sys.argv[2]
    cases = [
        ("root: npm exec", root, ["npm", "exec", "--", "node", "-v"]),
        ("cwd=workspace: npm exec", workspace, ["npm", "exec", "--", "node", "-v"]),
        ("root --prefix workspace: npm exec", root,
         ["npm", "--prefix", workspace, "exec", "--", "node", "-v"]),
    ]
    versions = [subprocess.run([tool, "-v"], capture_output=True, text=True).stdout.strip()
                for tool in ("npm", "node")]
    print(f"npm {versions[0]}, node {versions[1]}")
    for label, cwd, command in cases:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        refused = "EBADDEVENGINES" in result.stdout + result.stderr
        print(f"{label}: exit={result.returncode} refused={refused}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
