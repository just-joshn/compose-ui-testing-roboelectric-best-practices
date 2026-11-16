# Annotate test intent without hiding failures

Use this guide to configure Robolectric methods, document temporary exclusions, classify test scope, and preserve useful failure evidence. These annotations apply to the JUnit 4 Android local-test setup used by this skill.

## Contents

- [Choose an annotation](#choose-an-annotation)
- [Configure the local runtime](#configure-the-local-runtime)
- [Ignore only with an accountable reason](#ignore-only-with-an-accountable-reason)
- [Use assumptions for genuine applicability](#use-assumptions-for-genuine-applicability)
- [Do not imitate expected-failure annotations](#do-not-imitate-expected-failure-annotations)
- [Bound slow work at its owner](#bound-slow-work-at-its-owner)
- [Name steps and attach metadata](#name-steps-and-attach-metadata)
- [Troubleshoot annotation behavior](#troubleshoot-annotation-behavior)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose an annotation

| Need | Mechanism | Effect |
| --- | --- | --- |
| Execute a test method | `org.junit.Test` | JUnit discovers the method |
| Run local Android behavior | `@RunWith(RobolectricTestRunner::class)` | Uses Robolectric's runner |
| Pin a runtime SDK or resources | `org.robolectric.annotation.Config` | Changes the simulated environment |
| Make looper mode explicit | `@LooperMode(PAUSED)` | Documents the selected looper contract |
| Temporarily disable a known broken case | `@Ignore("issue and reason")` | Reports a skipped test, not a pass |
| Declare a real precondition | `Assume.assumeTrue` | Unmet assumption aborts the case |
| Classify a suite | JUnit 4 `@Category` plus runner configuration | Enables explicit category filtering |
| Check a promised exception | `Assert.assertThrows` around the exact call | Tests exception behavior, not a known UI regression |

`@Tag`, `@Disabled`, `@BeforeEach`, and Jupiter parameterized-test annotations are not interchangeable with this JUnit 4 runner. Do not add them and assume the configured engine discovers or honors them.

## Configure the local runtime

This complete illustrative test requires the dependencies and default activity host in [configuration](configuration.md):

```kotlin
import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class RuntimeContractTest {
	@get:Rule val rule = createComposeRule()

	@Test fun mountsUnderDeclaredRuntime() {
		rule.setContent { Text("Ready") }
		rule.onNodeWithText("Ready").assertIsDisplayed()
	}
}
```

`@Config` selects the Robolectric runtime. It does not change the compile SDK or turn a local test into a device test. Keep broad defaults in a documented location and use method overrides only for a specific requirement.

A qualifier changes Android resource configuration. Reset any additional global locale or time-zone mutation your own code performs. A configuration annotation does not own every application singleton.

## Ignore only with an accountable reason

Import `org.junit.Ignore` and apply `@Ignore("APP-482: local host cannot yet exercise the required platform adapter")` to the existing behavior method. Keep its real test body and its `@Test` annotation. Record an owner, an issue, and the condition for re-enabling it. Review exclusions regularly.

If the behavior fundamentally requires a device, move its real assertion to the device suite and retain a narrower local contract test. Do not leave an ignored empty test as the only coverage.

Class-level `@Ignore` excludes every method. Use it only when the entire class has the same reason. A single flaky method is not a reason to disable the whole feature suite.

The repository's verification contract rejects skipped expected methods. An ignored test can be visible debt, but it cannot satisfy a required passing behavior check.

## Use assumptions for genuine applicability

Assumptions are for an optional test whose precondition is legitimately unavailable, not for suppressing a failing assertion. This fragment belongs at the start of an explicitly optional integration method:

```kotlin
import org.junit.Assume.assumeTrue

val endpoint = System.getenv("OPTIONAL_TEST_SERVICE_URL")
assumeTrue("Optional service environment is not configured", !endpoint.isNullOrBlank())
```

A required CI lane should validate that variable before executing tests and fail when it is missing. Otherwise the entire lane can report success while all meaningful tests abort.

Do not conditionally skip a required local test because `CI=true`, the machine is slow, or a selector currently fails. Fix its ownership or move the claim to the correct layer.

A new configuration requirement should be an explicit lane input. Avoid helper functions that silently apply assumptions to every class.

## Do not imitate expected-failure annotations

JUnit 4 has no direct equivalent of Playwright's `test.fail()` that fails on an unexpected pass. `@Test(expected = AssertionError::class)` is not a safe substitute for a known broken UI test. Any unrelated assertion can satisfy it.

Anti-pattern. Annotating a broken checkout journey with `@Test(expected = AssertionError::class)` makes any failing assertion in its body satisfy the expected exception. An unrelated missing-node assertion can then hide the original checkout regression. Keep the normal `@Test` and the required final confirmation assertion instead.

Keep the real behavior assertion failing in a required regression branch, or use an accountable temporary exclusion when policy explicitly permits it. Use separate negative-control evidence to demonstrate that a test catches a mutation.

For a function whose public contract is an exception, use `assertThrows` around that exact function call. For UI error behavior, provide a controlled failure and assert the visible error state. A caught internal exception does not establish the user's recovery path.

## Bound slow work at its owner

There is no standard JUnit 4 `@Slow` that triples every Compose timeout. Categories classify tests but do not change their timing.

Do not add `@Test(timeout = ...)` mechanically to Compose tests. JUnit's method-timeout mechanism can execute the method on a different thread from lifecycle methods. That can conflict with thread-affine framework behavior. A `Timeout` rule has its own execution-thread semantics and also needs deliberate compatibility checks.

For external progress, use a local bounded `waitUntil` and identify its producer. For Compose animation, use the main test clock. For a hung process, use the test infrastructure's worker or job bound and preserve logs.

A slow test deserves diagnosis of the expensive operation. Reclassifying it or enlarging a timeout does not fix a leaked thread, incomplete fake, or recomposition loop.

## Name steps and attach metadata

JUnit 4 does not automatically create Playwright trace steps. Use descriptive method names and focused robot methods so stack traces identify the failing operation. Keep essential inputs and result assertions in the test.

For example, the readable sequence is `enterMessage("Hello")`, `send()`, `assertSending()`, explicit fake completion, then `assertReceipt("Delivered Hello")`. Do not collapse it into `happyPath()`.

Custom annotations can carry an issue ID or owner for repository tooling. A declaration alone does not make JUnit report or filter that metadata:

```kotlin
@Target(AnnotationTarget.CLASS, AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class TestIssue(val value: String)
```

Use this only when an existing reporter or static check reads it. Otherwise put the issue next to the temporary exclusion and keep the test name about behavior.

Use categories for runner-supported classification. Do not confuse them with `Modifier.testTag`, which labels UI nodes and cannot select JUnit tests.

## Troubleshoot annotation behavior

| Symptom | Observation | Correction |
| --- | --- | --- |
| Annotation has no effect | Import package and test engine | Use JUnit 4 annotations with the Robolectric runner |
| CI green with no behavior exercised | Skips, assumptions, XML counts | Fail required lanes on missing or skipped cases |
| Test runs at unexpected SDK | Class, method, and project configuration | Remove conflicting defaults and document the narrow override |
| Known bug appears to pass | Expected-exception wrapper | Restore the actual result assertion |
| Timeout changes threading | JUnit timeout mechanism | Bound the real work and verify runner compatibility |
| Custom metadata absent from report | Reporter support | Add explicit tooling or remove unused metadata |

## Review checklist

- Every annotation comes from the intended JUnit or Robolectric package.
- Exclusions include a concrete reason and re-enable condition.
- Required lanes reject missing preconditions rather than silently skipping.
- Exception tests target public exception behavior.
- Timing changes identify the actual work owner.
- Test names and robot methods preserve the failing step's meaning.

## Related guides and sources

- [Test filtering](test-filtering.md) covers categories and method filters.
- [Assertions and waiting](assertions-waiting.md) covers synchronization instead of sleeps.
- [JUnit 4 Ignore](https://junit.org/junit4/javadoc/4.13.2/org/junit/Ignore.html) and [Assume](https://junit.org/junit4/javadoc/4.13.2/org/junit/Assume.html) define exclusion behavior.
- [JUnit 4 Test](https://junit.org/junit4/javadoc/4.13.2/org/junit/Test.html) documents expected exceptions and timeout threading.
- [Robolectric configuration](https://robolectric.org/configuring/) describes environment annotations.
