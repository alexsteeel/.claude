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

Используй Task tool с **явными инструкциями** для subagent:

```
Task(
    subagent_type="general-purpose",
    prompt="## КРИТИЧЕСКИ ВАЖНО — Прочитай внимательно!

Ты ДОЛЖЕН использовать Skill tool для загрузки инструкций codex-review.
Это НЕ просьба сделать code review — это команда вызвать конкретный skill.

### Что ты ДОЛЖЕН сделать:

1. Вызови Skill tool:
   ```
   Skill(skill=\"codex-review\", args=\"$ARGUMENTS\")
   ```

2. Skill загрузит 404 строки инструкций включая:
   - 6 фаз workflow (Get Task → Run Codex → Read Review → Handle Issues → Re-Review → Finalize)
   - Команду `codex review` с профилем gpt-5.2-codex
   - UI тестирование через Playwright
   - До 3 итераций проверок

3. Следуй инструкциям из загруженного skill

### Что тебе ЗАПРЕЩЕНО:

❌ НЕ делай review самостоятельно
❌ НЕ запускай git diff, ruff, тесты напрямую
❌ НЕ используй Edit tool для редактирования кода
❌ НЕ пиши свой review вместо вызова Codex CLI

### Проверка успеха:

После выполнения skill в логе ДОЛЖНЫ быть:
- Вызов `which codex`
- Вызов `codex review ...`
- Запись в review поле задачи через mcp__md-task-mcp__update_task

Начни с вызова Skill tool СЕЙЧАС."
)
```

**Codex сам сохраняет результаты в review поле задачи** — не дублируй!

## Верни статус

После завершения Task:

```
✅ Codex Review: {project}#{number} — см. review поле задачи
```

Если в результате Task **НЕТ** вызова `codex review`:

```
❌ Codex Review FAILED: subagent не вызвал Skill tool
   Проверь лог на наличие "codex review" команды
```
