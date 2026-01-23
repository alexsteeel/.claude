---
name: commit
description: Create a commit following repository style
---

Создай коммит для текущих изменений, соблюдая стиль репозитория.

## Workflow

1. **Анализ стиля коммитов**
   ```bash
   git log --oneline -10
   ```
   Определи:
   - Язык (English/Russian)
   - Формат (conventional commits, plain, etc.)
   - Стиль глаголов (imperative, past tense)

2. **Просмотр изменений**
   ```bash
   git status
   git diff --staged
   git diff
   ```

3. **Staging изменений**
   - Добавь релевантные файлы по имени
   - НЕ используй `git add -A` или `git add .`
   - Исключи sensitive файлы (.env, credentials)

4. **Создание коммита**
   - Сообщение в стиле репозитория
   - Используй HEREDOC для форматирования:
   ```bash
   git commit -m "$(cat <<'EOF'
   Commit message here.

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   EOF
   )"
   ```

## Стиль этого репозитория

На основе истории:
- **Язык**: English
- **Формат**: Plain (без префиксов feat:/fix:)
- **Глаголы**: Imperative (Add, Fix, Improve, Update, Refactor)
- **Длина**: Короткие, 50-72 символа

Примеры:
- `Add safety checks to ralph plan`
- `Improve error handling and logging in ralph`
- `Fix ralph review hang, add notify command`

## Результат

После коммита покажи:
```bash
git log --oneline -1
git status
```
