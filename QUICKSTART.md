# 🤖 Multi-Agent System — Quick Start

## ⚡ 3 команды для начала работы

### В этом проекте (уже настроено)

```powershell
# 1. Добавить задачу
.\agent.ps1 -Task "Спроектировать API" -Roles Architect -Priority high

# 2. Запустить агента
.\agent.ps1 -AutoConnect -Role Architect

# 3. Проверить статус
.\agent.ps1 -Status
```

---

## 📦 В новом проекте

```powershell
# 1. Скопировать файлы из d:\!AiSite\toplivo
Copy-Item d:\!AiSite\toplivo\agent.ps1 C:\MyNewProject\
Copy-Item d:\!AiSite\toplivo\agent-init.ps1 C:\MyNewProject\
Copy-Item d:\!AiSite\toplivo\.agent\workflows C:\MyNewProject\.agent\ -Recurse

# 2. Инициализировать
cd C:\MyNewProject
.\agent-init.ps1

# 3. Готово! Использовать как обычно
.\agent.ps1 -Status
```

---

## 🎯 Основные команды

| Команда | Описание |
|---------|----------|
| `.\agent.ps1 -Status` | Показать статус системы |
| `.\agent.ps1 -AutoConnect -Role Architect` | Подключить агента |
| `.\agent.ps1 -Task "Задача" -Roles Architect,Designer -Priority high` | Добавить задачу |
| `.\agent.ps1 -SyncMemory` | Синхронизировать память |
| `.\agent.ps1 -Init` | Инициализировать проект |

---

## 🤖 Роли

| Роль | Когда использовать |
|------|-------------------|
| **Architect** | "спроектировать", "архитектура", "план", "ADR" |
| **Designer** | "дизайн", "UI", "UX", "CSS", "стиль" |
| **Coder** | "код", "реализовать", "функция", "баг" |
| **QA** | "тест", "проверка", "валидация", "review" |
| **MemoryKeeper** | "память", "контекст", "синхронизация" |

---

## 📡 Авто-подключение

Агенты подключаются **сами** при наличии:
1. Файла `.agent-signal.md` с приоритетом `high`/`urgent`
2. Задачи в `.agent/tasks/queue.json` со статусом `pending`

---

## 💾 Экономия токенов

- **Skill Router:** загружает только 5 нужных скиллов
- **Кэширование:** скиллы хранятся 1 час
- **Экономия:** до 90% токенов

---

## 📚 Документация

- `AGENT_SETUP.md` — полная инструкция
- `.agent/workflows/auto-connect.md` — авто-подключение
- `.agent/workflows/skill-router.md` — выбор скиллов

---

## ⚠️ Проблемы?

### "Не удается найти параметр"
Файл должен быть в кодировке UTF-8 BOM.

### "Нет доступных задач"
Добавьте задачу: `.\agent.ps1 -Task "Задача" -Roles Architect -Priority high`

---

**Готово!** Система работает в любом проекте на Windows PowerShell.
