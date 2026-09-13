---
name: code-review
description: Run a final code review on a pull request
---

Use subagents to review code using all code-review-* skills other than this orchestrator. One subagent per skill. Pass full skill path to subagents. Use xhigh reasoning.

You must return every single issue from every subagent. You can return an unlimited number of findings.
Use raw Markdown to report findings.
Number findings for ease of reference.
Each finding must include a specific file path and line number.

If the GitHub user running the review is the owner of the pull request add a `code-reviewed` label.
Do not leave GitHub comments unless explicitly asked.

When work touches Plan mode, model configuration, thread restoration, or downstream history, read the [durable Plan mode contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
