# Test security-sensitive client behavior

Use this guide for untrusted input, session expiry, role-sensitive screens, deep links, document access, and client reactions to authorization failures. Local Compose tests prove client behavior. They do not prove backend authorization, TLS, real authentication, or a WebView's execution policy.

## Table of contents

- [Choose the security boundary](#choose-the-security-boundary)
- [Test untrusted text and links](#test-untrusted-text-and-links)
- [Test session expiry and reset flows](#test-session-expiry-and-reset-flows)
- [Test roles and object access](#test-roles-and-object-access)
- [Test input and storage validation](#test-input-and-storage-validation)
- [Verify transport and WebView policy](#verify-transport-and-webview-policy)
- [Test exported Android entry points](#test-exported-android-entry-points)
- [Avoid false security proof](#avoid-false-security-proof)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the security boundary

| Threat or behavior | Useful local test | Required separate evidence |
| --- | --- | --- |
| Untrusted text appears in native `Text` | Assert literal display and safe action handling | Web execution only if content enters a WebView |
| Malicious link invokes a privileged operation | URL parser and navigation-policy tests, then UI rejection | Exported intent and real external-app behavior |
| Expired session exposes protected content | Controlled session event and content removal | Real token expiry and refresh enforcement |
| User changes another user's resource ID | Client denial-state test | Service authorization with two accounts |
| SQL-like input changes query meaning | Real database query test with seeded rows | Backend query tests for server data |
| Cookie-based embedded web flow is vulnerable to CSRF | Client reaction to rejection | Browser or service integration with actual cookie policy |
| Shared file reveals private data | Intent and provider adapter checks | Receiving app, grants, and packaged manifest |
| Security headers are missing | Real HTTP response inspection | Service or WebView integration, not semantics |

Use the Android `src/test` setup and runner in [setup](../references/setup.md). Keep fakes narrow and identify what they remove from the claim.

## Test untrusted text and links

Native Compose text does not run HTML or JavaScript. Do not translate a browser XSS test into an assertion that searches a nonexistent DOM. Test how your application routes untrusted content.

For plain text, the following illustrative test demonstrates literal rendering. It needs Material3, Compose UI testing, JUnit 4, Robolectric, Android resources, and the default host manifest. It is not compiled by this fixture.

```kotlin
import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class UntrustedTextTest {
	@get:Rule val compose = createComposeRule()

	@Test fun displaysMarkupAsLiteralText() {
		val payload = "<script>alert('test')</script>"
		compose.setContent { Text(payload) }
		compose.onNodeWithText(payload).assertTextEquals(payload).assertIsDisplayed()
	}
}
```

This proves native rendering of the supplied string. For a production screen, mount the real component that consumes stored or searched content. Otherwise the test says nothing about an accidental switch to HTML rendering elsewhere.

When content becomes an annotated link, deep link, markdown action, or WebView input, test that boundary separately. Cover forbidden schemes such as `javascript:`, malformed URLs, lookalike hosts, unexpected ports, and valid allowed links. Decide whether a bad link remains inert text or produces an explanation, then assert that behavior.

For stored content, write the payload through the real ingestion path and reopen the screen. Assert that legitimate text remains available and the malicious action does not become a privileged navigation request. A fake request recorder can supplement the visible result.

Do not use a string-prefix host check. Parse the URI and compare the intended scheme and host policy. Tests should include a hostname that merely starts with an allowed hostname and an allowed hostname inside user information or a query string.

## Test session expiry and reset flows

Represent session state explicitly, such as signed out, authenticated, refreshing, or expired. A fake session source can emit each transition while the real UI and state owner remain under test.

For expiry:

1. Mount a protected screen with fresh authenticated session state and synthetic private content.
2. Assert that the intended content is visible.
3. Emit an expired-session event or fail the controlled repository with the app's authentication error.
4. Assert the sign-in destination and expiry explanation.
5. Assert that the previous private content no longer appears.
6. Attempt the protected action again and verify that no authenticated action starts.

For time-based expiry, inject the application's time source. Advancing `mainClock` does not advance a token's server-issued expiry or `Instant.now()`.

For refresh, hold the refresh request pending and verify that the UI does not briefly expose another account's stale content. Test a late response from the previous account after logout or account switch. The state owner must associate results with the correct session identity.

For password reset, test the client states for accepted, expired, invalid, and already-used tokens. A fake "already used" result only proves the client's error state. Use a service integration test to request a disposable reset token, consume it once, and verify that reuse is rejected without changing the password again.

For concurrent sessions, keep two independent client instances and session stores. A server invalidation test needs two real authorized sessions in a test environment. Do not simulate both clients with one mutable singleton and call it multi-device security.

## Test roles and object access

Use a role and resource matrix rather than testing only the administrator happy path:

| Actor | Owned resource | Another user's resource | Administrative action |
| --- | --- | --- | --- |
| Signed out | Sign-in required | Sign-in required | Sign-in required |
| Regular user | Allowed according to policy | Denied without content exposure | Denied |
| Administrator | Explicit policy | Explicit policy | Allowed according to policy |

Replace generic policy cells with your application's actual rules. Do not infer that administrators can read all private content.

For the local client, return a controlled forbidden result for an identified resource and assert a useful denial state. Assert that cached content for a previous resource is not still displayed. Test direct navigation as well as the path through a hidden or disabled button.

For service authorization, use disposable accounts A and B:

1. Create a resource owned by A.
2. Verify A can retrieve it.
3. Request the same resource using B's credentials and the exact identifier.
4. Verify denial and absence of resource bytes or fields.
5. Repeat the relevant update and delete operations.
6. Clean up resources with an authorized test principal.

The denial status can be 403 or 404 according to the service contract. Assert the intended behavior rather than accepting any non-200 response, which could hide a server crash.

Client button visibility is a usability policy, not authorization enforcement. A direct service request bypasses it.

## Test input and storage validation

For length limits, test just below, exactly at, and just above the supported boundary. Define whether the limit counts bytes, Unicode code points, or user-perceived characters. Include non-ASCII input if the policy is user-facing.

For forms, enter the payload through the actual editable semantics, submit it, and assert a visible validation result. Also test the validator directly because callers can bypass UI limits.

For database injection, seed known rows and execute the real DAO or query path with SQL-looking input. Verify that the result is the literal intended match or no match, and that all unrelated rows remain intact. A UI that merely avoids showing "SQL error" is not proof that query construction is safe.

Use parameterized database APIs in production and test actual storage behavior. A repository fake that returns an empty list for every string cannot detect query injection.

For file paths, test traversal-like names, duplicate names, and content URIs through the appropriate adapter. Do not concatenate untrusted display names into private directory paths. See [file operations](file-operations.md) for URI-based reading.

For secrets, keep synthetic credentials in tests. Do not attach access tokens, reset links, private database dumps, or real user documents to reports. Add checks around logging and failure formatting where those paths can expose sensitive data.

## Verify transport and WebView policy

Native bearer-token requests and cookie-authenticated web forms have different security models. Do not add a CSRF field to a Compose form because the browser source guide has one. If the service uses cookie credentials, test its actual CSRF policy at the service or browser layer.

For an embedded WebView or OAuth browser flow, test trusted origins, redirects, external navigation, JavaScript bridge exposure, and cookie behavior in an environment with a real web engine. Robolectric does not establish WebView execution security.

Inspect real HTTP responses for required service headers where browser content is served. Content Security Policy, MIME sniffing policy, and framing policy concern web content. They are not properties of native Compose text. Do not require obsolete `X-XSS-Protection` merely because an older checklist lists it.

For Android transport policy, inspect the packaged network security configuration and test release-like behavior. Confirm that unintended cleartext requests fail and that production trust settings do not include debug-only exceptions. A fake HTTP response bypasses TLS entirely.

Use a dedicated authorized test environment for security integration cases. Keep the cases bounded to the agreed resources and avoid destructive probes against production.

## Test exported Android entry points

For activities, receivers, services, and providers, inspect exported status and required permissions in the merged manifest of the tested variant. Then verify access from outside the application where the claim depends on caller identity.

A local adapter test can pass an untrusted intent into the parser and assert rejection of malformed or unauthorized requests. It cannot prove that Android blocks another app from invoking the component.

For shared documents, verify that the intended recipient can read only the shared content and cannot access another private document by changing its URI. Check grant lifetime and revocation behavior using installed-app integration tests.

## Avoid false security proof

Bad practice is hiding **Delete** for a regular user and declaring the resource protected. The user can bypass the UI and invoke a service or exported component directly.

Correct it by retaining the local visibility test, adding direct-navigation client coverage, and independently testing service or Android boundary enforcement.

Do not catch all exceptions and accept them as attack rejection. A crash, parser bug, or unavailable backend is not an intended denial response.

## Isolate and synchronize

Use fresh session stores, account identities, caches, and fakes per test. Never reuse authenticated singleton state between role cases. Cancel pending work during logout and test stale completion explicitly.

Use controlled results to make refresh and expiry transitions observable. Separate business time, coroutine time, Compose frames, and server time. Restore global credentials or providers in cleanup, including when an assertion fails.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Signed-out screen still shows private text | Cached state and session identity | Clear or partition protected state correctly |
| Role test passes for every role | Fake policy and asserted destination | Use distinct outcomes and negative assertions |
| Expiry never occurs | Actual time source | Inject business time or test server expiry separately |
| SQL payload test always returns empty | Real versus fake database path | Exercise parameterized storage against seeded data |
| Malicious link opens externally | Parsed scheme, host, and dispatch request | Fix policy at the navigation boundary |
| HTTP fake passes but release networking fails | TLS and packaged security configuration | Run the real transport integration test |

## Review checklist

- [ ] Each security claim names the enforcing boundary.
- [ ] Negative cases assert intended denial, not an arbitrary error.
- [ ] Private stale content disappears after expiry or account switch.
- [ ] Authorization tests bypass the client UI independently.
- [ ] WebView, TLS, exported components, and URI grants have real integration evidence.
- [ ] Reports and fixtures contain no real secrets.

## Related guides and sources

- [Authentication](../advanced/authentication.md) covers session fixtures.
- [Authentication flows](../advanced/authentication-flows.md) covers external identity flows.
- [Multi-user tests](../advanced/multi-user.md) covers separate client identities.
- [Android security tips](https://developer.android.com/privacy-and-security/security-tips) describes client security boundaries.
- [Unsafe URI loading](https://developer.android.com/privacy-and-security/risks/unsafe-uri-loading) describes URI validation risks.
- [Network security configuration](https://developer.android.com/privacy-and-security/security-config) describes transport policy.
- [WebView security](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges) describes native bridge risks.
