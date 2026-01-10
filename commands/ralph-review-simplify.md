---
name: ralph-review-simplify
description: Run code-simplifier agent, save results to task
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
Task(subagent_type="code-simplifier:code-simplifier",
     prompt=context, model="opus")
```

## Добавь к существующему review

```python
existing = task.get("review", "")

update_task(
    project, number,
    review=existing + "\n\n### Code Simplifier\n" + results
)
```

## Верни статус

```
✅ Code Simplifier: {project}#{number} — N замечаний
```
