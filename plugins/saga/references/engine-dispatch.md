# External engine dispatch

Saga uses a one-shot request/result harness, not a plugin-owned lifecycle controller.

1. The operator chooses an exact route and bounded context.
2. Saga creates `saga.harness.request.v1`.
3. `external_action_adapters.py` resolves the canonical registry row and invokes the CLI delegate
   or generic HTTP bridge.
4. The adapter validates route identity, invocation digest, bridge receipt, and output attestation.
5. Saga returns `saga.harness.result.v1` as advisory evidence.

There is no offer preference, onboarding overlay, promotion state, retry controller, circuit
breaker, status projection, or action store. A failed call returns one terminal unavailable result;
the operator or calling workflow decides what happens next.

Direct calls have an empty `write_set`. An approved Verified Workflow may receive a patch produced
in a disposable remote-stripped checkout. The patch remains inert until its Git operator imports
the matching request/result pair.
