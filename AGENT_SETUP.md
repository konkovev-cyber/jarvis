# 🤖 Multi-Agent Orchestration System

Автоматическая система управления агентами для проектов. Агенты подключаются сами, берут задачи из очереди, координируют работу и синхронизируют память.

---

## 📦 Быстрый старт

### В новом проекте (2 команды)

```powershell
# 1. Инициализация
.\agent-init.ps1

# 2. Проверка
.\agent.ps1 -Status
```

### В этом проекте (уже настроено)

```powershell
# Запустить агента
.\agent.ps1 -AutoConnect -Role Architect

# Добавить задачу
.\agent.ps1 -Task "Добавить новую функцию" -Roles Architect,Designer -Priority high
```

---

## 📁 Структура файлов

```
project/
├── agent.ps1                    # Главный CLI скрипт
├── agent-init.ps1               # Скрипт инициализации (для новых проектов)
├── AGENT_SETUP.md               # Этот файл
├── .agent-signal.md             # Сигнал для агентов (триггер)
│
├── .agent/
│   ├── workflows/
│   │   ├── auto-connect.md      # Авто-подключение агентов
│   │   ├── skill-router.md      # Выбор и кэширование скиллов
│   │   └── multi-agent-orchestrate.md
│   ├── tasks/
│   │   ├── queue.json           # Очередь задач
│   │   ├── active.json          # Активные задачи
│   │   └── completed.json       # История
│   ├── context-cache/           # Кэш скиллов
│   ├── logs/                    # Логи
│   └── communication/           # Канал связи
│
└── .agent-memory/
    ├── state.md                 # Текущее состояние
    ├── knowledge_graph.json     # Семантическая связь
    └── skills_index.json        # Индекс скиллов
```

---

## 🚀 Установка в новый проект

### Шаг 1: Скопировать файлы

```powershell
# Из этого проекта (d:\!AiSite\toplivo) в новый
Copy-Item -Path "d:\!AiSite\toplivo\agent.ps1" -Destination "C:\NewProject\"
Copy-Item -Path "d:\!AiSite\toplivo\agent-init.ps1" -Destination "C:\NewProject\"
Copy-Item -Path "d:\!AiSite\toplivo\.agent\workflows" -Destination "C:\NewProject\.agent\" -Recurse
```

### Шаг 2: Инициализировать проект

```powershell
cd C:\NewProject
.\agent-init.ps1
```

### Шаг 3: Проверить

```powershell
.\agent.ps1 -Status
```

---

## 🎯 Использование

### Команды CLI

| Команда | Описание |
|---------|----------|
| `.\agent.ps1 -Status` | Показать статус системы |
| `.\agent.ps1 -AutoConnect -Role Architect` | Авто-подключение агента |
| `.\agent.ps1 -Task "Задача" -Roles Architect,Designer -Priority high` | Добавить задачу |
| `.\agent.ps1 -SyncMemory` | Синхронизировать память |
| `.\agent.ps1 -Orchestrate` | Запустить оркестрацию |

### Примеры

#### 1. Добавить задачу и запустить агента

```powershell
# Добавляем задачу
.\agent.ps1 -Task "Спроектировать API" -Roles Architect -Priority high

# Агент подключится автоматически
.\agent.ps1 -AutoConnect -Role Architect
```

#### 2. Несколько агентов работают вместе

```powershell
# Задача для нескольких ролей
.\agent.ps1 -Task "Создать страницу каталога" -Roles Architect,Designer,Coder -Priority urgent

# Подключаем агентов по очереди
.\agent.ps1 -AutoConnect -Role Architect   # Проектирование
.\agent.ps1 -AutoConnect -Role Designer    # UI/UX
.\agent.ps1 -AutoConnect -Role Coder       # Реализация
```

#### 3. Проверка статуса

```powershell
.\agent.ps1 -Status
```

**Вывод:**
```
========================================
   MULTI-AGENT ORCHESTRATION STATUS   
========================================

TASKS:
   Pending:   1
   Active:    2
   Completed: 5

ACTIVE AGENTS:
   [ARCH] agent-Architect-23: Architect - Design phase
   [COD]  agent-Coder-45: Coder - Implementation

FILES:
   Signal:  [OK] .agent-signal.md
   Queue:   [OK] .agent/tasks/queue.json
   Memory:  [OK] .agent-memory/state.md

========================================
```

---

## 🤖 Роли агентов

