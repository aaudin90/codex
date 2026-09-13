---
name: code-breaking-changes
description: Breaking changes
---

Search for breaking changes in external integration surfaces:
- app-server APIs
- CLI parameters
- configuration loading
- resuming sessions from existing rollouts

Do not stop after finding one issue; analyze all possible ways breaking changes can happen.

When work touches Plan mode, model configuration, thread restoration, keybindings, subagent menus, or downstream history, read the [durable fork behavior contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
