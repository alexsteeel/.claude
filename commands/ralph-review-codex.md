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

## 1. Получи задачу

Используй `mcp__md-task-mcp__tasks(project, number)` чтобы получить task.

## 2. Запусти Codex review

Выполни `/codex-review {project}#{number}` для проверки кода через Codex CLI.

## 3. ОБЯЗАТЕЛЬНО сохрани в review поле

```
mcp__md-task-mcp__update_task(
    project=project,
    number=number,
    review=existing_review + "\n\n---\n\n### Codex Review\n\n" + results
)
```

**НЕ записывай в blocks!** Только в `review` поле.

## 4. Верни статус

```
✅ Codex Review записан: {project}#{number} — N замечаний
```
