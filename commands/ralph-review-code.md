---
name: ralph-review-code
description: Run 5 code review agents in parallel, save results to task
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

## Запусти 5 агентов ПАРАЛЛЕЛЬНО

Все 5 Task в **ОДНОМ сообщении**:

```
Task(subagent_type="pr-review-toolkit:code-reviewer",
     prompt=context, model="opus")

Task(subagent_type="pr-review-toolkit:silent-failure-hunter",
     prompt=context, model="opus")

Task(subagent_type="pr-review-toolkit:type-design-analyzer",
     prompt=context, model="opus")

Task(subagent_type="pr-review-toolkit:pr-test-analyzer",
     prompt=context, model="opus")

Task(subagent_type="pr-review-toolkit:comment-analyzer",
     prompt=context, model="opus")
```

## Добавь к существующему review

```python
existing = task.get("review", "")

update_task(
    project, number,
    review=existing + "\n\n### Code Review (5 agents)\n" + results
)
```

## Верни статус

```
✅ Code Review: {project}#{number} — N замечаний
```
