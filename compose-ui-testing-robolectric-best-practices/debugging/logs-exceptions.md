# Capture Android logs and preserve exceptions

Use this guide when a local Compose test fails without enough context, when a caught failure must be reported, or when unexpected application errors must fail a test. It covers Robolectric's Android log capture and JUnit evidence. It does not replace device logcat or provide a browser-style uncaught-error listener.

## Table of contents

- [Choose the evidence channel](#choose-the-evidence-channel)
- [Capture Android logs with their causes](#capture-android-logs-with-their-causes)
- [Fail on unexpected application errors](#fail-on-unexpected-application-errors)
- [Preserve uncaught exceptions](#preserve-uncaught-exceptions)
- [Handle expected failures explicitly](#handle-expected-failures-explicitly)
- [Retain logs in JUnit reports](#retain-logs-in-junit-reports)
- [Monitor warnings without blanket suppression](#monitor-warnings-without-blanket-suppression)
- [Troubleshoot missing evidence](#troubleshoot-missing-evidence)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the evidence channel

| Evidence | Capture | Limit |
| --- | --- | --- |
| `android.util.Log` messages | `ShadowLog.getLogs()` or `getLogsForTag()` | Not every logger writes to Android Log |
| Throwable passed to `Log.e` | `LogItem.throwable` and its stack | A log entry is not automatically a test failure |
| Test exception or assertion | JUnit failure with complete cause chain | Do not catch and discard it |
| Coroutine failure | Structured job or test scope that owns it | Detached work can outlive the test |
| Java standard output | Gradle test logging and JUnit `system-out` | Output must not expose secrets |
| Missing or ambiguous UI node | Semantics tree and selector cardinality | Logs alone do not describe the tree |
| Device crash or system service failure | Device logcat and instrumentation result | Local ShadowLog does not establish device behavior |

Capture before the action that can fail. An after-the-fact logger cannot reconstruct omitted payloads, timing, or a throwable that was reduced to its message.

Use a small application-tag policy rather than failing every framework warning. Robolectric and AndroidX can emit diagnostics outside your feature's contract. Review those diagnostics, but do not suppress all errors to make the suite pass.

## Capture Android logs with their causes

The data shape is a log item with level, tag, message, and optional throwable. Robolectric 4.18 exposes these fields on `ShadowLog.LogItem`. This illustrative helper uses `org.robolectric:robolectric:4.18` and Android's `Log` through the Robolectric runner.

```kotlin
import org.robolectric.shadows.ShadowLog

fun printAndroidLogs() {
	for (item in ShadowLog.getLogs()) {
		println("level=${item.type} tag=${item.tag} message=${item.msg}")
		item.throwable?.printStackTrace(System.out)
	}
}
```

Do not assume `msg` includes a stack trace. Preserve `throwable` separately. Do not print raw tokens, passwords, entire API responses, or personal data. A useful message identifies the operation and a sanitized request identifier.

For focused diagnosis, inspect one tag:

```kotlin
import android.util.Log
import org.junit.Assert.assertTrue
import org.robolectric.shadows.ShadowLog

val applicationErrors = ShadowLog.getLogsForTag("MessageRepository")
	.filter { it.type >= Log.ERROR }
assertTrue(applicationErrors.joinToString("\n"), applicationErrors.isEmpty())
```

This fragment checks Android Log only. If the application uses a separate logging interface, inject a recording implementation or configure that logger's test appender. Do not claim ShadowLog captures arbitrary standard error or coroutine exceptions.

## Fail on unexpected application errors

A JUnit rule can retain logs on failure and enforce a narrow policy on success. The following complete illustrative rule wraps test evaluation, not activity launch by itself. It uses JUnit 4 and Robolectric 4.18. Its policy is specific to the sample tag and message.

```kotlin
import android.util.Log
import org.junit.rules.TestRule
import org.junit.runner.Description
import org.junit.runners.model.Statement
import org.robolectric.shadows.ShadowLog

class ApplicationLogRule : TestRule {
	override fun apply(base: Statement, description: Description): Statement =
		object : Statement() {
			override fun evaluate() {
				var primary: Throwable? = null
				try {
					base.evaluate()
				} catch (failure: Throwable) {
					primary = failure
					throw failure
				} finally {
					val errors = ShadowLog.getLogsForTag("MessageRepository")
						.filter { it.type >= Log.ERROR }
					for (item in errors) {
						println("${description.methodName} ${item.tag} ${item.msg}")
						item.throwable?.printStackTrace(System.out)
					}
					val unexpected = errors.filterNot {
						it.msg == "Send rejected by test service" &&
							it.throwable is ExpectedSendFailure
					}
					if (unexpected.isNotEmpty()) {
						val logFailure = AssertionError(unexpected.joinToString("\n"))
						val original = primary
						if (original == null) throw logFailure
						original.addSuppressed(logFailure)
					}
				}
			}
		}
}

class ExpectedSendFailure : RuntimeException("Controlled send rejection")
```

This is an example policy, not a reason to add `ExpectedSendFailure` to production. Replace the exact allowed entry with your application's defined failure type, owner, and scenario. Avoid a global allow pattern such as `.*failed.*`.

Order the log rule outside the Compose rule if it must inspect activity setup and disposal logs as well as test-body logs. Use `RuleChain.outerRule(logs).around(compose)` in the test class. Keep any unrelated dependency-installation rule ordered before the activity starts.

The rule does not clear the log buffer before running. Clearing after activity launch would lose startup diagnostics. Robolectric resets its log shadow between tests. If a helper calls `ShadowLog.clear()` within a test, capture the needed entries first. In 4.18, `clear()` also resets log-level configuration and related shadow state.

Do not turn off log capture in one test without restoring it. `getLogs` throws when capture is disabled. Avoid changing `ShadowLog.stream` unless you own restoring the previous stream. Never close `System.out` or `System.err`.

## Preserve uncaught exceptions

A thrown assertion or exception must reach JUnit. An empty error log does not prove the absence of a failure. Code can throw without logging, and code can log an expected failure without throwing.

Do not install a global `Thread.setDefaultUncaughtExceptionHandler` that prints and returns. It can hide failures, affects unrelated tests, and does not join the thread that failed.

Prefer structured ownership:

- Await or join test-owned work through the relevant test API.
- Use a scope whose failures are reported to the test that owns it.
- Cancel and join owned work before teardown completes.
- Keep cancellation distinct from business failure.
- Let Compose's test environment report its own composition failures.

A `CoroutineExceptionHandler` is not a substitute for an application error state or structured cancellation. A Compose composable does not have React's error-boundary mechanism. Do not intentionally crash a composable and assume a generic fallback will catch it.

Use [error testing](error-testing.md) to map defined repository failures into a recoverable state. Use the original uncaught exception to diagnose programmer defects.

## Handle expected failures explicitly

Faulty illustrative pattern:

```kotlin
try {
	compose.onNodeWithText("Saved").assertIsDisplayed()
} catch (error: Throwable) {
	println(error.message)
}
```

The test passes after an assertion failure. Correct behavior tests do not catch their own failed assertions:

```kotlin
compose.onNodeWithText("Save").performClick()
compose.onNodeWithText("Saved").assertIsDisplayed()
```

Both fragments require `assertIsDisplayed`, `onNodeWithText`, and `performClick` from `androidx.compose.ui.test`, plus an already mounted screen and configured rule. The corrected example assumes Save synchronously produces `Saved`; release a controlled dependency first for asynchronous work.

A diagnostic test that verifies a framework failure can use `assertThrows(AssertionError::class.java)`. Keep that deliberate diagnostic separate from production behavior tests. The canonical `selectorFailureIncludesTreeDiagnostics` test does this to preserve a known missing-node message, then verifies the corrected finder.

## Retain logs in JUnit reports

Enable standard streams for the local test task when investigating. This illustrative Android-module Gradle fragment assumes the existing `android` configuration:

```kotlin
android {
	testOptions {
		unitTests.all {
			it.testLogging.showStandardStreams = true
		}
	}
}
```

Run the narrow test and retain both the process output and JUnit XML. Replace the module, variant, and test filter for another project.

```bash
./gradlew :fixture:testDebugUnitTest \
  --tests 'fixture.FixtureUiTest.selectorFailureIncludesTreeDiagnostics' \
  --console=plain --no-daemon --rerun-tasks
```

The recorded fixture JUnit `system-out` contains this real excerpt:

```text
selectorFailureIncludesTreeDiagnostics original assertion
Failed: assertExists.
Reason: Expected exactly '1' node but could not find any node that satisfies: (TestTag = 'summary-child')
However, the unmerged tree contains '1' node that matches. Are you missing `useUnmergedNode = true` in your finder?
```

The public Kotlin finder parameter is `useUnmergedTree`, despite the 1.12.1 message's `useUnmergedNode` hint. The test catches this expected diagnostic, prints both trees, and verifies the unmerged child. This log is not an unexpected production crash.

Do not equate a `BUILD SUCCESSFUL` line with executed coverage. Inspect the intended JUnit test name, zero failures and errors, and no skipped cases. Preserve failed results before rerunning because Gradle can replace report directories.

## Monitor warnings without blanket suppression

Treat warnings as evidence with a scoped policy:

| Warning | Action |
| --- | --- |
| Deprecated test factory import | Inspect resolved version and migrate deliberately |
| Application invariant warning | Add a feature-specific assertion or fix the invariant |
| Known framework warning | Record exact tag, message, version, and reason if allowed |
| Missing resource or host diagnostic | Fix setup before investigating selectors |
| Network or dependency download warning | Separate infrastructure availability from UI behavior |

Do not assert an empty warning list across every dependency version. A useful warning test checks a known application contract. Keep upgrade diagnostics in build checks rather than disguising them as UI behavior.

## Troubleshoot missing evidence

| Symptom | Observe | Fix |
| --- | --- | --- |
| No Android log entries | Logger destination and capture-enabled setting | Configure the correct logger or restore capture |
| Log exists but test passes | Was any assertion made about the entry? | Add a narrow policy if it represents a defect |
| Original failure disappears | Did teardown throw another failure? | Preserve primary and attach diagnostics as suppressed |
| Failure appears after test finishes | Detached job or rogue thread | Give work a test-owned lifecycle |
| Stack trace missing | Was only `Throwable.message` stored? | Retain the throwable and its causes |
| Logs from startup disappear | Was the buffer cleared after launch? | Capture before setup or order the rule outside launch |

## Review checklist

- Does capture begin before the failing action?
- Are level, tag, message, and throwable retained?
- Is the unexpected-error policy scoped to application behavior?
- Are allowed failures exact and justified?
- Can assertion and coroutine failures still reach JUnit?
- Are logs sanitized and archived with the named test result?
- Does cleanup preserve the original failure?

## Related guides and sources

- [Debugging](debugging.md) classifies the first failed boundary.
- [Error testing](error-testing.md) tests recoverable outcomes.
- [Flaky tests](flaky-tests.md) diagnoses races and leaked jobs.
- [Robolectric 4.18 ShadowLog API](https://robolectric.org/javadoc/4.18/org/robolectric/shadows/ShadowLog.html) documents capture methods.
- [Robolectric 4.18 ShadowLog source](https://github.com/robolectric/robolectric/blob/robolectric-4.18/shadows/framework/src/main/java/org/robolectric/shadows/ShadowLog.java) defines log item fields and reset behavior.
- [Android Log reference](https://developer.android.com/reference/android/util/Log) documents log levels and throwable overloads.