| Роль | Описание | Когда использовать |
|------|----------|-------------------|
| **Architect** | Проектирование, ADR, структура | "спроектировать", "архитектура", "план" |
| **Designer** | UI/UX, стили, темы | "дизайн", "UI", "CSS", "стиль" |
| **Coder** | Реализация, функции, баги | "код", "реализовать", "баг", "функция" |
| **QA** | Тесты, проверка | "тест", "проверка", "валидация" |
| **MemoryKeeper** | Синхронизация памяти | "память", "контекст", "синхронизация" |

---

## 📡 Авто-подключение

Агенты подключаются **автоматически** при обнаружении:

1. **Файл `.agent-signal.md`** с приоритетом `high` или `urgent`
2. **Задача в очереди** со статусом `pending`
3. **CLI команда** `-AutoConnect`

### Формат `.agent-signal.md`

```markdown
# Agent Signal

## Active Task
Описание задачи

## Required Roles
- Architect
- Designer
- Coder

## Priority
high
```

---

## 💾 Экономия токенов

### Skill Router

Умная загрузка скиллов — только нужные для задачи:

| Без оптимизации | С оптимизацией | Экономия |
|-----------------|----------------|----------|
| ~50,000 токенов | ~15,000 токенов | 70% |
| Все скиллы подряд | Топ-5 для роли | |

### Кэширование

Скиллы кэшируются в `.agent/context-cache/skill-presets.json`:
- **TTL:** 1 час
- **Повторное использование:** 0 токенов

---

## 🔧 Настройка

### Изменить путь к скиллам

В `agent.ps1` (строка ~50):

```powershell
$SkillsPath = "c:\Users\user\.tools\antigravity-awesome-skills"
```

### Изменить интервал опроса

В `.agent-signal.md`:

```json
{
  "pollInterval": 60000  // 60 секунд
}
```

### Добавить свою роль

В `agent.ps1`, функция `Get-AgentRole`:

```powershell
$keywords = @{
    "YourRole" = @("keyword1", "keyword2")
}
```

---

## 📊 Мониторинг

### Логи

Файл: `.agent/logs/agent.log`

```
[INFO] 2026-03-11 12:00:00 [CLI] Agent CLI started
[INFO] 2026-03-11 12:00:01 [CONNECT] === AGENT CONNECT ===
[SUCCESS] 2026-03-11 12:00:02 [CONNECT] Agent connected successfully!
```

### Статистика

В `.agent-memory/state.md`:
- Активные агенты
- Очередь задач
- Завершённые задачи

---

## ⚠️ Решение проблем

### Ошибка: "Не удается найти параметр -auto-connect"

**Причина:** Файл без UTF-8 BOM.

**Решение:**
```powershell
$bom = New-Object System.Text.UTF8Encoding $true
$text = [System.IO.File]::ReadAllText('agent.ps1')
[System.IO.File]::WriteAllText('agent.ps1', $text, $bom)
```

### Ошибка: "Нет доступных задач"

**Причина:** В очереди нет задач для указанной роли.

**Решение:**
```powershell
# Добавить задачу с нужной ролью
.\agent.ps1 -Task "Задача" -Roles Architect -Priority high
```

### Агенты не подключаются автоматически

**Проверка:**
1. Файл `.agent-signal.md` существует?
2. Приоритет `high` или `urgent`?
3. Задачи в `.agent/tasks/queue.json` есть?

---

## 📚 Дополнительные ресурсы

- `.agent/workflows/auto-connect.md` — детальное описание авто-подключения
- `.agent/workflows/skill-router.md` — выбор и кэширование скиллов
- `.agent/workflows/multi-agent-orchestrate.md` — координация агентов

---

## 🎯 Пример полного цикла

```powershell
# 1. Инициализация (в новом проекте)
.\agent-init.ps1

# 2. Добавление задачи
.\agent.ps1 -Task "Создать главную страницу" -Roles Architect,Designer,Coder -Priority high

# 3. Запуск агентов
.\agent.ps1 -AutoConnect -Role Architect   # Проектирование
.\agent.ps1 -AutoConnect -Role Designer    # Дизайн
.\agent.ps1 -AutoConnect -Role Coder       # Код

# 4. Проверка статуса
.\agent.ps1 -Status

# 5. Синхронизация памяти
.\agent.ps1 -SyncMemory
```

**Результат:**
- ✅ Задача создана
- ✅ Агенты подключились
- ✅ Задача выполнена
- ✅ Память синхронизирована

---

**Готово!** Система работает в любом проекте на Windows PowerShell.
