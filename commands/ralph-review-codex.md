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

## Запусти Codex review через Task (изолированный контекст)

Используй Task tool для запуска codex-review в изолированном контексте:

```
Task(
    subagent_type="general-purpose",
    prompt="/codex-review $ARGUMENTS"
)
```

**Codex сам сохраняет результаты в review поле задачи** — не дублируй!

## Верни статус

После завершения Task:

```
✅ Codex Review: {project}#{number} — см. review поле задачи
```
