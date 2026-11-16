# Test background work and offline queues

## Table of contents

- [Choose the background-work claim](#choose-the-background-work-claim)
- [Test queued work through the UI](#test-queued-work-through-the-ui)
- [Test worker logic separately](#test-worker-logic-separately)
- [Test enqueueing and constraints](#test-enqueueing-and-constraints)
- [Test cached data and offline recovery](#test-cached-data-and-offline-recovery)
- [Test retries, updates, and cancellation](#test-retries-updates-and-cancellation)
- [Test push and notification entry points](#test-push-and-notification-entry-points)
- [Isolate work and control time](#isolate-work-and-control-time)
- [Avoid false-green background tests](#avoid-false-green-background-tests)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the background-work claim

Use this guide for WorkManager-backed synchronization, offline submission queues, cached content, and background-result UI. Android WorkManager is not a service worker. It does not install a web cache, intercept browser requests, or execute web push scripts.

Split the application into the screen, durable repository, scheduler adapter, worker, and external service. Test the real boundary named by the claim rather than loading all of them into every UI test.

| Claim | Test layer | Control |
| --- | --- | --- |
| Offline send shows queued status | Compose with a queue boundary fake | Hold completion and publish queue state |
| Worker maps a successful upload to success | Worker unit test | Controlled uploader and worker test builder |
| Work request has network constraints | WorkManager adapter test | Real request configuration and test initialization |
| Constraints release pending work | WorkManager integration test | `TestDriver` |
| Queue survives reopening the database | Repository test with a real test database | Close and reopen storage |
| Device eventually schedules work under power limits | Device integration test | Real Android scheduling conditions |
| Push delivery reaches the application | Provider integration test | Test backend and device |

Local tests can prove enqueueing and application behavior. They cannot promise wall-clock execution deadlines under Doze, app standby, background restrictions, or vendor policy.

## Test queued work through the UI

Keep the queue state observable through the application's repository contract. A successful enqueue is not a successful upload. The screen must distinguish queued, in progress, delivered, and failed states when the product exposes those states.

Illustrative test fragment. It requires the standard Robolectric Compose host, a project-defined `ControlledOutbox`, and an `OutboxScreen` that observes that outbox. The fake holds the upload pending and exposes main-thread-safe state updates. These types are an example contract, not Android APIs.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

val outbox = ControlledOutbox(online = false)
rule.setContent { OutboxScreen(outbox = outbox) }
rule.onNodeWithText("Message").performTextInput("Meet at noon")
rule.onNodeWithText("Send").performClick()
rule.onNodeWithText("Queued for sync").assertIsDisplayed()
rule.onNodeWithText("Message delivered").assertDoesNotExist()
rule.runOnIdle {
	outbox.setOnline(true)
	outbox.completeUpload(receipt = "Message delivered")
}
rule.onNodeWithText("Message delivered").assertIsDisplayed()
rule.onNodeWithText("Queued for sync").assertDoesNotExist()
```

The test drives the queue-to-result path through a controlled boundary. It does not prove that the real WorkManager request was created or that an HTTP upload occurred. Add adapter and transport tests for those claims.

Also test the queue's empty state, retryable failure, and permanent rejection. Assert that a retry preserves the user's message rather than asking the user to type it again.

## Test worker logic separately

Use `androidx.work:work-testing` aligned with the project's WorkManager version. Use the test builder appropriate to the worker type. `CoroutineWorker` is a `ListenableWorker`; a plain `Worker` has a different execution API.

Illustrative standalone worker test. It requires WorkManager runtime, `work-testing`, AndroidX Test core, Robolectric, JUnit 4, and `kotlinx-coroutines-test`. This tests a worker result and output contract, not scheduling or Compose UI. The snippet is not compiled by the canonical fixture.

```kotlin
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import androidx.work.testing.TestListenableWorkerBuilder
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

class EchoWorker(context: Context, params: WorkerParameters) :
	CoroutineWorker(context, params) {
	override suspend fun doWork(): Result {
		val message = inputData.getString("message") ?: return Result.failure()
		return Result.success(workDataOf("receipt" to "Saved $message"))
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class EchoWorkerTest {
	@Test fun producesReceipt() = runTest {
		val context = ApplicationProvider.getApplicationContext<Context>()
		val worker = TestListenableWorkerBuilder<EchoWorker>(context)
			.setInputData(workDataOf("message" to "Draft"))
			.build()
		val result = worker.doWork()
		assertEquals(
			androidx.work.ListenableWorker.Result.success(
				workDataOf("receipt" to "Saved Draft"),
			),
			result,
		)
	}
}
```

No Compose rule is needed for a worker result. For a production worker with injected dependencies, use the project's `WorkerFactory` or explicit test construction rather than introducing a global singleton uploader.

Test missing input, successful upload, retryable failure, permanent failure, and cancellation according to the worker's actual contract. Do not convert every exception to `Result.retry()`. Invalid credentials or rejected data may require user action instead of an infinite retry.

## Test enqueueing and constraints

Initialize WorkManager's test environment before the first production access. If the test application's startup initializer creates WorkManager first, use the test configuration supported by the project to prevent competing initialization. A Compose host can start the application before a test method runs, so method-local initialization can be too late.

Use `WorkManagerTestInitHelper` with an explicit test configuration. Inspect enqueue completion before inspecting `WorkInfo`. For a constrained request, get the test driver from the initialized context and call `setAllConstraintsMet(request.id)` only for the work under test.

Illustrative integration-test fragment. It assumes `context`, a test-initialized WorkManager, and the `EchoWorker` above. It also assumes a deterministic executor configuration for this integration test. Imports belong at the top of the test file.

```kotlin
import androidx.work.Constraints
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.testing.WorkManagerTestInitHelper
import org.junit.Assert.assertEquals

val request = OneTimeWorkRequestBuilder<EchoWorker>()
	.setConstraints(
		Constraints.Builder()
			.setRequiredNetworkType(NetworkType.CONNECTED)
			.build(),
	)
	.build()
val manager = WorkManager.getInstance(context)
manager.enqueue(request).result.get()
val driver = checkNotNull(WorkManagerTestInitHelper.getTestDriver(context))
driver.setAllConstraintsMet(request.id)
val info = checkNotNull(manager.getWorkInfoById(request.id).get())
assertEquals(WorkInfo.State.FAILED, info.state)
```

This case deliberately supplies no required message, so the example worker fails. Add valid input for a success case. Blocking future access belongs only in a worker integration test whose executor can make progress. Never block the UI thread or a Compose callback waiting for background work.

Use the test driver's delay controls for initial and periodic delays. Do not advance Compose time and expect a WorkManager constraint or backoff timer to change.

## Test cached data and offline recovery

Treat connectivity as an input and cache policy as repository behavior. A simulated offline flag does not prove persistent cache contents.

Cover these cases with controlled repository fixtures:

| Initial storage | Refresh result | Expected screen |
| --- | --- | --- |
| Cached records | Pending | Cached content with the designed refresh indication |
| Cached records | Network unavailable | Cached content with offline or stale status |
| Empty storage | Network unavailable | Empty offline explanation and retry |
| Cached records | New server version | New content replaces or merges according to policy |
| Pending local edit | Reconnect | Queued status followed by the acknowledged result |
| Invalid cached schema | Migration or recovery | The supported migrated or recoverable state |

Use a real test database for persistence and migration claims. Seed records through the repository's test setup, close the database, reopen it, and read the records. Keep that test separate from a rendering test that supplies a list in memory.

For a UI refresh test, hold the network fake, assert cached content, release a newer result, then assert new content and removal of the stale indicator. Do not clear all cache state as a blanket repair for a failed update test.

## Test retries, updates, and cancellation

Use stable operation identifiers for repeated submissions. A unique-work policy and a server idempotency policy solve different problems. Test both at their respective boundaries.

In an adapter test, enqueue the same logical sync twice and inspect the resulting work according to the configured unique-work policy. In a repository test, replay a completed operation and verify it does not duplicate the durable record. A fake UI success alone proves neither property.

For retry, supply a retryable first result and a successful next result. Assert the visible failure or pending state before releasing the next attempt. Verify permanent rejection does not silently become delivered.

For cancellation, cancel the owned work or leave the screen according to the product contract. Screen disposal need not cancel durable WorkManager work. Do not impose composition lifetime on a task designed to survive the screen.

Test application upgrades with database migrations and changed request-input contracts. There is no Android equivalent of a service worker's install, waiting, activate, and controller-change cycle.

## Test push and notification entry points

Extract message parsing and app-state updates from the provider callback. Give the handler a fixed payload and verify the repository change or notification request. Then render the affected screen and assert its result.

For notification entry, verify destination data and route parsing, including missing identifiers and an expired session. Keep actual push token registration, delivery while backgrounded, notification presentation, and tap behavior in provider or device coverage.

Do not send real push messages in every local test. Do not claim a locally invoked callback proves provider delivery.

## Isolate work and control time

Use a fresh database, work identifiers, fakes, and test-owned executors. Cancel test-owned work and close resources after each test, including failures. Avoid sharing a process-global WorkManager setup across unrelated classes without a defined lifecycle.

Distinguish the Compose clock, coroutine test scheduler, WorkManager test driver, Android loopers, and business clock. Select the one that owns the awaited condition. Do not globally drain all queues.

For timestamped cache expiry, inject the repository's time source. Changing Compose time does not change `Instant.now()` or a stored expiration timestamp.

## Avoid false-green background tests

| Anti-pattern | Why it fails | Correction |
| --- | --- | --- |
| Assert only that enqueue returned | The worker may never run or may fail | Inspect worker result and UI state in their own tests |
| Sleep until sync probably finished | Machine load changes the result | Hold the fake or use the WorkManager test driver |
| Cancel durable sync when a screen leaves | The work is meant to outlive that screen | Test the actual lifecycle contract |
| Share a work database | Old records can satisfy new assertions | Give each test isolated storage |
| Use a fake cache and claim persistence | In-memory state survives only in the fake | Reopen a real test database |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| WorkManager already initialized | Application startup and initializer order | Install the test environment before production access |
| Request remains enqueued | Constraints, input, delay, and test driver | Release the specific constraint or delay |
| Worker succeeds but UI stays queued | Repository update and flow collection | Repair the worker-to-repository result path |
| Offline screen is empty | Cache seed and repository read policy | Seed the real boundary used by the screen |
| Test hangs on a future | Executor and thread ownership | Avoid waiting on a thread needed to run the work |
| Duplicate delivery | Work identity and server idempotency key | Test and repair the responsible boundary |

## Review checklist

- Are enqueueing, execution, persistence, and UI claims separate?
- Does pending work remain pending until the test releases it?
- Do offline tests cover cached and uncached data?
- Are retries, permanent failure, and cancellation distinguished?
- Does cleanup close databases and owned executors?
- Are OS scheduling and push delivery reserved for integration evidence?

## Related guides and sources

- [Reactive streams](reactive-streams.md) covers observing work results.
- [Network fakes](../advanced/network-fakes.md) covers transport boundaries.
- [Navigation](../frameworks/navigation.md) covers notification destinations.
- [WorkManager worker testing](https://developer.android.com/develop/background-work/background-tasks/testing/persistent/worker-impl) documents worker builders.
- [WorkManager integration testing](https://developer.android.com/develop/background-work/background-tasks/testing/persistent/integration-testing) documents initialization and `TestDriver`.
- [Offline-first architecture](https://developer.android.com/topic/architecture/data-layer/offline-first) describes local data and synchronization policy.
