# Codex front-door architecture

The Codex plugin is a thin adapter between a proposed repository edit and two
producer-owned contracts. Team Mimir owns path classification. Hermes owns
dialogue, health, routing, credentials, and the target profile's response.

![Codex front-door architecture](assets/profile-evolution-codex-front-door.png)

## Request flow

1. The skill collects bounded intent, repository-relative paths, and sanitized
   evidence references.
2. `profile_request.py` executes the active Team Mimir classifier. It does not
   copy or reinterpret classifier policy.
3. Ordinary work returns locally. A supported governed result must name exactly
   one target profile.
4. The adapter runs canonical `hermes profile-request doctor` and sends a
   version-1 proposal envelope to `suggest`, `reply`, `resume`, or `status`.
5. Hermes validates the route and owns the live dialogue. The target may accept,
   decline, defer, ask a question, or do nothing.

The adapter validates response shapes against pinned producer conformance
fixtures. The fixtures are compatibility evidence, not a second implementation.

## Identity and authority

The proposal target is the profile named by classification. The requester and
delegation chain describe who asked and which harness transported the request.
The Codex adapter uses a claimed `harness/codex` identity and never marks itself
as a verified profile.

The plugin cannot mutate profile files, commit a change, settle a mutation,
select a provider, store credentials, or operate an offline queue. Target-owned
changes continue through the Hermes producer and the deployment path documented
by the [Team Mimir operator hub](https://github.com/infiquetra/team-mimir/tree/main/docs/team/profile-evolution).

## Host-specific boundary

Codex provides skill discovery and a trusted `PreToolUse` hook. The hook is an
advisory guardrail for supported file-edit tools, not complete enforcement.
Classification or hook parsing failure returns a deny-shaped message so the
operator can stop safely, while the hook itself exits zero.

The [portability note](../PORTABILITY.md) lists supported and excluded surfaces.
The [Hermes producer documentation](https://github.com/infiquetra/infiquetra-hermes-plugins/tree/main/docs/profile-evolution)
is authoritative for proposal and response semantics.
