# Receipt Schema

Each run writes a Markdown receipt and a JSON sidecar under the target repo's configured receipt directory.

Required fields:

| field | meaning |
|---|---|
| `mode` | `generate-only`, `dry-run`, `publish`, or `partial-failure` |
| `target_repo` | portable target repository identifier, normally the Git top-level directory name |
| `target_repo_git` | target repository branch, HEAD, upstream, dirty flag, and porcelain status when invoked in a Git checkout |
| `target_id` | manifest target id |
| `manifest_sha256` | hash of the manifest file |
| `prompt_record_sha256` | hash of prompt sidecar when present |
| `local_assets` | paths, dimensions, byte sizes, and SHA-256 hashes |
| `publish_plan` | confirmation id and selected surfaces |
| `remote` | Discord readback ids and hashes for live publish |
| `partial_failure` | changed surfaces and failed surface when publish stops early |

Receipts must be human-readable, stable enough for rerun decisions, and redacted.
