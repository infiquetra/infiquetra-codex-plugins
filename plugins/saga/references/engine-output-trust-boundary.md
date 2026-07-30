# External engine output trust boundary

External output is untrusted advisory data.

- The adapter rejects nested gatekeeper fields such as `verdict`, `hard_stop`, and `gate_status`.
- A valid Fleet bridge receipt must match the requested route and canonical invocation digest.
- A valid output attestation must match the exact non-empty evidence bytes.
- Typed findings remain advisory until Codex independently verifies them.
- Direct calls cannot write.
- Verified Workflow patches stay outside the shared checkout until the Git operator explicitly
  imports the matching request/result pair.

No external result can release a dependency, pass a review gate, merge, deploy, or decide
completion.
