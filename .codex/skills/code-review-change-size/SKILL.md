---
name: code-review-change-size
description: Change size guidance (800 lines)
---

Unless the change is mechanical the total number of changed lines should not exceed 800 lines.
For complex logic changes the size should be under 500 lines.

If the change is larger, explain whether it can be split into reviewable stages and identify the smallest coherent stage to land first.
Base the staging suggestion on the actual diff, dependencies, and affected call sites.

When work touches Plan mode, model configuration, thread restoration, or downstream history, read the [durable Plan mode contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
