# Changelog

## 0.1.3 - 2026-08-10

- Require the producer's profile-change classifier contract as an explicit repository opt-in.
- Ignore generic team repositories without the contract while denying classifier failures after opt-in.

## 0.1.2 - 2026-08-09

- Project standard chat-completion responses onto the producer-declared public fields.
- Remove provider-specific response metadata instead of rejecting otherwise compatible dialogue.

## 0.1.1 - 2026-08-09

- Allow the producer's bounded 30-second network request to finish before the Codex adapter exits.
- Document how to distinguish an adapter timeout from unavailable model-provider service.

## 0.1.0 - 2026-08-02

- Add the Codex-native skill and trusted advisory `PreToolUse` hook.
- Consume pinned Team Mimir classifier and Hermes command conformance artifacts.
- Route bounded dialogue requests to canonical `hermes profile-request` over standard input.
- Reject malformed, oversized, secret-bearing, version-skewed, or unexpected producer data without
  echoing request content.
