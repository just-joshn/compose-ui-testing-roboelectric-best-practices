# Test Doubles: Fakes, Mocks, and Shadows

## Table of Contents

1. [Core Principle](#core-principle)
2. [Decision Matrix](#decision-matrix)
3. [Fakes](#fakes)
4. [Dependency Injection Seams](#dependency-injection-seams)
5. [Hermetic Tests](#hermetic-tests)
6. [Android Classes: Do Not Mock](#android-classes-do-not-mock)
7. [Threads and Executors](#threads-and-executors)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

> **When to use**: Deciding how to replace a dependency in a unit, Robolectric, or device test. Default to a fake.

## Core Principle

**Prefer fakes. Avoid complex mocks. Never mock Android classes that other Android code acts on.** Fakes "don't require a mocking framework and are lightweight. They are preferred." Android's UI-testing guidance gives the example of replacing a data repository with an in-memory version that provides fake, deterministic data.

## Decision Matrix

| Dependency                                  | Double          | Strategy                                                          |
| ------------------------------------------- | --------------- | ----------------------------------------------------------------- |
| Your repository / data source               | Fake            | In-memory implementation giving fake, deterministic data          |
| Network, database                           | Fake            | Replace the module via DI; keep the test hermetic                 |
| Library with official testing support       | Its fakes       | Check for officially-supported testing infrastructure             |
| Android class (`Context`, `SharedPreferences`) | Real, via Robolectric | Do not mock or spy; stubbing is very brittle              |
| Android class needing a double              | Shadow          | "Fake used in Robolectric"; Robolectric shadows for Android classes |
| Dispatchers                                 | `TestDispatcher` | Inject and replace; see [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md) |
| Behavior verification of a collaborator     | Mock            | Only for simple interactions; avoid complex mocks                 |
| Spy on real object                          | Spy             | Usually avoided; adds complexity                                  |

Terminology: Fake (working lightweight implementation), Mock (verifies interactions), Stub (canned answers; fakes are preferred over stubs), Dummy (fills a parameter), Spy (wraps a real object), Shadow (Robolectric's fake).

## Fakes

Put fakes in the test source set and implement the production interface.

```kotlin
// src/test/java/.../FakeUserRepository.kt
object FakeUserRepository : UserRepository {
    private val users = listOf(User("1", "Alex"), User("2", "Sam"))

    override fun getUser(id: String): User? = users.find { it.id == id }
}
```

```kotlin
// Good: a ViewModel unit test with a fake, no mocking framework
class UserViewModelTest {
    @Test
    fun loadsUser() {
        val viewModel = UserViewModel(FakeUserRepository)

        viewModel.load("1")

        assertEquals("Alex", viewModel.state.value.name)
    }
}
```

```kotlin
// Bad: complex mock wiring that mirrors the implementation
val repository = mockk<UserRepository>()
every { repository.getUser("1") } returns User("1", "Alex")
```

## Dependency Injection Seams

"The recommended approach to replace dependencies is dependency injection." Use interfaces plus constructor injection "even if you don't use a DI framework". Do not use Android `Context` in ViewModels.

```kotlin
// Good: dependency arrives through the constructor
class UserViewModel(private val repository: UserRepository) : ViewModel()

@Test
fun showsFakeUser() {
    composeTestRule.setContent { UserScreen(UserViewModel(FakeUserRepository)) }
    composeTestRule.onNodeWithText("Alex").assertIsDisplayed()
}
```

For big tests, use a DI framework such as Hilt to replace a data repository with an in-memory version. Composables usually consume dependencies through a ViewModel, so replacing the binding in Hilt is enough. Details in [hilt.md](../frameworks/hilt.md).

Pass navigation callbacks (lambdas) into screens instead of a `NavController`, so tests supply mock values or callbacks. See [navigation.md](../frameworks/navigation.md).

## Hermetic Tests

A hermetic test "avoids all external dependencies, such as fetching data from the internet". It is more reliable and faster.

- Fake the data layer; never reach a real server from `src/test`.
- Make dispatchers and clocks injectable so time is virtual.
- Make fire-and-forget work awaitable (suspending function or `Deferred`).
- Keep state out of statics shared across tests.

## Android Classes: Do Not Mock

Robolectric runs real framework code, so use it instead of stubbing.

```kotlin
// Bad: mocking a Context that other Android code will act on
val context = mockk<Context>()

// Good: the real application context under Robolectric
val context = ApplicationProvider.getApplicationContext<Context>()
```

- Test layout inflation and click listeners directly "rather than mocking the LayoutInflater or providing an abstraction over the View".
- Use public lifecycle APIs, not `@VisibleForTesting` hooks.
- Plain AGP unit tests without Robolectric get stubbed Android APIs that throw `Method ... not mocked`. `unitTests.returnDefaultValues = true` hides this and "might allow failing tests to pass"; use it only as a last resort.

```kotlin
// build.gradle.kts: last resort, not a default
android { testOptions { unitTests.returnDefaultValues = true } }
```

## Threads and Executors

"Limit the number of threads that are running during each test." Rogue threads (for example `ExecutorService` pools) pollute other tests. If possible, mock dependent components that spawn threads, or use `MoreExecutors.directExecutor()`. If multiple threads are necessary, explicitly stop all threads and `ExecutorService`s.

## Anti-Patterns to Avoid

| Don't Do This                                  | Problem                                              | Do This Instead                                      |
| ---------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Mock `Context` or `SharedPreferences`          | Stubbing is very brittle                             | Real classes on Robolectric                          |
| Complex mocks                                  | Coupled to implementation                            | Fakes, or shadows for Android classes                |
| `returnDefaultValues = true` as default        | Failing tests can pass                               | Robolectric, or fakes                                |
| Test hits the real network                     | Slow, flaky, not hermetic                            | Fake the data source via DI                          |
| Spies everywhere                               | Complexity                                           | Fakes                                                |
| Unbounded executors in tests                   | Test pollution                                       | `directExecutor()`, stop threads                     |

## Related References

- **Coroutine test dispatchers**: See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md)
- **Hilt bindings**: See [hilt.md](../frameworks/hilt.md)
- **Choosing test types**: See [test-architecture.md](test-architecture.md)
- **Navigation callbacks**: See [navigation.md](../frameworks/navigation.md)

## Sources

- https://developer.android.com/training/testing/fundamentals/test-doubles
- https://developer.android.com/training/testing/fundamentals
- https://developer.android.com/training/testing/local-tests
- https://developer.android.com/training/testing/ui-tests
- https://developer.android.com/training/dependency-injection/hilt-testing
- https://developer.android.com/guide/navigation/testing/compose
- https://robolectric.org/best-practices/
