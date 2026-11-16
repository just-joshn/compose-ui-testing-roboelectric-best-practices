# Select tests by method, package, and category

Use this guide to run one local regression, define smoke coverage, or separate required and quarantined suites. This skill uses JUnit 4 through Robolectric. Playwright tags and `--grep` are not Gradle test filters.

## Contents

- [Choose a selection mechanism](#choose-a-selection-mechanism)
- [Run a method or class](#run-a-method-or-class)
- [Declare JUnit categories](#declare-junit-categories)
- [Configure category selection](#configure-category-selection)
- [Express unions and intersections](#express-unions-and-intersections)
- [Define pipeline lanes](#define-pipeline-lanes)
- [Keep filtering separate from UI tags](#keep-filtering-separate-from-ui-tags)
- [Validate the selected evidence](#validate-the-selected-evidence)
- [Troubleshoot filters](#troubleshoot-filters)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a selection mechanism

| Need | Mechanism | Caveat |
| --- | --- | --- |
| Reproduce one regression | `--tests package.Class.method` | Quote shell wildcards |
| Run a feature package | `--tests 'package.feature.*'` | Inspect actual discovered methods |
| Select a business-critical lane | JUnit 4 `@Category` and `useJUnit` configuration | Metadata needs runner support |
| Select an Android build | Concrete variant task | Not a test category |
| Select a runtime SDK | Robolectric configuration | Not a Gradle `--tests` expression |
| Label a UI node | `Modifier.testTag` | Does not filter test methods |
| Exclude a known broken test | Explicit quarantine policy | A skipped or omitted test is not passing coverage |

Use package and method filters for debugging. Add categories when a maintained cross-feature lane needs a stable contract.

## Run a method or class

These commands assume a module named `app` and an existing debug local-unit-test task:

```bash
./gradlew :app:testDebugUnitTest --tests 'example.messages.MessageTest'
./gradlew :app:testDebugUnitTest \
  --tests 'example.messages.MessageTest.sendShowsReceipt'
./gradlew :app:testDebugUnitTest --tests 'example.messages.*'
```

To request either of two classes, repeat the filter:

```bash
./gradlew :app:testDebugUnitTest \
  --tests 'example.messages.MessageTest' \
  --tests 'example.profile.ProfileTest'
```

Multiple include filters select a union. They are not an AND expression. Gradle test filters are name patterns, not Playwright regular expressions. Do not paste lookahead expressions from a `--grep` recipe.

For a fresh diagnostic run, add `--rerun-tasks --console=plain`. This intentionally reruns relevant build work. It does not guarantee a completely cold environment.

Use the containing class after a narrow regression passes. A method passing alone may still leak or consume shared state when run with its neighbors.

## Declare JUnit categories

Categories are marker types. Keep them in a stable test package. This illustrative declaration needs JUnit 4.13.2:

```kotlin
package example.testcategories

interface Smoke
interface Critical
interface Quarantined
```

Apply them to a Robolectric class and method. This complete illustrative example uses the canonical `MessagePanel` and `Sender`, plus the configured local host:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import example.testcategories.Critical
import example.testcategories.Smoke
import fixture.MessagePanel
import fixture.Sender
import org.junit.Rule
import org.junit.Test
import org.junit.experimental.categories.Category
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@Category(Smoke::class)
class MessageTest {
	@get:Rule val rule = createComposeRule()

	@Category(Critical::class)
	@Test
	fun sendShowsReceipt() {
		rule.setContent { MessagePanel(Sender { "Delivered $it" }) }
		rule.onNodeWithText("Message").performTextInput("Hello")
		rule.onNodeWithText("Send").performClick()
		rule.onNodeWithText("Delivered Hello").assertIsDisplayed()
	}
}
```

This example checks the final result with an immediate fake. Use a controlled pending fake in a separate test when loading is part of the claim. Do not replace the Robolectric runner with JUnit's `Categories` runner on the test class. The build's JUnit category filter selects tests while the Robolectric runner executes them.

Class categories apply to the class's tests. Method categories add classification at a narrower scope. Keep that effective classification in mind when using exclusions.

## Configure category selection

The following illustrative Gradle Kotlin DSL fragment belongs in the Android module's build script. It assumes the existing local tasks use JUnit 4. A missing `testLane` property leaves the full suite unfiltered:

```kotlin
import org.gradle.api.tasks.testing.Test

val testLane = providers.gradleProperty("testLane").orElse("all")

tasks.withType<Test>().configureEach {
	useJUnit {
		when (val lane = testLane.get()) {
			"all" -> Unit
			"smoke" -> includeCategories("example.testcategories.Smoke")
			"critical" -> includeCategories("example.testcategories.Critical")
			"required" -> excludeCategories("example.testcategories.Quarantined")
			else -> error("Unknown testLane: $lane")
		}
	}
}
```

Run the configured lane:

```bash
./gradlew :app:testDebugUnitTest -PtestLane=smoke
./gradlew :app:testDebugUnitTest -PtestLane=required
```

The category string must match the fully qualified marker type. A typo can select no tests. Keep the list small and review each lane's actual executed methods.

This fragment configures every `Test` task in the module. Narrow it if the module also contains a differently configured test engine. Do not add `useJUnitPlatform()` merely to filter these JUnit 4 tests. That changes discovery requirements and needs the Vintage engine plus deliberate runner validation.

## Express unions and intersections

JUnit category lists generally express union within their include list. They do not provide a Playwright-style arbitrary regex expression over a tag string.

For a maintained intersection such as critical smoke coverage, prefer one explicit marker, such as `CriticalSmoke`, or a carefully reviewed build filter over the intended test names. Document that marker's admission criteria. Do not create a hierarchy of every possible Boolean combination.

For a one-off debug intersection, combine a category lane with a name filter:

```bash
./gradlew :app:testDebugUnitTest -PtestLane=smoke \
  --tests 'example.messages.*'
```

The selected tests must satisfy the configured smoke category and the message package include filter. An empty intersection is not successful evidence.

For exclusions, keep quarantine visible as a separately executed lane. Do not hide every unstable test behind a permanent `required` filter and report the remaining subset as full regression coverage.

## Define pipeline lanes

| Lane | Admission rule | Required observation |
| --- | --- | --- |
| Smoke | Small set of critical local behavior checks | Expected methods execute without skips |
| Full local regression | All deterministic local tests | Complete reports per module and variant |
| Quarantine | Known unstable cases with owner and issue | Failures remain visible outside the required lane |
| Service integration | Real adapter or service contract | Service preconditions and cleanup evidence |
| Device | Platform behavior not established locally | Device identity and actual instrumentation results |

Use feature packages for ownership. Use categories for a cross-cutting execution policy or priority. Avoid redundant labels such as both `Fast` and `Quick`, or a separate marker for every method.

A `Slow` category is a classification, not a timeout. A `Critical` category is a policy label, not proof that a test detects a broken action. Preserve behavior assertions and negative-control evidence.

Make lane selection explicit in CI commands. Hidden environment-based filters inside individual tests are hard to audit and can silently change coverage between local and CI runs.

## Keep filtering separate from UI tags

`Modifier.testTag("send")` labels a semantics node. It is consumed by `onNodeWithTag("send")`. It cannot make Gradle run a test called `sendShowsReceipt`.

JUnit `@Category(Smoke::class)` classifies a test description. It does not identify a UI node and does not add accessibility semantics.

Anti-patterns include adding `@smoke` to Kotlin method names and expecting `--grep`, or filtering on a UI tag through Gradle. Use runner metadata for tests and semantics identity for controls.

## Validate the selected evidence

Check the process exit code and the task's JUnit XML. Require nonzero executed tests, zero unexpected failures and errors, and no skipped expected methods. Compare the executed method set to the lane contract.

Do not disable fail-on-no-matching-tests to silence a typo. Do not count `UP-TO-DATE`, `NO-SOURCE`, or an empty HTML report as a new behavior execution. For SDK-expanded or parameterized methods, inspect the runner's actual reported names before designing a strict method matcher.

Archive the full command, selected variant, categories, and expected names. Then rerun the containing class or full lane after a narrow correction to check isolation.

## Troubleshoot filters

| Symptom | Observe | Fix |
| --- | --- | --- |
| No matching tests | Task, package, method name, and quoting | Use the actual discovered name and correct variant |
| Category ignored | Annotation package and configured engine | Use JUnit 4 categories with the JUnit 4 runner path |
| Smoke lane runs too much | Class-level categories and marker hierarchy | Narrow the admission rule |
| Intended test omitted | Category string or filter intersection | Correct fully qualified type or name pattern |
| Green lane contains skips | Ignore and assumptions in XML | Restore required execution or report missing coverage |
| CI and local differ | Command and hidden environment filters | Make lane configuration explicit |

## Review checklist

- The filter selects test descriptions, not UI tags.
- Categories have documented, distinct meanings.
- Narrow runs are followed by containing-suite checks.
- Required lanes verify expected method execution and reject empty results.
- Quarantine remains accountable and visible.
- No engine migration is hidden inside a filtering change.

## Related guides and sources

- [Annotations](annotations.md) covers ignore and assumption behavior.
- [Suite structure](test-suite-structure.md) organizes packages and layers.
- [JUnit 4 Category](https://junit.org/junit4/javadoc/4.13.2/org/junit/experimental/categories/Category.html) defines marker usage.
- [Gradle test filtering](https://docs.gradle.org/current/userguide/java_testing.html#test_filtering) documents name filters.
- [Gradle JUnit options](https://docs.gradle.org/current/javadoc/org/gradle/api/tasks/testing/junit/JUnitOptions.html) documents category selection.
