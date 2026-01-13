# Claude Code Configuration

Конфигурация Claude Code: команды, хуки и CLI для автоматизации разработки.

## Быстрый старт

```bash
# Установка CLI
cd ~/.claude/cli
pip install -e .

# Планирование задач (интерактивно)
ralph plan myproject 1 2 3

# Реализация задач (автономно)
ralph implement myproject 1 2 3 -w /path/to/project

# Ревью кода
ralph review myproject#1

# Проверка API
ralph health -v
```

## Структура

```
~/.claude/
├── commands/           # Slash-команды (/command-name)
├── hooks/              # Хуки автоматизации workflow
├── cli/                # Ralph Python CLI
│   ├── ralph/          # Модули пакета
│   └── tests/          # pytest тесты
├── .env                # Конфигурация (git-ignored)
├── .env.example        # Шаблон конфигурации
├── CLAUDE.md           # Техническая документация для Claude
└── README.md           # Этот файл
```

## Ralph CLI

| Команда | Описание |
|---------|----------|
| `ralph plan` | Интерактивное планирование задач |
| `ralph implement` | Автономная реализация с recovery |
| `ralph review` | Запуск ревью в изолированных сессиях |
| `ralph health` | Проверка доступности API |

### Примеры

```bash
# Планирование нескольких задач
ralph plan myproject 1-5

# Реализация с ограничением бюджета
ralph implement myproject 1-5 -w /workspaces/myapp --max-budget 10

# Отключить автоматическое восстановление
ralph implement myproject 1 --no-recovery
```

## Команды Claude

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
| `/ralph-review-code project#N` | 5 агентов ревью параллельно |
| `/ralph-review-simplify project#N` | Упрощение кода |
| `/ralph-review-security project#N` | Аудит безопасности |
| `/ralph-review-codex project#N` | Ревью через Codex CLI |
| `/python-linters` | Запуск ruff и djlint |

### Управление задачами

| Команда | Описание |
|---------|----------|
| `/create-tasks` | Создание задач в md-task-mcp |
| `/memorize-task` | Сохранение контекста задачи в память |

## Workflow

### Типичный сценарий

```bash
# 1. Утром: планируем задачи интерактивно
ralph plan myproject 5 6 7

# 2. Днём: запускаем автономную реализацию
ralph implement myproject 5 6 7 -w /workspaces/myapp

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

## Конфигурация

Создайте `~/.claude/.env`:

```bash
# Telegram уведомления (опционально)
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="-1001234567890"

# Настройки восстановления
RECOVERY_ENABLED=true
RECOVERY_DELAYS="600,1200,1800"  # 10, 20, 30 минут
CONTEXT_OVERFLOW_MAX_RETRIES=2
```

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

Конфигурация синхронизируется в контейнеры.

```bash
# Синхронизация файла
docker cp ~/.claude/commands/file.md container:/home/claude/.claude/commands/
docker exec --user root container chown claude:claude /home/claude/.claude/commands/file.md
```
