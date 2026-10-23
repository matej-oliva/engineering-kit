---
name: kit-grill-me
description: Interview the user about a plan, decision or idea in numbered rounds with recommended answers. Use only when the user asks for kit-grill-me or grill-me by name; do not start automatically for ordinary planning or decisions.
disable-model-invocation: true
---

Follow `.engineering-kit/kit/procedures/grill-me.md`. Start only when the
user asks for this interview by name; otherwise return to the current task.
The interview reads evidence and changes nothing. Acting on its outcome
requires a separate request under the project's rules.
