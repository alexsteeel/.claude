---
name: codex-review
description: Automated iterative code review with Codex CLI
arguments:
  - name: task_ref
    description: Task reference in format "project#N" (e.g., "myproject#4")
    required: true
---

Ты выполняешь автоматизированный итеративный код-ревью с использованием Codex CLI.

## Workflow Overview

```
1. GET TASK → 2. RUN CODEX REVIEW → 3. READ REVIEW → 4. FIX/CLARIFY → 5. RE-REVIEW → 6. COMPLETE
```

## Phase 1: Get Task Details

Получи детали задачи через md-task-mcp:
- Используй `mcp__md-task-mcp__tasks` с project и number из `{{task_ref}}`
- Запомни содержимое задачи для контекста

## Phase 2: Run Codex Review

### 2.1 Проверь доступность Codex

**ПЕРЕД запуском** убедись что codex доступен:

```bash
# Проверь что codex установлен
which codex || { echo "ERROR: codex not found"; exit 1; }
```

**Если codex не установлен или недоступен:**
- **КРИТИЧЕСКАЯ ОШИБКА** → сообщи пользователю
- **НЕ ПРОДОЛЖАЙ** workflow
- **НЕ ЗАМЕНЯЙ** codex своим собственным ревью

### 2.2 Запусти Codex CLI

Запусти Codex CLI для проверки git changes. Вывод перенаправляй во временный файл чтобы не засорять контекст.

```bash
# Создай временную директорию
REVIEW_DIR="/tmp/code-review-$(date +%s)"
mkdir -p "$REVIEW_DIR"

# Запусти codex review с gpt-5-codex и high reasoning effort (inline profile)
codex review \
  -c 'profiles.review.model="gpt-5-codex"' \
  -c 'profiles.review.model_reasoning_effort="high"' \
  -c 'profile="review"' \
  "
Ты выполняешь код-ревью для задачи {{task_ref}}.

## Твоя задача

1. Получи детали задачи через MCP md-task-mcp: tasks(project, number)
2. Проанализируй ТОЛЬКО незакоммиченные изменения (git diff, git status) на соответствие ТЗ
3. Запиши результаты в раздел Review задачи через update_task(project, number, review=...)

## Что проверять

1. **Соответствие ТЗ**: Все изменения соответствуют требованиям задачи
2. **Безопасность**: SQL injection, XSS, CSRF, hardcoded secrets, input validation
3. **Логика**: Ошибки в бизнес-логике, edge cases, race conditions
4. **Тесты**: Достаточность покрытия, корректность assertions, edge cases в тестах
5. **Code Quality**: Naming, DRY, SOLID, error handling

## Формат замечаний

Для КАЖДОГО замечания укажи:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **File**: путь к файлу
- **Line**: номер строки (если применимо)
- **Issue**: описание проблемы

НЕ ПИШИ suggestion — это задача разработчика.

## Пример формата Review

\`\`\`markdown
## Code Review - Iteration 1

### CRITICAL
1. **SQL Injection** - services/web/app/db/users.py:45
   Прямая интерполяция пользовательского ввода в SQL запрос

### HIGH
1. **Missing Input Validation** - services/web/app/routes/api.py:123
   Отсутствует валидация входных данных

### MEDIUM
1. **Error Handling** - services/processor/src/main.py:89
   Не обрабатывается исключение при потере соединения

### Summary
- CRITICAL: 1
- HIGH: 1
- MEDIUM: 1
- LOW: 0
\`\`\`

## Важно

- НЕ ИЗМЕНЯЙ КОД — только анализируй
- Результаты пиши в Review секцию задачи через md-task-mcp update_task
- Если нет замечаний — напиши 'NO ISSUES FOUND'
" 2>&1 > "$REVIEW_DIR/codex-output.log"

# Проверь exit code
CODEX_EXIT_CODE=$?
if [ $CODEX_EXIT_CODE -ne 0 ]; then
    echo "ERROR: codex exited with code $CODEX_EXIT_CODE"
    cat "$REVIEW_DIR/codex-output.log"
fi
```

### 2.3 Проверь результат выполнения

**ОБЯЗАТЕЛЬНО проверь:**
1. Exit code команды codex (должен быть 0)
2. Содержимое лог-файла на наличие ошибок

**Если codex завершился с ошибкой:**
- Прочитай лог из `$REVIEW_DIR/codex-output.log`
- **КРИТИЧЕСКАЯ ОШИБКА** → сообщи пользователю точную ошибку
- **НЕ ПРОДОЛЖАЙ** к Phase 3
- **НЕ ЗАМЕНЯЙ** codex своим собственным ревью

## Phase 3: Read Review from Task

После выполнения Codex:

1. **Получи обновлённую задачу** через `mcp__md-task-mcp__tasks(project, number)`

2. **ОБЯЗАТЕЛЬНО проверь наличие секции Review**:
   - Секция должна содержать результаты от Codex (формат "## Code Review - Iteration N")
   - Должен быть Summary с количеством issues

