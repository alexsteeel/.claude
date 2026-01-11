# Claude Code Configuration

Конфигурация Claude Code: команды, хуки и скрипты для автоматизации разработки.

## Быстрый старт

```bash
# Планирование задач (интерактивно)
cd /path/to/project
~/.claude/scripts/ralph-plan.sh myproject 1 2 3

# Реализация задач (автономно)
WORKING_DIR=/path/to/project ~/.claude/scripts/ralph-implement.sh myproject 1 2 3
```

## Структура

```
~/.claude/
├── commands/           # Slash-команды (/command-name)
├── hooks/              # Хуки автоматизации workflow
├── scripts/            # Shell-скрипты для запуска loops
├── ARCHITECTURE.md     # Диаграммы работы скриптов
├── CLAUDE.md           # Техническая документация для Claude
└── README.md           # Этот файл
```

## Команды

### Основной workflow

| Команда | Описание |
|---------|----------|
| `/execute-python-task` | Полный цикл: планирование → одобрение → реализация → тесты |

### Ralph Wiggum (разделённый workflow)

| Команда | Описание |
|---------|----------|
| `/ralph-plan-task project#N` | Только планирование с участием человека |
| `/ralph-implement-python-task project#N` | Только реализация, полностью автономно |

**Зачем разделять?**
- Планирование требует обсуждения и уточнений
- Реализация может выполняться автономно пока вы заняты другим
- Можно запланировать пул задач, а потом запустить реализацию на ночь

### Ревью

| Команда | Описание |
|---------|----------|
| `/pr-review` | Комплексное ревью через 6 специализированных агентов |
| `/security-review` | Аудит безопасности |
| `/codex-review project#N` | Ревью через Codex CLI |
| `/python-linters` | Запуск ruff и djlint |

### Управление задачами

| Команда | Описание |
|---------|----------|
| `/create-tasks` | Создание задач в md-task-mcp |
| `/memorize-task` | Сохранение контекста задачи в память |

## Скрипты

### ralph-plan.sh — Планирование

```bash
# Запуск из директории проекта
cd /path/to/project
~/.claude/scripts/ralph-plan.sh <project> <task_numbers...>

# Пример
~/.claude/scripts/ralph-plan.sh myproject 1 2 3
```

- **Режим**: интерактивный (Claude в терминале)
- **Взаимодействие**: можно общаться с Claude, уточнять требования
- **Между задачами**: спрашивает "Continue to next task?"
- **Результат**: план записывается в задачу, статус → `work`

### ralph-implement.sh — Реализация

```bash
# Указать директорию проекта через WORKING_DIR
WORKING_DIR=/path/to/project ~/.claude/scripts/ralph-implement.sh <project> <task_numbers...>

# Примеры
WORKING_DIR=/workspaces/myapp ~/.claude/scripts/ralph-implement.sh myproject 1 2 3
WORKING_DIR=/workspaces/myapp MAX_BUDGET=10 ~/.claude/scripts/ralph-implement.sh myproject 1
```

- **Режим**: автономный (`--print`, без взаимодействия)
- **Взаимодействие**: нет, полностью автономно
- **Логи**: `~/.claude/logs/ralph-implement/`
- **При проблемах**: задача переводится в `hold` с описанием блокировки
- **Результат**: коммит создаётся автоматически, статус → `done`

## Workflow

### Типичный сценарий

```bash
# 1. Утром: планируем задачи интерактивно
cd /workspaces/myapp
~/.claude/scripts/ralph-plan.sh myproject 5 6 7

# 2. Днём: запускаем автономную реализацию
WORKING_DIR=/workspaces/myapp ~/.claude/scripts/ralph-implement.sh myproject 5 6 7

# 3. Вечером: проверяем результаты
# - Задачи в статусе "done" — готовы к ревью
# - Задачи в статусе "hold" — требуют внимания
```

### Статусы задач (md-task-mcp)

| Статус | Значение |
|--------|----------|
| `backlog` | Не начата |
| `work` | В работе (план готов) |
| `done` | Реализация завершена |
| `human approved` | Проверено человеком |
| `hold` | Заблокирована, требует внимания |

## Хуки

### check_workflow.py

Отслеживает `/execute-python-task`:
- Блокирует остановку до завершения обязательных фаз
- Разрешает остановку по "need feedback" или в Plan Mode

### check_workflow_ralph.py

Отслеживает `/ralph-implement-python-task`:
- Полностью автономный режим (без "need feedback")
- Отслеживает создание коммита
- Разрешает остановку только при завершении или `hold`

## Docker-контейнеры

Конфигурация синхронизируется в:
- `your-project-devcontainer-1`
- `your-project-devcontainer-2`

Пользователь в контейнерах: `claude`

```bash
# Синхронизация файла
docker cp ~/.claude/commands/file.md container:/home/claude/.claude/commands/
docker exec --user root container chown claude:claude /home/claude/.claude/commands/file.md
```
