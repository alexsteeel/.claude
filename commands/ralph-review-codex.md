---
name: ralph-review-codex
description: Run Codex review, save results to task
arguments:
  - name: task_ref
    description: Task reference "project#N"
    required: true
---

Task ref: `$ARGUMENTS`

**ВАЖНО:** Это standalone review команда, НЕ полный workflow. Не требует confirmation phrase.

## Запусти Codex review

Выполни `/codex-review {project}#{number}` для проверки кода через Codex CLI.

**Codex сам сохраняет результаты в review поле задачи** — не дублируй!

## Верни статус

После завершения `/codex-review`:

```
✅ Codex Review: {project}#{number} — см. review поле задачи
```
