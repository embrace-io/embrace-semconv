# The codegen part

The part is two fragments, added to a project the base skill set up (its "Adding a part"):

- `assets/project/Makefile`: the `codegen` section, the Makefile's last. It adds `generate` (to
  `generate-all::`), `validate-generated` (to `test::`) and `package-generated`, the last two as
  failing stubs the project replaces (`templates.md`, "The codegen contract").
- `assets/project/ci-validation.yaml`: the `validate-generated` job, and its entry in the
  aggregate job's `needs`. It installs weaver the way the base's jobs do: when the workflow uses
  the base's fallback for setup-weaver, use it here too.

The templates are the project's own: `templates/registry/<CODEGEN_TARGET>/`, written for the
language (`templates.md`). Copy the Makefile fragment rather than retyping it: it is indented with
tabs.

The base parts it needs: `core`, `templates` (with a collection for each kind of convention the
templates cover), and `no-drift` when the generated code is committed. Without committed code,
delete the job's "Compare committed code with the regenerated code" step and leave `no-drift` out.

## Settings

At the top of the section:

| Setting | Default | Meaning |
|---|---|---|
| `SOURCE_REGISTRY` | token | the registry the code is generated from (`sources.md`) |
| `CODEGEN_TARGET` | token | the template target under `templates/registry/` |
| `GENERATED_DIR` | token | the output directory, emptied on every run, so it holds only generated files |

With the part, the base's `TEMPLATE_TARGETS` includes `$(CODEGEN_TARGET)`, and `all:` usually
runs `validate-generated`.

## Tokens

| Token | Where | Value |
|---|---|---|
| `LANGUAGE` | Makefile `codegen` | the language generated, e.g. `Kotlin` |
| `SOURCE_REGISTRY` | Makefile `codegen` | see `sources.md`, e.g. `https://github.com/open-telemetry/semantic-conventions@v1.44.0[model]` |
| `CODEGEN_TARGET` | Makefile `codegen` | the template target's directory name, e.g. `kotlin` |
| `GENERATED_DIR` | Makefile `codegen` | where the code goes, relative to the project directory |
| `GENERATED_REPO_PATH` | CI job | `GENERATED_DIR` relative to the repo root, normalized (no `..`): e.g. `packages/sdk/src/generated` |
| `PROJECT_DIR` | CI job | the base's token: the project directory relative to the repo root |

## Projects in a subdirectory

A codegen project often lives in a subdirectory of an SDK's repo, with `GENERATED_DIR` pointing
out of it into the SDK's sources (`../src/generated`). Everything the base says about
subdirectories applies; `GENERATED_REPO_PATH` is that directory from the repo root, normalized,
since the CI job's drift check runs there.
