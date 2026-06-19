# Hermes Sandbox Boundary

This repository is the active Hermes/agent sandbox.

The upstream checkpoint repository is:

* gitugitu555/tm-trading-v92-core

Rules:

* Do not push to upstream.
* Do not modify upstream branch protection.
* Do not create upstream workflows.
* Do not run force-push.
* Do not rewrite upstream history.
* All experimental agent work must happen in gitugitu555/tm-trading-v92-hermes-lab.
* Any future promotion back to tm-trading-v92-core requires explicit human approval and a separate review process.

Checkpoint state:

tm-trading-v92-core is frozen as the canonical checkpoint after recovery. Its visible top history includes:

* 8b55d35183f84fa5f548a18625159a9abdce6219
* 405691fbc96e67dee89c09ec3d9dc7126261948f
* 8313cc5f9c2429139a00a2715b3e6669b32f7f51

The current sandbox tree must not contain:

* .github/workflows/manifest-check.yml
* scripts/verify_run_manifest.py
