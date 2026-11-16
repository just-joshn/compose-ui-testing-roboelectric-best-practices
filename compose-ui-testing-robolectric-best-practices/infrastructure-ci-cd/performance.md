# Reduce local UI test feedback time

Use this guide to improve suite execution and CI feedback for Compose tests on
Robolectric. It measures the test system, not application frame rate or device startup.
Use Android benchmarks for product performance claims.

## Table of contents

- [Choose the optimization target](#choose-the-optimization-target)
- [Separate setup from execution](#separate-setup-from-execution)
- [Measure equivalent work](#measure-equivalent-work)
- [Tune forks and modules](#tune-forks-and-modules)
- [Reduce unnecessary setup](#reduce-unnecessary-setup)
- [Remove uncontrolled external work](#remove-uncontrolled-external-work)
- [Replace sleeps with work ownership](#replace-sleeps-with-work-ownership)
- [Control memory and resource lifetime](#control-memory-and-resource-lifetime)
- [Decide whether to shard](#decide-whether-to-shard)
- [Keep diagnostics proportional](#keep-diagnostics-proportional)
- [Avoid apparent speedups](#avoid-apparent-speedups)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the optimization target

| Observed cost | First change to evaluate | Preserve |
| --- | --- | --- |
| Dependency or SDK downloads | Trusted download cache or provisioned image | Same dependency versions |
| Android compilation | Gradle build cache and module inputs | Same source and variant |
| Robolectric initialization | Reuse test workers where safe | Fresh test state and composition |
| Long per-test setup | Mount the smallest real UI boundary | Actual action-to-result behavior |
| Fixed waits | Deterministic fake or clock ownership | Pending and completed-state assertions |
| Underused CPU with spare memory | More test forks | Complete test inventory |
| Memory pressure or native allocations | Fewer concurrent workers and proper cleanup | The same behavioral coverage |
| One machine's critical path | Independent CI shards | Complete disjoint partitions |
| Device jank | Device benchmark lane | Real renderer and release-like build |

Do not begin by reducing assertion strength or skipping flaky tests.
A faster suite that no longer detects the promised behavior is not an optimization.

## Separate setup from execution

Capture the whole job and distinguish:

1. Queue and checkout time.
2. JDK and Android SDK provisioning.
3. Wrapper and dependency downloads, including Robolectric runtime artifacts.
4. Gradle configuration, compilation, and resource processing.
5. Test worker startup and per-class execution.
6. Report generation and artifact upload.

Use the Gradle profile report for task-level costs:

```bash
./gradlew :app:testDebugUnitTest --profile --console=plain
```

Inspect `build/reports/profile/` in the root project.
Use JUnit test durations for class and method distribution, but do not sum them and
call the result the pipeline duration. Concurrent work and setup change the critical path.
Build scans can provide more detail, but review their data-sharing policy before
publishing a proprietary build to an external service.

## Measure equivalent work

The following shell commands illustrate a controlled local comparison.
The `uiTestForks` property must first be wired as shown in
[parallel sharding](parallel-sharding.md).

```bash
./gradlew :app:testDebugUnitTest -PuiTestForks=1 --rerun-tasks
/usr/bin/time -p ./gradlew :app:testDebugUnitTest \
  -PuiTestForks=1 --rerun-tasks --console=plain
/usr/bin/time -p ./gradlew :app:testDebugUnitTest \
  -PuiTestForks=2 --rerun-tasks --console=plain
```

This is a procedure, not a reported speed result.
Repeat baseline and treatment in alternating order to reduce warm-up bias.
Record Java, SDK, runner hardware, source revision, test inventory, and cache state.
Keep first-use download measurements separate from warm-input measurements.

`--rerun-tasks` forces requested task work rather than accepting up-to-date outputs.
It can also repeat compilation. Use the task profile to separate that cost.
Do not describe a build-cache hit as a test execution speedup.

Accept a change only if both runs execute the same expected methods without unexpected
skips and retain equivalent assertions. Compare failure rate as well as elapsed time.
Include queue time and repeated setup when deciding whether a CI change helps users.
Do not publish a percentage improvement from one noisy local run.

## Tune forks and modules

Gradle's `Test.maxParallelForks` controls test JVMs for a task.
Gradle `--parallel` enables eligible tasks in different projects.
`--max-workers` limits overall build worker resources.
They are not interchangeable switches.

Start with one fork on a constrained runner.
Increase only while the machine has CPU and memory headroom.
Account for the daemon, compiler workers, test heaps, native graphics, and filesystem I/O.
Running two workers with a large heap each does not leave the rest of the job free.

Do not add concurrent JUnit method execution to a Robolectric Compose class merely
because the processor has more cores. Android process state and framework scheduling
need a verified isolation model. Prefer separate test JVMs or independent CI jobs.

If a class dominates execution, first inspect its setup and behavior scope.
Split independent scenarios into classes only when that improves ownership and distribution.
Do not split one user flow into ordered methods that depend on a previous method's activity.

## Reduce unnecessary setup

Mount the smallest real component that owns the claimed behavior.
For a rendering test, supply a state value and assert that it renders correctly.
For an orchestration test, mount the real owner and drive the action through its fake
repository boundary. Do not inject the final state and claim the transition worked.

Use a fresh fake authenticated session for a screen that requires one.
Do not perform a real login before every local UI test.
Keep separate integration checks for session establishment and authorization.
Immutable fixture data can be reused as values. Mutable sessions and deferred results cannot.

Prefer per-test factories over static mutable objects:

```kotlin
import kotlinx.coroutines.CompletableDeferred

class PendingReceipt {
    val result = CompletableDeferred<String>()
}
```

This illustrative helper requires `kotlinx-coroutines-core` on the test classpath.
Construct it inside each test or in per-test setup.
Do not move it to a companion object to avoid one allocation.
A completed shared deferred changes later tests' initial state and can hide loading behavior.
The canonical [sender example](../examples/FixtureUiTest.kt) shows a full action and UI result.

Keep one content owner.
Do not reuse the same mounted activity across methods as an optimization.
If a launched activity sets content itself, do not add another `setContent` to that test.

## Remove uncontrolled external work

Fake repositories, image loaders, analytics, and time sources at explicit application
boundaries when those integrations are not the claim.
Do not mock Compose semantics, the test rule, or Android framework objects that
Robolectric needs to run realistically.

| External work | Local replacement | Separate proof |
| --- | --- | --- |
| Slow repository response | Per-test controllable deferred | Real client contract test |
| Remote image | Local deterministic image source | Decode and device rendering checks |
| Analytics upload | Recording fake | Transport and event-schema integration |
| Authentication refresh | Fake session state | OAuth and token handling integration |
| Wall-clock deadline | Injected clock | Real scheduling or service behavior |

Do not remove resources that are part of the UI claim just to make rendering faster.
Missing fonts, images, or layout inputs can change semantics, bounds, and behavior.
A JVM test does not prove device pixels even when it loads the same resources.

Avoid a global response cache that calls the real network on a miss.
It makes test order, cache warmth, and service availability affect the suite.
Use explicit deterministic data and test real network behavior separately.

## Replace sleeps with work ownership

Bad:

```kotlin
Thread.sleep(2_000)
```

A fixed delay spends wall time when the work finished early and still fails when it
finishes late. It also says nothing about which actor must make progress.

Use the smallest appropriate control:

- Complete the test's fake to release an external result.
- Use `mainClock` for Compose-owned animation or delay.
- Advance an independent coroutine scheduler only when it owns the pending work.
- Use a bounded `waitUntil` for genuine external progress that the test can observe.
- Register an idling resource only when that subsystem should participate in synchronization.

Compose actions and assertions synchronize known work.
They are not Playwright-style retrying assertions for arbitrary business state.
Increasing every timeout does not repair a fake that never completes.
Do not globally drain loopers and schedulers until the symptom disappears.

When measuring pending UI, hold the result with a controllable fake.
Do not register that same pending operation as globally busy if synchronized assertions
must inspect the pending state. They would wait for the state you are trying to hold.
See [synchronization](../references/synchronization.md).

## Control memory and resource lifetime

Close every resource the test owns:

- Cancel test-owned coroutine scopes.
- Stop local HTTP servers and release sockets.
- Shut down executors and join owned threads.
- Unregister idling resources.
- Restore changed dispatchers, globals, and system properties.
- Let the Compose rule dispose the composition.

Robolectric does not clean up arbitrary rogue threads for you.
A worker that stays alive after tests finish can be a cleanup defect rather than a
slow assertion. Inspect thread ownership before forcing process termination.

Use bounded memory settings based on the runner's actual limit.
Do not raise test heaps until the operating system kills the whole job.
Native allocations are not fully described by Java heap limits.
A periodic fresh fork may help diagnose growth, but it is not a substitute for closing resources.

## Decide whether to shard

Sharding repeats checkout, Gradle setup, resource processing, and worker initialization.
It helps when saved test execution exceeds those additional costs and queue delay.
Do not select a shard count from a universal five-minute rule.

Partition classes with explicit lists or a tested distribution integration.
Verify that the union matches the full intended method inventory.
Keep separate workspaces and artifact directories.
Balance using durations from the same variant, SDK, and runner class.
See [parallel sharding](parallel-sharding.md) for the implementation.

Keep the runtime SDK matrix as small as the behavior claim permits.
One pinned SDK is a reproducible default. Add SDKs for known framework risks.
Do not remove a required SDK dimension and call the reduced work a speed improvement.

## Keep diagnostics proportional

Retain JUnit and HTML on every ordinary completed run.
Capture semantics near failures rather than printing the entire tree after every action.
Do not disable result files merely to improve an upload timing while relying on them
for completeness checks.

Separate instrumented coverage runs from execution-speed measurements.
A profiler, verbose logging, coverage agent, and native renderer choice can change timing.
Keep each condition explicit in the measurement record.
No JVM test duration is a Macrobenchmark or device frame-time measurement.

## Avoid apparent speedups

| Anti-pattern | Why it looks faster | What it loses |
| --- | --- | --- |
| Share one mounted UI across methods | Avoids host setup | Isolation and reproducibility |
| Drop outcome assertions | Less synchronization | Detection of broken actions |
| Exclude flaky tests silently | Fewer failures and reruns | Required behavior coverage |
| Compare cold baseline with warm treatment | Downloads vanish | A valid causal comparison |
| Report only Gradle task duration | Omits queue and uploads | User-visible feedback time |
| Accept up-to-date outputs as execution | No test process runs | Fresh runtime evidence |
| Overpartition the suite | Each job appears shorter | Total compute and setup efficiency |

## Troubleshoot

| Symptom | Observe | Fix |
| --- | --- | --- |
| First class much slower | Runtime downloads and sandbox startup | Warm trusted inputs and keep cold cost separate |
| More forks cause timeouts | CPU, native memory, GC, disk pressure | Reduce concurrency before changing waits |
| One method always waits the same interval | Fixed sleeps or timeout-driven completion | Control the work owner explicitly |
| Fast alone, slow in suite | Shared state, unclosed threads, repeated host work | Repair ownership and setup scope |
| Container slower than host | Bind mount I/O and architecture emulation | Compare copied source and native architecture |
| Job finishes tests but never exits | Leaked executors or server threads | Close owned resources in cleanup |
| Coverage lane alone slows down | Agent overhead and report generation | Measure it separately from ordinary tests |

## Review checklist

- The optimization target is suite feedback, not device performance.
- Baseline and treatment execute equivalent tests and assertions.
- Cache state, runtime SDK, Java, and runner identity are recorded.
- Fork and shard decisions include total setup cost and resource limits.
- Fakes and mounted UI remain per-test.
- Waits target the actor that can complete the operation.
- Diagnostics and first-attempt failures remain available.

## Related guides and sources

- [Parallel execution](parallel-sharding.md), [CI](ci-cd.md), and [coverage](test-coverage.md).
- [Device performance boundary](../testing-patterns/performance-testing.md).
- [Gradle performance](https://docs.gradle.org/9.4.1/userguide/performance.html).
- [Gradle profiling](https://docs.gradle.org/9.4.1/userguide/performance.html#profile_report).
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization).
- [Robolectric best practices](https://robolectric.org/best-practices/).
