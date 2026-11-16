# Reference skill inspection

Inspected [currents-dev/playwright-best-practices-skill](https://github.com/currents-dev/playwright-best-practices-skill/tree/0b75b5835a87de1fdd202ba965f3bc5a27738fdf) at commit `0b75b5835a87de1fdd202ba965f3bc5a27738fdf` on 2026-11-16, before designing this skill.

## Activation

`playwright-best-practices/SKILL.md` has Agent Skills frontmatter with `name`, a task-rich `description`, MIT license, and author/version metadata. Its description names writing, debugging, reviewing, and configuration activities rather than requiring an explicit invocation.

This skill keeps task-based activation but restricts it to Kotlin Compose UI testing with Robolectric. It does not claim general Android testing expertise.

## Routing

The reference uses activity-to-reference tables and a second decision tree. Categories include writing, debugging, architecture, maintenance, and setup. Individual Markdown files carry the detail.

This skill keeps activity routing in one concise table. It does not repeat the table as a decision tree. Compose semantics, clock ownership, and Android local-unit-test setup replace browser topics.

## Packaging

The reference repository has one named skill directory, a root README, and a root MIT notice. Its README advertises `npx skills add https://github.com/currents-dev/playwright-best-practices-skill`.

This repository uses the same discoverable named-directory convention. The installed directory must be self-contained. The executable validation fixture and evidence report remain repository artifacts, not mandatory application dependencies.

## Examples

Inspected `core/locators.md` and the entry skill. The locator reference uses focused headings, a table of contents, Kotlin-inapplicable TypeScript examples, short rules, and links to related waiting guidance. The entry skill ends with a run-and-debug loop.

This skill keeps short positive and negative examples with links to executable Kotlin tests. It does not translate DOM locators, browser auto-waiting, page objects, screenshots, or browser lifecycle into Compose equivalents. Compose assertions synchronize with registered idle work but are not Playwright-style retrying assertions for arbitrary external work.

## License and attribution

The reference is MIT, Copyright 2026 Currents Software Inc. Its permission notice requires inclusion with copies or substantial portions. No browser example code or reference prose is copied. The packaging and activity-routing design inform this skill. The installed skill includes the original MIT notice and an attribution file so redistribution preserves credit even under a conservative reading of reuse.
