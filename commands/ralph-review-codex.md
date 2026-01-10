---
name: ralph-review-codex
description: Run Codex review, save results to task
arguments:
  - name: task_ref
    description: Task reference "project#N"
    required: true
---

Task ref: `$ARGUMENTS`

## Получи контекст задачи

```python
task = get_task(project, number)
context = f"""
Контекст задачи:
- Описание: {task.description}
- План: {task.plan}
"""
```

## Запусти агент

```
Task(subagent_type="general-purpose",
     prompt=context + "\n\nВыполни /codex-review", model="opus")
```

## Добавь к существующему review

```python
existing = task.get("review", "")

update_task(
    project, number,
    review=existing + "\n\n### Codex Review\n" + results
)
```

## Верни статус

```
✅ Codex Review: {project}#{number} — N замечаний
```
