# Test authentication and signed-in state

## Table of contents

- [Choose the authentication boundary](#choose-the-authentication-boundary)
- [Seed sessions without bypassing the behavior](#seed-sessions-without-bypassing-the-behavior)
- [Exercise the login screen](#exercise-the-login-screen)
- [Cover roles and anonymous routes](#cover-roles-and-anonymous-routes)
- [Handle OAuth, SSO, and MFA](#handle-oauth-sso-and-mfa)
- [Test refresh and persisted sessions](#test-refresh-and-persisted-sessions)
- [Keep sessions isolated](#keep-sessions-isolated)
- [Avoid false authentication proof](#avoid-false-authentication-proof)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the authentication boundary

Use this guide for login, authenticated screens, protected navigation, roles, and session refresh in Android local tests. Use [authentication flows](authentication-flows.md) for verification, password reset, expiry warnings, and logout.

A Robolectric Compose test runs your app's client behavior. It does not create a trustworthy identity provider or prove that a backend rejects unauthorized requests.

| Question | Test setup | What it proves |
| --- | --- | --- |
| Does a signed-in user see their account? | Fresh session fake seeded before content | Session-to-UI mapping |
| Does entering credentials produce the home screen? | Real login screen and controlled auth repository | Client action-to-result path |
| Does a viewer lack edit controls? | Viewer capabilities in a fresh fake | Client permission presentation |
| Does the server reject a viewer's write? | Authenticated service integration test | Server authorization |
| Does token refresh update requests? | Real repository and controlled transport | Refresh and request construction |
| Does a provider return to the app? | Device test with provider test tenant | Browser, SDK, and redirect integration |
| Does login survive reconstruction? | Real store and newly constructed session owner | The store's restoration contract |

Use the Android `src/test` setup in [setup](../references/setup.md). It requires Android resources, `testImplementation`, a Robolectric runner, and a declared activity host. The canonical fixture uses Compose UI 1.12.1's v2 rule factory. It does not validate every auth SDK.

## Seed sessions without bypassing the behavior

For a profile-editing test, start signed in. Do not repeat credential entry when login is not the claim. Seed the boundary that normally supplies the active session, not the screen's final "Profile saved" state.

Keep the data shape explicit. A session contains identity and capabilities. A failed login is not a partially populated session. A challenge is not a signed-in user.

Illustrative application contract, not a fixture-compiled example. It uses Kotlin and `kotlinx-coroutines-core`.

```kotlin
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class Session(
	val userId: String,
	val displayName: String,
	val canManageUsers: Boolean,
)

sealed interface AuthState {
	data object Anonymous : AuthState
	data class SignedIn(val session: Session) : AuthState
	data class Challenge(val challengeId: String) : AuthState
}

interface SessionSource {
	val state: StateFlow<AuthState>
}

class FakeSessionSource(initial: AuthState) : SessionSource {
	override val state = MutableStateFlow(initial)
}
```

Create `FakeSessionSource(AuthState.SignedIn(...))` inside each test. Inject it before the screen or activity reads its dependencies. Do not replace a singleton after the ViewModel already captured the real repository.

Reuse immutable factory functions for sessions. Do not reuse a mutable `StateFlow`, preferences file, token cache, or fake instance between tests. Browser storage-state files have no direct Compose equivalent.

Global setup may validate tool installation. It must not create one mutable signed-in object for the local suite. Backend integration jobs can provision accounts separately, with names unique to the run, shard, worker, and test.

## Exercise the login screen

Keep one focused set of tests that enters credentials through semantics. Assert loading, success, rejected credentials, required fields, and password-reset navigation where those behaviors exist.

Illustrative test-body fragment. It assumes a project-defined `ControlledAuthRepository`, a `LoginRoute(repository)` composable that owns login orchestration, and a v2 `rule`. The repository holds a pending login until `succeed` or `reject` is called. Required testing APIs come from `androidx.compose.ui.test`.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

val auth = ControlledAuthRepository()
rule.setContent { LoginRoute(auth) }
rule.onNodeWithText("Sign in").assertIsNotEnabled()
rule.onNodeWithText("Email").performTextInput("alex@example.test")
rule.onNodeWithText("Password").performTextInput("test-only-password")
rule.onNodeWithText("Sign in").performClick()
rule.onNodeWithText("Signing in").assertIsDisplayed()
rule.runOnIdle {
	auth.succeed(Session("alex", "Alex", canManageUsers = false))
}
rule.onNodeWithText("Welcome, Alex").assertIsDisplayed()
rule.onNodeWithText("Signing in").assertDoesNotExist()
```

The final home assertion matters. Checking only `auth.submittedEmail` passes when navigation is broken. A request assertion can supplement the UI result when credential forwarding is part of the contract.

For wrong credentials, start a fresh test, submit through the screen, release `RejectedCredentials`, and assert a useful error with a usable retry action. Do not throw an uncaught exception from a fake if the production repository returns a typed failure.

Use a small login robot only when selectors repeat across tests. Keep explicit credentials and outcome assertions visible at the call site. Avoid a helper that silently logs in, seeds data, advances clocks, and navigates.

## Cover roles and anonymous routes

Choose roles from the application's actual permission model. Test a matrix rather than an administrator with every permission.

| Identity | Observable example | Separate security check |
| --- | --- | --- |
| Anonymous | Opening a protected destination shows sign-in | Server rejects missing credentials |
| Viewer | Content visible, edit unavailable | Server rejects write despite forged UI request |
| Editor | Edit available, user management absent | Server enforces resource ownership |
| Administrator | User management reachable | Server verifies administrative privilege |

For anonymous tests, explicitly construct an anonymous session source. Do not rely on whichever preference value a previous method left behind.

Drive a protected destination through the actual navigation entry point. Assert the sign-in screen and the intended return destination after successful sign-in. A test that mounts the sign-in screen directly cannot prove route protection.

When labels repeat, scope controls by meaningful identity. For example, select the edit control inside the current account group, not the first "Edit" in the tree.

A local "Access denied" screen proves client handling of denied access. It does not prove that privileged data never reached the device. Verify that boundary in repository and service tests.

## Handle OAuth, SSO, and MFA

Replace the provider launcher or SDK adapter, not Compose. Install the adapter before clicking **Continue with provider**. Return a typed success, cancellation, or failure through the same app-owned callback that production uses.

Use [third-party services](third-party.md) for the full provider workflow. Keep these cases distinct:

1. Launch accepted, provider result pending, cancellation restores sign-in.
2. Provider code returned, token exchange pending, home screen still absent.
3. Exchange accepted, signed-in UI appears.
4. Exchange rejected, session remains anonymous with a retry action.
5. Invalid or mismatched callback state is rejected by the app-owned callback handler.

Do not simulate a successful OAuth exchange by accepting any arbitrary code in production. Do not add test-only authentication bypasses to the release app. Test state correlation and PKCE in the component that implements them, using the real implementation and controlled transport.

For enterprise SAML, the app commonly receives a result from a browser or backend rather than parsing a SAML assertion itself. Fake that app boundary for UI tests. Verify assertion validation at the backend or identity-provider integration layer.

For MFA, use a repository result such as `Challenge(challengeId)` after the first factor. Enter the code in the UI, then release accepted, invalid, expired, or rate-limited results. Assert that home remains unavailable before the second factor succeeds.

TOTP algorithm tests need an explicit time source and fixed test secret. SMS delivery needs an integration environment. A fake code such as `123456` proves neither TOTP validation nor phone ownership. Do not disable MFA in every layer and then claim MFA coverage.

## Test refresh and persisted sessions

Use fixed or mutable application time, not a long-running test that waits for a real token to expire. Cover valid access token, expired access token with valid refresh token, rejected refresh, and user logout while refresh is pending.

Keep refresh protocol tests below the UI. With two concurrent protected requests, control the transport so both encounter expiry. Verify the intended refresh coordination and replay behavior there. In Compose, assert the observable consequence, such as remaining signed in after success or returning to sign-in after rejection.

A late refresh response must not resurrect a logged-out session. Hold refresh pending, perform logout, complete refresh, and assert that protected content stays absent.

For persistence, use the actual store in a temporary, test-owned location. Write through the normal session owner, reconstruct that owner, and verify restoration. Reusing the same fake in memory is not persistence proof. Activity recreation and process death require their own host or device scenarios.

Do not log tokens, passwords, provider authorization URLs, or complete redirect payloads in diagnostics. Keep integration credentials in CI secrets. Never commit captured authenticated storage.

## Keep sessions isolated

- Construct fresh session state, pending operations, and repositories for each test.
- Install DI replacements before activity launch when the activity owns content.
- Use one content owner. Do not call `setContent` over an activity that already supplies it.
- Cancel pending login and refresh jobs during teardown.
- Restore global dispatchers or service registrations if the project requires them.
- Use explicit store names and delete only test-owned data after assertions.

Compose assertions synchronize known UI work. A fake awaiting a result remains pending after `waitForIdle()`. Release it explicitly. For independent executors, use a bounded condition or an appropriate idling resource. Do not insert sleeps after **Sign in**.

## Avoid false authentication proof

Bad practice is to inject `SignedIn` and describe the test as "credentials are accepted". That skips validation, repository execution, and navigation.

Correct it by choosing the claim. Seed `SignedIn` for account-screen tests. For login, submit credentials through the real screen and release the auth boundary result.

Another anti-pattern shares one mutable auth store across workers. Logout in one test invalidates another test's assumptions. Replace it with per-test stores locally and independently provisioned accounts in service integration jobs.

## Troubleshoot

| Symptom | Observe first | Correction |
| --- | --- | --- |
| Login still launches the real provider | Dependency captured before replacement | Install adapter before activity or ViewModel creation |
| Loading never ends | Pending fake and owner of coroutine | Complete fake or advance the actual scheduler |
| Test passes only alone | Preferences, singleton cache, reused deferred | Fresh state and explicit cleanup |
| Viewer sees admin controls | Capability data and selected account | Assert role-specific UI with separate identities |
| Callback accepted but home absent | Exchange result and session emission | Assert each boundary without seeding final UI |
| Tokens appear in test reports | Logging and captured request bodies | Redact before publishing artifacts |

## Review checklist

- Is login exercised only where login is the behavior under test?
- Does each result assertion follow a real user action?
- Are anonymous, rejected, challenged, and signed-in states distinct?
- Are provider, transport, persistence, and backend claims assigned to their real test layers?
- Can one test log out without affecting another?
- Does a late result fail to restore a cleared session?

## Related guides and sources

- [Authentication flows](authentication-flows.md), [third-party services](third-party.md), and [network fakes](network-fakes.md).
- [Fixtures and hooks](../core/fixtures-hooks.md) and [screen robots](../core/screen-robots.md).
- [Canonical examples](../examples/FixtureUiTest.kt) demonstrate pending work and visible results, not authentication implementation.
- [Android authentication guidance](https://developer.android.com/identity) describes platform identity options.
- [Compose testing](https://developer.android.com/develop/ui/compose/testing) and [synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) define local interaction and waiting contracts.
- [Robolectric best practices](https://robolectric.org/best-practices/) and [versioned evidence](../references/evidence.md) bound the local environment.