3. **Если секция Review отсутствует или пустая:**
   - Codex НЕ выполнил свою задачу
   - **КРИТИЧЕСКАЯ ОШИБКА** → сообщи пользователю
   - Прочитай лог `$REVIEW_DIR/codex-output.log` для диагностики
   - **НЕ ПРОДОЛЖАЙ** к Phase 4
   - **НЕ ЗАПИСЫВАЙ** своё собственное ревью вместо codex

4. **Категоризируй замечания** (только если Review есть):
   - CRITICAL/HIGH — исправить обязательно
   - MEDIUM — исправить если корректно
   - LOW — на усмотрение

## Phase 4: Handle Issues

Для каждого замечания определи:

### 4.1 Если замечание корректно
- Исправь код
- Добавь в Review пометку: `[claude] Fixed: <краткое описание исправления>`

### 4.2 Если замечание спорное или есть варианты
Используй `AskUserQuestion`:

```
Codex указал на проблему в файле X:
[описание замечания]

Варианты:
1. [Вариант A] — [описание]
2. [Вариант B] — [описание]
3. Замечание некорректно потому что [причина]

Какой вариант выбрать?
```

После ответа пользователя добавь в Review:
`[claude] User Decision: По замечанию X пользователь указал: <решение>`

### 4.3 Если замечание некорректно
Добавь в Review: `[claude] Declined: <причина почему замечание некорректно>`

## Phase 5: Re-Review (Iteration)

После исправлений запусти повторную проверку:

```bash
ITERATION=2
codex review \
  -c 'profiles.review.model="gpt-5-codex"' \
  -c 'profiles.review.model_reasoning_effort="high"' \
  -c 'profile="review"' \
  "
Это повторная проверка после исправлений (итерация $ITERATION) для задачи {{task_ref}}.

1. Получи текущий Review из задачи через md-task-mcp
2. Проверь ТОЛЬКО незакоммиченные изменения (git diff, git status) что предыдущие замечания исправлены
3. Проверь что исправления не внесли новых проблем
4. ДОПОЛНИ Review в задаче новыми замечаниями или статусом

Если всё исправлено — добавь в Review: '## Iteration $ITERATION: ALL ISSUES RESOLVED'
Если есть новые проблемы — добавь их в том же формате с заголовком '## Iteration $ITERATION'
" 2>&1 > "$REVIEW_DIR/codex-iteration-$ITERATION.log"
```

**Повторяй итерации** пока:
- Codex не напишет "ALL ISSUES RESOLVED"
- Или не останется только LOW замечания
- Максимум 3 итерации (после — спроси пользователя)

## Phase 6: Finalize Review

После завершения всех итераций добавь в Review финальный статус через `mcp__md-task-mcp__update_task`:

```markdown
## Final Review Status

[claude] Review completed after N iterations

### Stats
- Issues Found: X
- Issues Fixed: Y
- Issues Declined: Z

### User Decisions
- [Список решений пользователя]

### Status: APPROVED / APPROVED_WITH_NOTES / NEEDS_ATTENTION
```

## Error Handling

### Критические ошибки (СТОП)

| Ситуация | Действие |
|----------|----------|
| `which codex` не находит codex | СТОП → сообщить → ждать решения |
| codex завершился с ненулевым exit code | СТОП → показать лог → ждать решения |
| Review секция не появилась в задаче | СТОП → показать лог → ждать решения |
| md-task-mcp недоступен | СТОП → сообщить → ждать решения |

### ⚠️ ЗАПРЕЩЕНО

- **НЕ ЗАМЕНЯЙ** codex-ревью своим собственным анализом
- **НЕ ЗАПИСЫВАЙ** своё ревью в задачу если codex не сработал
- **НЕ ПРОДОЛЖАЙ** к следующим фазам при критической ошибке
- **НЕ ИГНОРИРУЙ** ошибки "codex not found" или ненулевой exit code

### Что делать при ошибке

1. Прочитай лог из временного файла (`$REVIEW_DIR/codex-output.log`)
2. Сообщи пользователю **точную ошибку** (не общие слова)
3. Предложи варианты:
   - Исправить проблему с codex и повторить
   - Отменить codex-review
4. **ЖДАТЬ УКАЗАНИЙ** — не принимай решение самостоятельно

## Checklist

- [ ] Задача получена через md-task-mcp
- [ ] **Codex доступен** (`which codex` успешно)
- [ ] Codex review запущен с правильным промптом
- [ ] **Exit code = 0** (codex завершился успешно)
- [ ] **Review секция появилась** в задаче (не пустая!)
- [ ] Все CRITICAL/HIGH обработаны
- [ ] Спорные моменты решены через AskUserQuestion
- [ ] Пометки [claude] добавлены для всех решений
- [ ] Повторный ревью подтвердил исправления
- [ ] Финальный статус записан в Review

---

Начни выполнение для задачи `{{task_ref}}`.
