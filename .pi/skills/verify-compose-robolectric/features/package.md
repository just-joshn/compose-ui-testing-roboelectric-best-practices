# Package portability and hosted setup

A user installs the named skill with its references/examples/licenses intact, then runs the documented local JVM fixture. A copied package must remain useful without paths into the original checkout.

## Sub-features

- `package-copy`: frontmatter, all seven foundation references, all 58 mapped topic guides, direct routes, local links and fragments, Kotlin examples, and license/attribution files survive copying.
- `package-reject`: deliberately broken packages fail validation, including missing map records, unknown sources, unsafe or unrouted targets, orphan guides, and broken fragments.
- `setup-host`: resource-enabled tests can start the hosted Compose UI.
- `setup-compare`: observe what changes when only Android resource inclusion is disabled.

## How to get to it (user POV)

- Follow README installation using the skills CLI and `--skill compose-ui-testing-robolectric-best-practices`.
- Or manually copy the entire named skill directory, preserving its child directories.
- Follow README's fixture command `./gradlew :fixture:testDebugUnitTest --console=plain --rerun-tasks`.

## Driving it with Python/Gradle

Preconditions:

- Launch and doctor succeeded. The current skill/build files have not changed since launch.
- Package files and Android prerequisites exist; missing files/tools are failures, not optional setup.

- **Copied-package path.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" package`. Require both package checks and the standalone copied-install check to pass, plus all malformed-package rejection tests. Inspect `evidence/package/command-*.log` and `commands.json`.
- **Hosted fixture path.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" suite`. Require 8 executed tests with zero failures/skips and the expected names in baseline `result.json`. Launch compilation alone does not establish the UI host works.
- **Resource comparison.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" setup`. Inspect all `resources-*/result.json` files: enabled and restored must pass. To claim the documented host-resolution failure, disabled must reach the named test and fail because ComponentActivity cannot be resolved, not because of compilation or dependency failure. If disabled passes, report the changed observation rather than forcing failure.
- **Installer entry.** Actual skills-CLI installation is a separate user path, not exercised by `package`. When needed, perform the README install into a disposable consumer project, retain installer output and installed file inventory, and test invocation there. Do not install into the user's agent configuration or claim copied-package validation covered CLI prompts.

## Gotchas

- Do not run the installer against this checkout's agent directories merely to check structure.
- The comparison script's PASS means outcomes were recorded; it does not require the disabled case to fail for the documented reason. Read its JUnit/log evidence.
- Compile SDK 37 is not runtime SDK 35. Upgrading the runtime can require a different JDK.
- This map's initial proof does not certify a new installer invocation or a cold SDK installation.
