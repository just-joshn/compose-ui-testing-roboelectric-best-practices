# Isolate mutable state and external work

## Use a fresh boundary fake

Fake the boundary that makes a test nondeterministic, such as a sender or repository. Keep Compose runtime, semantics, and interaction APIs real. Do not mock the Compose rule or an Android `Context` that framework code will call.

A fake that suspends until completion lets the test verify loading and success independently. Give each test its own deferred, state, request data, and instance. The [canonical examples](../examples/) use this pattern. Reusing a completed deferred makes a later test skip the pending state.

Prefer the smallest boundary that exercises the promised behavior. If a test directly supplies a final UI state, describe it as a rendering test. Do not claim it proves the asynchronous orchestration.

Check what the fake removes from the claim. A fake sender proves how the UI handles that sender's contract. It does not prove the real transport, serialization, authentication, or server behavior.

## Keep ownership local

- Create mutable Compose state and fakes per test.
- Let the rule create and dispose the test composition. Call `setContent` once.
- Use composition-owned scopes for work that belongs to the composition.
- Cancel test-owned scopes and pending work in cleanup.
- Unregister idling resources and restore any global state you changed.
- Shut down executors and join owned threads. Robolectric does not clean up rogue threads between tests.
- Do not depend on method order, singleton caches, a shared fake, or a previous test's preferences.

If you must replace a dispatcher or global service, install it before the relevant work starts and restore it after every test, including failures. Do not add a global replacement when a constructor parameter or local fake already isolates the boundary.

## Verify independence

Run the class, run the suspect method alone, and rerun the class. A passing sequence is evidence for those runs, not proof against every interleaving. If a test passes only alone, inspect shared objects, completed fakes, persisted state, threads, clock settings, and global replacements before increasing timeouts.

A test that checks only a newly constructed fake's field proves little about isolation. Prefer a behavioral test that starts pending work, completes it, and verifies a fresh test still observes its own initial state. Exercise disposal or cancellation when that is part of the ownership contract.

## Evidence

The [Compose common patterns guide](https://developer.android.com/develop/ui/compose/testing/common-patterns) describes testing small composables in isolation. [Robolectric best practices](https://robolectric.org/best-practices/) warns about rogue threads and mocking Android objects. The [evidence reference](evidence.md) states which cleanup and independence cases this fixture actually executes.
