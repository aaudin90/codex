---
name: code-review-context
description: Model visible context
---

Codex maintains a context (history of messages) that is sent to the model in inference requests.

1. No history rewrite - the context must be built up incrementally.
2. Avoid frequent changes to context that cause cache misses.
3. No unbounded items - everything injected in the model context must have a bounded size and a hard cap. 
4. No items larger than 10K tokens.
5. Highlight new individual items that can cross >1k tokens as P0. These need an additional manual review.
6. All injected fragments must be defined as structs in `core/context` and implement ContextualUserFragment trait

When work touches Plan mode, model configuration, thread restoration, keybindings, subagent menus, or downstream history, read the [durable fork behavior contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
