# Write a Test

## When to use

Use this playbook when the goal is a new Compose UI test that runs on Robolectric.

## Investigate and establish evidence

1. Read the composable under test, the code that calls it, and any existing tests that cover it.
2. Check that the module declares the Compose UI test dependencies and the Robolectric dependencies. See [configuration.md](../core/configuration.md#quick-reference).
3. Check which SDK level Robolectric runs the code against and which Java version that level needs. See [configuration.md](../core/configuration.md#sdk-level) and [the Java version table](../core/configuration.md#android).
4. Check that the test will live in the `test` source set, where any UI test runs with Robolectric. See [test-suite-structure.md](../core/test-suite-structure.md#running-on-robolectric).
5. Decide whether Robolectric has enough fidelity for the behavior, or whether it needs a device test, such as system UI like edge-to-edge or picture-in-picture. See [test-architecture.md](../architecture/test-architecture.md#device-tests).
6. Decide how much UI the test covers: `ComposeTestRule` lets you start an activity displaying any composable, whether your full application, a single screen, or a small element. See [test-suite-structure.md](../core/test-suite-structure.md#test-scope).
7. Print the semantics tree, which is the main way to solve problems in tests. Developers decide what and how much to expose to it. See [debugging.md](../debugging/debugging.md#semantics-tree-printing) and [semantics-finders.md](../core/semantics-finders.md#semantics-tree).
8. Run the existing tests of the module and record the exact command and its result.

## Deliver supported findings

- State the behavior the test will check and the success check.
- Name the rule or test function, the finders, and the assertions chosen, each with the reference or official page that supports it.
- Name any behavior that needs a device test, with the evidence.
- List open questions.

## Design and implement

- Build the test from the documented structure: a rule, content set on it, a finder, an action, and an assertion. See [test-suite-structure.md](../core/test-suite-structure.md#quick-reference).
- Use the v2 rule and test functions. The v1 APIs are deprecated, and migrating to the new APIs is strongly recommended. See [test-suite-structure.md](../core/test-suite-structure.md#v2-apis).
- Pick the function that matches where the content is hosted: `createComposeRule` for tests where it is irrelevant where the compose content is hosted, `createAndroidComposeRule` for tests that require a custom Activity, `createEmptyComposeRule` for tests that need to create their own compose host during the test. See [test-suite-structure.md](../core/test-suite-structure.md#rule-and-test-functions-v2).
- A common pattern for accessing activity resources while setting your own content is to create the rule with an empty activity such as `ComponentActivity`, which needs to be added to the app's manifest through the documented dependency. See [test-suite-structure.md](../core/test-suite-structure.md#setting-content).
- Select nodes with finders. `useUnmergedTree` is for tests with a special need to inspect implementation detail within children. See [semantics-finders.md](../core/semantics-finders.md#finders) and [semantics-finders.md](../core/semantics-finders.md#merged-and-unmerged-trees).
- Rely on the documented synchronization: assertions and actions on the rule synchronize with the UI first, and a condition that depends on external work should use a more general concept such as `waitUntil`. See [synchronization.md](../core/synchronization.md#automatic-synchronization) and [synchronization.md](../core/synchronization.md#waiting-for-conditions).
- To run under a different SDK, specify the desired SDK(s) using the `sdk`, `minSdk` and `maxSdk` config properties. You can explicitly configure the set of resource qualifiers in effect for a test with `qualifiers`. To configure Robolectric for a single test class or method, use the `@Config` annotation on that class or method. See [configuration.md](../core/configuration.md#sdk-level), [configuration.md](../core/configuration.md#qualifiers), and [configuration.md](../core/configuration.md#config-annotation).

## Verify behavior and challenge findings

- Run the new test and record the exact command and its result.
- Break the behavior the test checks, confirm the test fails, then restore the behavior.
- Check whether the test is a behavior test. You can run behavior tests on Robolectric, for example when a Compose test verifies that the UI has changed after clicking a button. See [test-architecture.md](../architecture/test-architecture.md#behavior-tests).
- Check whether the test mocks or spies on Android classes that will be acted on by other Android code. The small exceptions are classes with very narrow responsibilities, such as event listeners. See [test-doubles.md](../architecture/test-doubles.md#mocking-and-spying-on-android-classes).
- Check whether the test waits with an external mechanism such as `CountDownLatch` instead of the `waitUntil` APIs. In some cases this could behave unexpectedly, since the test clock won't be advanced. See [synchronization.md](../core/synchronization.md#warnings).
- Ask an independent reviewer to challenge the test and to check each technical statement against its reference.

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/debug
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/v2/package-summary
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/getting-started
- https://robolectric.org/configuring/
- https://robolectric.org/compatibility_table
- https://robolectric.org/best-practices
