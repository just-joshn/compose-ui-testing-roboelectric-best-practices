# Control clocks, timers, and date-dependent UI

## Table of contents

- [Choose the time owner](#choose-the-time-owner)
- [Fix business time before creating content](#fix-business-time-before-creating-content)
- [Advance Compose effects deliberately](#advance-compose-effects-deliberately)
- [Test debounce and repeated work](#test-debounce-and-repeated-work)
- [Control animation frames](#control-animation-frames)
- [Cover zones and date boundaries](#cover-zones-and-date-boundaries)
- [Separate external work and loopers](#separate-external-work-and-loopers)
- [Avoid time shortcuts](#avoid-time-shortcuts)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the time owner

Use this guide for countdowns, delayed messages, relative dates, debounce, polling, and animations in local Android Compose tests. Use the [host setup](../references/setup.md) before adding manual time control.

There is no single clock that replaces every Android time source. Identify the owner before advancing anything.

| Work | Control | What it does not control |
| --- | --- | --- |
| Recomposition and Compose animation | `rule.mainClock` | Real service responses |
| Composition-owned coroutine effects | Compose clock and its scheduler | Independent dispatcher scheduler |
| ViewModel on an injected test dispatcher | That dispatcher's `TestCoroutineScheduler` | Compose unless deliberately shared |
| `Instant.now()` or billing date | Injected application clock | Coroutine delays |
| Android handler callback | The relevant Robolectric looper control | Every coroutine or executor |
| HTTP response | Controlled fake or transport | No clock can invent a response |
| Android drawing | Test framework synchronization | Device pixels or frame performance |

Keep `autoAdvance = true` for ordinary settled-state tests. Pause it only when the intermediate time is the behavior under test. Compose synchronization can advance virtual time to settle work and therefore skip a transient countdown value.

The fixture uses Compose UI 1.12.1 and `androidx.compose.ui.test.junit4.v2.createComposeRule`. Do not copy 1.13-only `ComposeUiTestConfig` into it.

## Fix business time before creating content

Inject time into the component that computes business state. `mainClock.advanceTimeBy` does not change `Clock.systemUTC()` or `System.currentTimeMillis()`.

Illustrative Kotlin fragment for a JVM or Android project that supports `java.time`. Use core-library desugaring if required by the consuming app's minimum SDK. This is not a fixture-compiled date formatter.

```kotlin
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

val clock = Clock.fixed(
	Instant.parse("2025-01-15T17:00:00Z"),
	ZoneId.of("America/Los_Angeles"),
)
val formatter = DateTimeFormatter
	.ofPattern("h:mm a", Locale.US)
	.withZone(clock.zone)
val label = formatter.format(clock.instant())
```

The expected label is `9:00 AM`. Pass `clock` into the real formatter, repository, or ViewModel before it is constructed. Passing a preformatted expected label into a `Text` composable tests only rendering.

For a holiday banner, seed a December instant before mounting the real route, then assert the banner. Use a separate January test that asserts absence. Avoid dates relative to the day the suite happens to run.

For "2 hours ago", fix both the current instant and the item's creation instant. Set locale and zone when the product's formatting depends on them. Test the actual formatting path rather than calculating expected text with the same production formatter.

## Advance Compose effects deliberately

The following complete illustrative test uses the pinned fixture's rule API. It requires the same Compose Material3, test, JUnit, Robolectric, resource, and manifest dependencies as [setup](../references/setup.md). It is not included in the canonical compiled fixture.

```kotlin
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class DelayedNoticeTest {
	@get:Rule val rule = createComposeRule()

	@OptIn(ExperimentalCoroutinesApi::class)
	@Test fun noticeAppearsAfterDelay() {
		rule.mainClock.autoAdvance = false
		rule.setContent {
			var ready by remember { mutableStateOf(false) }
			LaunchedEffect(Unit) {
				delay(1_000)
				ready = true
			}
			Text(if (ready) "Ready" else "Waiting")
		}
		rule.mainClock.scheduler.runCurrent()
		rule.onNodeWithText("Waiting").assertIsDisplayed()
		rule.mainClock.advanceTimeBy(500)
		rule.onNodeWithText("Ready").assertDoesNotExist()
		rule.mainClock.advanceTimeBy(600)
		rule.mainClock.scheduler.runCurrent()
		rule.mainClock.advanceTimeByFrame()
		rule.onNodeWithText("Ready").assertIsDisplayed()
	}
}
```

Start the effect before measuring its delay. With the v2 standard dispatcher, launching an effect does not imply immediate execution. `runCurrent()` starts queued tasks at the current virtual time without jumping forward.

`advanceTimeBy` normally rounds to frame boundaries. Work at the exact target time may still need a current-task step. The example checks before and after the deadline rather than claiming millisecond-exact frame timing.

For exact debounce boundaries, test the coroutine owner below the UI with an explicit scheduler. Keep the UI test focused on the visible result.

## Test debounce and repeated work

For search debounce, inject the dispatcher used by the real search owner. Enter query A, advance less than the debounce, enter query B, then advance beyond B's deadline. Assert results for B and absence of stale A results.

A repository test can assert which queries crossed its public boundary. The Compose test must still assert rendered results. Do not treat "search was called" as proof that the user saw the right results.

For polling, start with a controlled initial result. Advance one polling interval on its owner, release a different result, and assert the displayed update. Repeat once if repeated scheduling is part of the claim.

Do not call `advanceUntilIdle()` on an indefinitely polling owner. It may never become idle. Advance a bounded interval and cancel the polling scope in teardown.

For a sequence of notifications, verify the first item before advancing to the second. Use the app's actual queue policy. A single jump to the final item cannot catch incorrect ordering or omitted intermediate items.

For countdowns based on a business deadline, advance both dependencies only if both exist. Moving the wall clock may change the computed remaining time, but the UI still needs its scheduled tick to recompute. Advancing only the tick leaves the fixed clock unchanged.

## Control animation frames

Disable automatic advancement before the action that starts the animation. Perform the action, run queued effects if needed, and advance a frame to establish the animation's start. Then advance a measured virtual interval for an intermediate state or until the intended settled state.

Prefer semantic outcomes for behavior tests. For example, after expanding a card, assert that details are displayed and the collapse action is available. A screenshot or numeric property test can cover interpolation separately if that is the actual requirement.

`advanceTimeUntil` is suitable for a predicate on known Compose state changed by this clock. Do not call synchronized semantics assertions inside its predicate. Such calls can recursively request synchronization.

Use bounded `waitUntil` when the predicate needs semantics queries or progress outside this clock. Do not catch every assertion error in the predicate.

Clock advancement can drive recomposition and layout work. It does not establish Android drawing completion by itself. Let the Compose framework synchronize pending Android work before inspecting rendered output. No virtual-time test measures real device animation performance.

## Cover zones and date boundaries

Use explicit instants with offsets. A string without a zone can mean a different instant on another machine.

| Case | Suggested fixed inputs | Expected contract |
| --- | --- | --- |
| Same instant, two zones | UTC instant with Los Angeles and Tokyo | Local time and date match each zone |
| Month end | January 31 and February 1 | Billing message crosses correctly |
| Leap day | February 28, 29, and March 1 in leap year | Correct date arithmetic |
| Midnight | Instants just before and after local midnight | "Today" changes on the local date |
| Daylight saving transition | Named region zone across transition | Product-defined gap or overlap handling |
| Locale | Explicit supported locales | Order, text, and numerals follow policy |

Keep duration arithmetic separate from calendar arithmetic. A day is not always 24 elapsed hours in a regional time zone. Test the product's chosen rule rather than assuming either interpretation.

Avoid changing the JVM default time zone when a constructor parameter works. If a legacy path requires a global change, capture and restore the default in `finally`. Such tests must not run concurrently with code that reads the same global.

## Separate external work and loopers

The canonical [clock example](../examples/FixtureUiTest.kt) shows **Still sending** after a Compose delay while the sender remains pending. Completion requires explicitly releasing the sender.

The same separation applies to executor tasks, socket messages, and Android handlers. Observe which owner has pending work before advancing a scheduler. Do not drain every queue until the UI accidentally reaches the expected state.

If a ViewModel has a separate coroutine scheduler, either advance that scheduler deliberately or configure deliberate sharing through supported APIs. Wrapping the test in an unrelated `runTest` does not connect its time to Compose.

Do not replace `Dispatchers.Main` globally around a rule by guesswork. That can change the environment the Compose rule expects. Restore any required global replacement even if the assertion fails.

## Avoid time shortcuts

Bad practice is `Thread.sleep(1_000)` followed by an assertion on a composition-owned delay. Real time may not advance virtual time, and machine load makes the test slower without making it correct.

Correct it by starting the effect, advancing its clock, and asserting the transition. For a suspended external request, release the fake instead.

Another anti-pattern advances 24 hours for every delayed behavior. It hides wrong timer lengths, skips states, and can run unrelated periodic work. Choose bounded intervals on both sides of the relevant deadline.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| Delay never begins | v2 queued tasks at current time | Start tasks with the owned scheduler |
| Warning appears immediately | Auto-advance settled a timer | Pause before starting the transition |
| Date stays unchanged | Real application clock still fixed | Update injected business time |
| UI not updated at exact deadline | Task or recomposition still queued | Run current tasks and a frame |
| Test never becomes idle | Infinite animation or polling | Bounded advancement and cancellation |
| Local pass, CI date failure | Implicit locale or zone | Fix both inputs explicitly |

## Review checklist

- Does every timer have a named owner?
- Is time installed before a constructor captures it?
- Are there assertions before and after the intended deadline?
- Are business time, scheduling time, and external completion separate?
- Are repeating jobs cancelled and globals restored?
- Are drawing and performance claims kept outside virtual-time proof?

## Related guides and sources

- [Synchronization](../references/synchronization.md), [network fakes](network-fakes.md), and [authentication flows](authentication-flows.md).
- [State and ViewModels](../frameworks/state-viewmodels.md) and [canonical examples](../examples/FixtureUiTest.kt).
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) and [v2 migration](https://developer.android.com/develop/ui/compose/testing/migrate-v2).
- [MainTestClock API](https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock) defines frame and scheduler behavior.
- [Robolectric configuration](https://robolectric.org/configuring/) and [versioned evidence](../references/evidence.md) describe the local environment.
