# Troubleshoot the Codex adapter

Start with `python3 ../../scripts/profile_request.py doctor <target>` from the
installed skill directory. A successful result reports the exact target and
true route, credential, and service fields.

| Symptom | Meaning | Action |
|---|---|---|
| Exit `2` and `standard input must contain one JSON object` | Input is empty, invalid, or not one object. | Send one bounded JSON object on standard input. |
| Exit `2` and a target mismatch | The caller target differs from the profile owner found by Team Mimir. | Correct the target or split the request; do not override classification. |
| `non_dialogue_disposition` | The paths include unsupported custody, unknown, prohibited, or external state. | Follow the returned classification and use the owning operational path. |
| Doctor reports unavailable or incompatible | Hermes route, credentials, service, or response contract is not ready. | Repair the external Hermes setup, then rerun doctor. |
| Hook shows a deny message | A supported edit is governed or could not be classified. | Use the skill and submit a bounded request. |
| Hook did not intercept an edit | The tool is outside `apply_patch`, `Edit`, and `Write`, or the hook is not trusted/enabled. | Treat the hook as advisory and run the skill explicitly. |
| Status rejects identifiers | The proposal identifier or 64-character revision digest is malformed. | Copy both values from the canonical response without editing them. |

The adapter prints a generic error rather than request contents. It does not
store a retry queue. After correcting a local input error or restoring the
producer boundary, rerun the same explicit command.

For custody and activation failures, use the
[Team Mimir operator hub](https://github.com/infiquetra/team-mimir/tree/main/docs/team/profile-evolution).
For route and dialogue behavior, use the
[Hermes producer troubleshooting guide](https://github.com/infiquetra/infiquetra-hermes-plugins/blob/main/docs/profile-evolution/troubleshooting.md).
