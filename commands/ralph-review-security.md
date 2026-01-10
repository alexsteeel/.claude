---
name: ralph-review-security
description: Run security review, save results to task
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
     prompt=context + "\n\nВыполни /security-review", model="opus")
```

## Добавь к существующему review

```python
existing = task.get("review", "")

update_task(
    project, number,
    review=existing + "\n\n### Security Review\n" + results
)
```

## Верни статус

```
✅ Security Review: {project}#{number} — N уязвимостей
```
