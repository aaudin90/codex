---
name: code-review-testing
description: Test authoring guidance
---

For agent changes prefer integration tests over unit tests. Integration tests are under `core/suite` and use `test_codex` to set up a test instance of codex.

Features that change the agent logic MUST add an integration test:
- Provide a list of major logic changes and user-facing behaviors that need to be tested.

If unit tests are needed, put them in a dedicated test file (*_tests.rs).
Avoid test-only functions in the main implementation.

Check whether there are existing helpers to make tests more streamlined and readable.

When work touches Plan mode, model configuration, thread restoration, or downstream history, read the [durable Plan mode contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
