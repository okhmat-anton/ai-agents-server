# Backend System Plan (AI Agents Server)

## 1. Технологии
- **Backend:** Python 3.11+ / FastAPI (async)
- **Frontend:** Vue 3 + Vuetify 3
- **Database:** PostgreSQL (основные данные) + Redis / Valkey (кэш, очереди, pub/sub)
- **Vector DB:** ChromaDB (память агентов, семантический поиск) — Apache 2.0
- **Embedding:** Ollama embeddings (nomic-embed-text, mxbai-embed-large и др.) — локально, бесплатно
- **Деплой:** Docker + Docker Compose
- **Real-time:** WebSocket (статусы агентов, логи, чат)
- **Аутентификация:** JWT (access + refresh tokens) + API Key (для VSCode / внешних клиентов)

---

## 2. Аутентификация и авторизация

### Login
- Дефолтный пользователь: `admin` / `admin123`
- JWT-токены: access (15 мин) + refresh (7 дней)
- При первом запуске автоматическое создание admin-пользователя

### API endpoints
```
POST   /api/auth/login          — логин, возвращает access + refresh tokens
POST   /api/auth/refresh        — обновление access token
POST   /api/auth/logout         — инвалидация refresh token
GET    /api/auth/me             — текущий пользователь
```

### API Key (для VSCode и внешних клиентов)
- Помимо JWT, поддерживается аутентификация через **API Key** (заголовок `X-API-Key`)
- API Key генерируется в Settings → API Keys
- Один пользователь может иметь несколько ключей (с описанием и датой последнего использования)
- API Key даёт полный доступ ко всем эндпоинтам (аналогично JWT)
- Можно отозвать ключ в любой момент

```
GET    /api/settings/api-keys          — список API ключей
POST   /api/settings/api-keys          — создать новый ключ { name, description? }
DELETE /api/settings/api-keys/{id}     — отозвать ключ
```

**Структура API Key:**
| Поле         | Тип      | Описание                          |
|-------------|----------|-----------------------------------|
| id          | UUID     | Уникальный идентификатор          |
| name        | string   | Название ключа (напр. "VSCode")   |
| key_hash    | string   | bcrypt-хеш ключа                 |
| key_prefix  | string   | Первые 8 символов (для отображения) |
| description | string?  | Описание                          |
| last_used_at| datetime?| Последнее использование           |
| created_at  | datetime | Дата создания                     |

> Полный ключ показывается **только один раз** при создании (потом хранится только хеш).

---

## 3. Settings (Настройки)

### 3.1 Смена пароля
```
PUT    /api/settings/password   — { old_password, new_password }
```

### 3.2 Модели (LLM провайдеры)
Управление подключениями к локальным LLM (Ollama, LM Studio, llama.cpp server и др. OpenAI-compatible серверы)

**Структура модели:**
| Поле         | Тип     | По умолчанию                | Описание                          |
|-------------|---------|----------------------------|-----------------------------------|
| id          | UUID    | auto                       | Уникальный идентификатор          |
| name        | string  | —                          | Название модели                   |
| provider    | enum    | "ollama"                   | ollama / openai_compatible / custom (только open-source / локальные) |
| base_url    | string  | http://localhost:11434     | URL API провайдера                |
| api_key     | string? | null                       | API ключ (для локальных серверов, если настроен) |
| is_active   | bool    | true                       | Активна ли модель                 |
| created_at  | datetime| auto                       | Дата создания                     |
| updated_at  | datetime| auto                       | Дата обновления                   |

**API endpoints:**
```
GET    /api/settings/models          — список моделей
POST   /api/settings/models          — создать модель
GET    /api/settings/models/{id}     — получить модель
PUT    /api/settings/models/{id}     — обновить модель
DELETE /api/settings/models/{id}     — удалить модель
POST   /api/settings/models/{id}/test — проверить подключение к модели
GET    /api/settings/models/{id}/available — список доступных моделей на провайдере (напр. ollama list)
```

### 3.3 Общие настройки системы
```
GET    /api/settings/general         — получить общие настройки
PUT    /api/settings/general         — обновить общие настройки
```
Включает: язык интерфейса, часовой пояс, уровень логирования, лимиты выполнения.

---

## 4. Агенты

### 4.1 Структура агента
| Поле           | Тип      | По умолчанию | Описание                                    |
|---------------|----------|-------------|---------------------------------------------|
| id            | UUID     | auto        | Уникальный идентификатор                     |
| name          | string   | —           | Имя агента                                   |
| description   | string?  | null        | Описание агента                              |
| model_id      | UUID     | —           | FK на модель из настроек                     |
| model_name    | string   | —           | Конкретная модель (напр. qwen2.5-coder:14b)  |
| system_prompt | text     | ""          | Системный промпт агента                      |
| status        | enum     | "idle"      | idle / running / paused / error / stopped    |
| **Параметры генерации:** |          |             |                                              |
| temperature   | float    | 0.7         | Температура генерации                        |
| top_p         | float    | 0.9         | Top-p (nucleus sampling)                     |
| top_k         | int      | 40          | Top-k sampling                               |
| max_tokens    | int      | 2048        | Макс. токенов в ответе                       |
| num_ctx       | int      | 32768       | Размер контекстного окна                     |
| repeat_penalty| float    | 1.1         | Штраф за повторения (1.0 = нет)              |
| num_predict   | int      | -1          | -1 = генерировать до конца                   |
| stop          | string[] | []          | Токены остановки (опционально)               |
| num_thread    | int      | 8           | Кол-во потоков CPU                           |
| num_gpu       | int      | 1           | Использование GPU (Metal на M1/M2)          |
| **Мета:**     |          |             |                                              |
| created_at    | datetime | auto        | Дата создания                                |
| updated_at    | datetime | auto        | Дата обновления                              |
| last_run_at   | datetime?| null        | Последний запуск                             |

### 4.2 API endpoints — Агенты
```
GET    /api/agents                   — список агентов (с пагинацией, фильтрами, сортировкой)
POST   /api/agents                   — создать агента
GET    /api/agents/{id}              — получить агента
PUT    /api/agents/{id}              — обновить агента
DELETE /api/agents/{id}              — удалить агента (с подтверждением на фронте)

POST   /api/agents/{id}/start       — запустить агента
POST   /api/agents/{id}/pause       — приостановить агента
POST   /api/agents/{id}/resume      — возобновить работу
POST   /api/agents/{id}/stop        — остановить агента

GET    /api/agents/{id}/stats        — статистика агента (задачи, токены, время работы)
POST   /api/agents/{id}/duplicate    — дублировать агента с настройками
```

### 4.3 Логи агента
```
GET    /api/agents/{id}/logs         — логи агента (пагинация, фильтр по уровню/дате)
DELETE /api/agents/{id}/logs         — очистить логи
WS     /ws/agents/{id}/logs          — real-time стрим логов через WebSocket
```

**Структура лог-записи:**
| Поле       | Тип      | Описание                                  |
|-----------|----------|-------------------------------------------|
| id        | UUID     | Уникальный идентификатор                   |
| agent_id  | UUID     | FK на агента                               |
| level     | enum     | debug / info / warning / error / critical  |
| message   | text     | Текст сообщения                            |
| metadata  | jsonb    | Доп. данные (task_id, tokens_used и т.д.)  |
| created_at| datetime | Временная метка                            |

---

## 5. Системные логи (System Logs)

Отдельная система логов для всего бэкенда (запуск/остановка системы, ошибки, подключения, действия пользователей и т.д.). Не привязаны к конкретному агенту.

### 5.1 Структура системного лога
| Поле       | Тип      | Описание                                       |
|-----------|----------|------------------------------------------------|
| id        | UUID     | Уникальный идентификатор                        |
| source    | enum     | system / auth / api / scheduler / engine        |
| level     | enum     | debug / info / warning / error / critical       |
| message   | text     | Текст сообщения                                 |
| metadata  | jsonb    | Доп. данные (user_id, ip, endpoint, error_trace)|
| created_at| datetime | Временная метка                                 |

### 5.2 API endpoints — Системные логи
```
GET    /api/system/logs              — системные логи (пагинация, фильтр: level, source, date_from, date_to, search)
GET    /api/system/logs/stream       — SSE-стрим системных логов (Server-Sent Events)
DELETE /api/system/logs              — очистить логи старше N дней { days: 30 }
GET    /api/system/health             — статус системы (uptime, DB, Redis, Ollama, ChromaDB)
GET    /api/system/stats              — общая статистика (кол-во агентов, задач, скилов, память)
```

### 5.3 WebSocket — Системные логи
```
WS  /ws/system/logs                  — real-time стрим системных логов
```

---

## 5. Задачи (Tasks)

Единая система задач — используется как для **Common Tasks** (общие), так и для **Agent Tasks** (привязаны к агенту). Один и тот же компонент на фронте, один и тот же API — разница только в наличии `agent_id`.

### 5.1 Структура задачи
| Поле            | Тип      | По умолчанию | Описание                                     |
|----------------|----------|-------------|----------------------------------------------|
| id             | UUID     | auto        | Уникальный идентификатор                      |
| agent_id       | UUID?    | null        | FK на агента (null = common task)             |
| title          | string   | —           | Название задачи                               |
| description    | text     | ""          | Подробное описание / промпт задачи            |
| type           | enum     | "one_time"  | one_time / recurring / cron                   |
| status         | enum     | "pending"   | pending / running / paused / completed / failed / cancelled |
| priority       | enum     | "normal"    | low / normal / high / critical                |
| schedule       | string?  | null        | Cron-выражение (для recurring/cron)           |
| next_run_at    | datetime?| null        | Следующий запуск (для cron задач)             |
| max_retries    | int      | 3           | Макс. кол-во повторных попыток при ошибке     |
| retry_count    | int      | 0           | Текущее кол-во повторов                       |
| timeout        | int      | 300         | Таймаут выполнения (секунды)                  |
| result         | jsonb?   | null        | Результат выполнения                          |
| error          | text?    | null        | Текст ошибки (при failure)                    |
| started_at     | datetime?| null        | Время начала выполнения                       |
| completed_at   | datetime?| null        | Время завершения                              |
| created_at     | datetime | auto        | Дата создания                                 |
| updated_at     | datetime | auto        | Дата обновления                               |

### 5.2 API endpoints — Common Tasks
```
GET    /api/tasks                    — список общих задач (agent_id = null)
POST   /api/tasks                    — создать общую задачу
GET    /api/tasks/{id}               — получить задачу
PUT    /api/tasks/{id}               — обновить задачу
DELETE /api/tasks/{id}               — удалить задачу (с подтверждением)

POST   /api/tasks/{id}/run           — запустить задачу
POST   /api/tasks/{id}/pause         — приостановить
POST   /api/tasks/{id}/resume        — возобновить
POST   /api/tasks/{id}/cancel        — отменить
```

### 5.3 API endpoints — Agent Tasks (тот же код, фильтр по agent_id)
```
GET    /api/agents/{agent_id}/tasks              — задачи конкретного агента
POST   /api/agents/{agent_id}/tasks              — создать задачу для агента
GET    /api/agents/{agent_id}/tasks/{task_id}    — получить задачу агента
PUT    /api/agents/{agent_id}/tasks/{task_id}    — обновить
DELETE /api/agents/{agent_id}/tasks/{task_id}    — удалить
POST   /api/agents/{agent_id}/tasks/{task_id}/run    — запустить
POST   /api/agents/{agent_id}/tasks/{task_id}/pause  — пауза
POST   /api/agents/{agent_id}/tasks/{task_id}/resume — возобновить
POST   /api/agents/{agent_id}/tasks/{task_id}/cancel — отменить
```

> **Реализация:** На бэкенде единый TaskService. Agent-эндпоинты просто добавляют фильтр `agent_id`. На фронте — один переиспользуемый компонент `TaskList` / `TaskForm`, которому передается `agentId` (опционально).

---

## 7. WebSocket — Real-time обновления

```
WS /ws/dashboard         — общие обновления (статусы агентов, задачи, уведомления)
WS /ws/agents/{id}/logs  — стрим логов конкретного агента
WS /ws/agents/{id}/chat  — чат с агентом (для интерактивных задач)
WS /ws/system/logs       — стрим системных логов
```

**Аутентификация WebSocket:**
- JWT token передаётся в query: `ws://host/ws/...?token=<jwt>`
- Или API Key: `ws://host/ws/...?api_key=<key>`
- VSCode-клиент подключается через API Key

**Формат сообщений (JSON):**
```json
{
  "type": "agent_status_changed | task_updated | log_entry | chat_message | error",
  "payload": { ... },
  "timestamp": "2026-03-04T12:00:00Z"
}
```

---

## 8. Agent Execution Engine (Движок выполнения)

### 7.1 Архитектура
- Каждый агент выполняется в отдельном **asyncio Task**
- Очередь задач через **Redis** (pub/sub + streams)
- Graceful shutdown: при остановке агент завершает текущий шаг задачи, сохраняет прогресс
- Изоляция: ошибка одного агента не влияет на других

### 7.2 Цикл работы агента
```
1. Получить задачу из очереди
2. Загрузить контекст (system_prompt + память + описание задачи)
3. Отправить запрос к LLM (через unified LLM interface)
4. Обработать ответ (parse, extract actions)
5. Выполнить действия (если есть tool calls / skills)
6. Записать лог + обновить статус задачи
7. Повторять шаги 3-6 до завершения задачи или stop-сигнала
8. Сохранить результат, обновить память
```

### 7.3 Unified LLM Interface
Единый интерфейс для работы с локальными провайдерами:
```python
class LLMProvider(Protocol):
    async def chat(self, messages: list[Message], params: GenerationParams) -> LLMResponse: ...
    async def stream(self, messages: list[Message], params: GenerationParams) -> AsyncIterator[str]: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def check_connection(self) -> bool: ...
    async def embeddings(self, text: str, model: str) -> list[float]: ...
```
Реализации:
- `OllamaProvider` — основной (Ollama API, локальные модели)
- `OpenAICompatibleProvider` — для LM Studio, llama.cpp server, text-generation-webui и др. серверов с OpenAI-совместимым API

> Все провайдеры работают только с локальными / self-hosted моделями. Платные облачные API (OpenAI, Anthropic и т.д.) не используются.

---

## 9. Память агентов (Memory System)

### 9.1 Short-term Memory (Краткосрочная)
- Хранится в Redis (TTL = время сессии)
- Последние N сообщений / шагов текущей задачи
- Контекстное окно для LLM

### 9.2 Long-term Memory (Долгосрочная)

**Хранилище:** ChromaDB (vector embeddings) + PostgreSQL (метаданные, теги, категории)
**Embeddings:** генерируются локально через Ollama (nomic-embed-text / mxbai-embed-large)

#### Структура записи памяти
| Поле           | Тип      | По умолчанию  | Описание                                        |
|---------------|----------|--------------|--------------------------------------------------|
| id            | UUID     | auto         | Уникальный идентификатор                          |
| agent_id      | UUID     | —            | FK на агента-владельца                            |
| type          | enum     | "fact"       | fact / summary / experience / note / hypothesis   |
| title         | string   | —            | Краткий заголовок записи                          |
| content       | text     | —            | Полное содержание                                 |
| source        | enum     | "agent"      | agent (агент решил сохранить) / user (добавил пользователь) / system (автосохранение) |
| importance    | float    | 0.5          | Важность 0.0–1.0 (агент оценивает при сохранении)|
| tags          | string[] | []           | Теги для быстрого поиска (напр. ["python", "api", "bug"]) |
| category      | enum     | "general"    | general / knowledge / task_result / error / skill / conversation |
| task_id       | UUID?    | null         | FK на задачу (если память связана с задачей)      |
| embedding_id  | string?  | null         | ID вектора в ChromaDB                             |
| access_count  | int      | 0            | Сколько раз запись была извлечена                  |
| last_accessed | datetime?| null         | Последний доступ к записи                         |
| is_pinned     | bool     | false        | Закреплена пользователем (не удаляется при compact)|
| created_at    | datetime | auto         | Дата создания                                     |
| updated_at    | datetime | auto         | Дата обновления                                   |

#### Как агент сохраняет в память
Агент **самостоятельно решает**, что стоит запомнить. В процессе выполнения задачи агент может вызвать скил `memory_store`:
```
1. Агент получает результат / узнаёт новый факт / делает вывод
2. Агент оценивает важность (importance) и выбирает тип (fact / experience / ...)
3. Агент назначает теги и категорию
4. Вызывается memory_store → запись сохраняется в PostgreSQL + embedding в ChromaDB
5. При извлечении: семантический поиск по ChromaDB + фильтр по тегам/категориям в PostgreSQL
```

Автосохранение (source = "system"):
- Результат каждой завершённой задачи (краткое саммари)
- Ошибки и как они были решены
- Новые навыки/подходы, которые агент применил впервые

#### Теги и категории
- **Теги** — произвольные строки, агент или пользователь может добавить любые
- **Категории** — фиксированный набор (general, knowledge, task_result, error, skill, conversation)
- Поиск по тегам и категориям: точное или частичное совпадение или пересечение нескольких тегов, фильтр по одной или нескольким

#### Компактизация памяти
Периодически (или по запросу) запускается процесс сжатия:
1. Записи с низким importance и давним last_accessed группируются
2. LLM генерирует саммари группы → одна запись типа "summary"
3. Оригиналы удаляются (кроме is_pinned)
4. Embedding пересчитывается для нового саммари

#### 9.2.1 Связи между записями памяти (Memory Links)

При глубокой обработке памяти агент устанавливает **типизированные связи** между записями. Это превращает плоский список записей в **граф знаний**, где можно найти фрагмент и получить все зависимости по типу связи.

**Структура связи (таблица `memory_links`):**
| Поле           | Тип      | Описание                                           |
|---------------|----------|----------------------------------------------------|
| id            | UUID     | Уникальный идентификатор связи                      |
| agent_id      | UUID     | FK на агента (для быстрой фильтрации)               |
| source_id     | UUID     | FK на запись-источник                                |
| target_id     | UUID     | FK на запись-цель                                    |
| relation_type | enum     | Тип связи (см. ниже)                                |
| strength      | float    | Сила связи 0.0–1.0 (насколько тесная зависимость)   |
| description   | string?  | Описание связи (почему агент установил эту связь)    |
| created_by    | enum     | agent / system / user — кто создал связь             |
| created_at    | datetime | Дата создания                                        |

**Типы связей (`relation_type`):**
| Тип               | Описание                                                  | Пример                                         |
|-------------------|-----------------------------------------------------------|-------------------------------------------------|
| `causes`          | A является причиной B                                     | ошибка → решение                                |
| `caused_by`       | A вызвано B (обратная к causes)                           | решение → ошибка                                |
| `depends_on`      | A зависит от B                                            | скил → библиотека                               |
| `related_to`      | A связано с B (общая тематика)                            | факт о Python → факт о FastAPI                  |
| `contradicts`     | A противоречит B                                          | гипотеза A ↔ гипотеза B                         |
| `supports`        | A подтверждает / подкрепляет B                            | эксперимент → гипотеза                          |
| `derived_from`    | A получено из B (обобщение, вывод)                        | summary → набор фактов                          |
| `part_of`         | A является частью B                                       | шаг решения → полное решение                    |
| `supersedes`      | A заменяет / обновляет B (новая версия знания)            | новый факт → старый факт                        |
| `example_of`      | A является примером B                                     | конкретный случай → общее правило               |
| `precedes`        | A предшествует B по времени / логике                      | шаг 1 → шаг 2                                   |
| `follows`         | A следует за B                                            | шаг 2 → шаг 1                                   |

**API endpoints — Связи памяти:**
```
GET    /api/agents/{id}/memory/{memory_id}/links              — все связи записи (входящие + исходящие)
GET    /api/agents/{id}/memory/{memory_id}/links?type=causes   — связи определённого типа
GET    /api/agents/{id}/memory/{memory_id}/graph               — граф зависимостей (рекурсивный обход, depth=1..5)
POST   /api/agents/{id}/memory/links                           — создать связь вручную { source_id, target_id, relation_type, strength?, description? }
DELETE /api/agents/{id}/memory/links/{link_id}                 — удалить связь
GET    /api/agents/{id}/memory/graph                            — полный граф памяти агента (визуализация)
GET    /api/agents/{id}/memory/graph?type=causes,depends_on     — граф только по определённым типам связей
```

**Ответ `/graph`:**
```json
{
  "nodes": [
    { "id": "mem_1", "title": "FastAPI async", "type": "fact", "importance": 0.8, "tags": ["python", "api"] }
  ],
  "edges": [
    { "id": "link_1", "source": "mem_1", "target": "mem_2", "relation_type": "depends_on", "strength": 0.9 }
  ]
}
```
Формат подходит для визуализации графа на фронте (напр. D3.js / vis-network).

### 9.3 API endpoints — Память агента

**Просмотр и навигация (для пользователя и VSCode):**
```
GET    /api/agents/{id}/memory                  — список записей (пагинация, сортировка по дате/важности/доступам)
GET    /api/agents/{id}/memory/{memory_id}      — одна запись целиком
GET    /api/agents/{id}/memory/stats             — статистика: кол-во записей по типам, категориям, топ-теги
GET    /api/agents/{id}/memory/tags              — список всех тегов агента с количеством записей
GET    /api/agents/{id}/memory/export            — экспорт памяти агента (JSON)
```

**Фильтрация:**
```
GET    /api/agents/{id}/memory?type=fact&category=knowledge        — фильтр по типу и категории
GET    /api/agents/{id}/memory?tags=python,api                      — фильтр по тегам (AND/OR)
GET    /api/agents/{id}/memory?source=agent&importance_min=0.7      — только важные записи агента
GET    /api/agents/{id}/memory?date_from=2026-01-01&date_to=2026-03-04 — по дате
GET    /api/agents/{id}/memory?search=текстовый поиск                — полнотекстовый поиск
```

**Семантический поиск:**
```
POST   /api/agents/{id}/memory/search           — семантический поиск { query, limit?, tags?, category?, importance_min? }
```
Возвращает записи, ранжированные по релевантности (cosine similarity по embedding'ам), с возможностью дополнительных фильтров.

**Управление:**
```
POST   /api/agents/{id}/memory                  — добавить запись вручную (source = "user")
PUT    /api/agents/{id}/memory/{memory_id}      — редактировать запись (content, tags, category, is_pinned)
DELETE /api/agents/{id}/memory/{memory_id}       — удалить запись
POST   /api/agents/{id}/memory/{memory_id}/pin   — закрепить запись (защита от compact)
POST   /api/agents/{id}/memory/{memory_id}/unpin — открепить
POST   /api/agents/{id}/memory/compact           — запустить компактизацию
POST   /api/agents/{id}/memory/deep-process       — запустить глубокую обработку (memory_deep_process)
POST   /api/agents/{id}/memory/import            — импорт памяти из JSON
DELETE /api/agents/{id}/memory/bulk               — массовое удаление { ids: [...] } или { older_than, importance_below }
```

---

## 10. Скилы агентов (Skills System)

Каждый агент может иметь набор **скилов** — модульных Python-функций, которые расширяют его возможности (работа с файлами, HTTP-запросы, парсинг, генерация кода и т.д.). Скилы можно **расшаривать** между агентами.

### 9.1 Структура скила
| Поле           | Тип      | По умолчанию | Описание                                      |
|---------------|----------|-------------|-----------------------------------------------|
| id            | UUID     | auto        | Уникальный идентификатор                       |
| name          | string   | —           | Уникальное имя скила (snake_case)              |
| display_name  | string   | —           | Человекочитаемое название                      |
| description   | text     | ""          | Описание: что делает, когда использовать       |
| category      | enum     | "general"   | general / web / files / code / data / custom   |
| version       | string   | "1.0.0"     | Версия скила (semver)                          |
| code          | text     | —           | Python-код скила                               |
| input_schema  | jsonb    | {}          | JSON Schema входных параметров                 |
| output_schema | jsonb    | {}          | JSON Schema результата                         |
| is_system     | bool     | false       | Системный скил (нельзя удалить/редактировать)  |
| is_shared     | bool     | false       | Доступен ли для добавления другим агентам      |
| author_agent_id| UUID?   | null        | Агент-автор (null = создан пользователем)      |
| created_at    | datetime | auto        | Дата создания                                  |
| updated_at    | datetime | auto        | Дата обновления                                |

### 9.2 Связь «Агент ↔ Скил» (Many-to-Many)
| Поле          | Тип      | Описание                                       |
|--------------|----------|-------------------------------------------------|
| agent_id     | UUID     | FK на агента                                    |
| skill_id     | UUID     | FK на скил                                      |
| is_enabled   | bool     | Включён ли скил для этого агента                |
| config       | jsonb?   | Индивидуальные настройки скила для агента        |
| added_at     | datetime | Когда скил был добавлен агенту                  |

> **Шаринг:** Скил создаётся один раз и хранится в общей таблице `skills`. Агенты подключают скилы через связующую таблицу `agent_skills`. Один скил может быть подключён к нескольким агентам. При шаринге скил не копируется — все агенты используют одну и ту же версию.

### 9.3 API endpoints — Общий каталог скилов
```
GET    /api/skills                       — каталог всех скилов (с фильтрами: category, is_shared, search)
POST   /api/skills                       — создать новый скил
GET    /api/skills/{id}                  — получить скил
PUT    /api/skills/{id}                  — обновить скил
DELETE /api/skills/{id}                  — удалить скил (если не используется агентами, или с force)
POST   /api/skills/{id}/test             — протестировать скил (запуск с тестовыми параметрами)
POST   /api/skills/{id}/duplicate        — дублировать скил
```

### 9.4 API endpoints — Скилы конкретного агента
```
GET    /api/agents/{agent_id}/skills             — скилы подключённые к агенту
POST   /api/agents/{agent_id}/skills             — подключить скил агенту { skill_id, config? }
DELETE /api/agents/{agent_id}/skills/{skill_id}  — отключить скил от агента
PUT    /api/agents/{agent_id}/skills/{skill_id}   — обновить настройки скила для агента (enable/disable, config)
```

### 9.5 API endpoints — Шаринг скилов
```
POST   /api/skills/{id}/share                    — расшарить скил (is_shared = true)
POST   /api/skills/{id}/unshare                  — убрать из шаринга
GET    /api/skills/shared                         — список всех расшаренных скилов (для подключения к другим агентам)
POST   /api/agents/{agent_id}/skills/from-shared  — подключить расшаренный скил к агенту { skill_id }
```

### 9.6 Системные скилы (встроенные)
Предустановленные скилы, доступные из коробки:

| Скил               | Описание                                         |
|-------------------|---------------------------------------------------|
| `web_fetch`       | HTTP GET/POST запросы к URL                       |
| `web_scrape`      | Парсинг HTML-страниц (BeautifulSoup)              |
| `file_read`       | Чтение файлов                                     |
| `file_write`      | Запись файлов                                     |
| `shell_exec`      | Выполнение shell-команд (sandbox)                 |
| `code_execute`    | Выполнение Python-кода (sandbox)                  |
| `json_parse`      | Парсинг и трансформация JSON                      |
| `text_summarize`  | Суммаризация текста через LLM                     |
| `memory_store`    | Сохранение информации в долгосрочную память        |
| `memory_search`   | Семантический поиск по памяти                     |
| `memory_deep_process` | Глубокая обработка памяти: анализ всех записей, установление связей между ними, построение графа знаний (см. 9.2.1) |

### 9.7 Выполнение скилов в Execution Engine
```
1. LLM решает, какой скил вызвать (на основе описания скилов в контексте)
2. Engine валидирует входные параметры по input_schema
3. Код скила выполняется в изолированном sandbox
4. Результат валидируется по output_schema
5. Результат возвращается в контекст LLM для следующего шага
6. Лог: запись вызова скила (agent_id, skill_id, input, output, duration)
```

### 9.8 Безопасность скилов
- Выполнение в **sandbox** (ограниченный набор модулей, таймаут, лимит памяти)
- Системные скилы нельзя удалить или изменить
- Пользовательские скилы проходят базовую валидацию (запрет опасных импортов: os.system, subprocess без sandbox и т.д.)
- Логирование всех вызовов скилов

---

## 11. Структура проекта (Backend)

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware
│   ├── config.py                # Настройки (Pydantic Settings)
│   ├── database.py              # Подключение к PostgreSQL, Redis
│   │
│   ├── api/                     # API роутеры
│   │   ├── auth.py
│   │   ├── settings.py
│   │   ├── agents.py
│   │   ├── tasks.py
│   │   ├── skills.py            # Скилы (каталог + агентские)
│   │   ├── logs.py              # Системные логи + логи агентов
│   │   ├── system.py            # Health, stats, system endpoints
│   │   ├── memory.py
│   │   └── websocket.py
│   │
│   ├── models/                  # SQLAlchemy / Pydantic модели
│   │   ├── user.py
│   │   ├── model.py             # LLM model config
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── skill.py             # Skill + AgentSkill (M2M)
│   │   ├── log.py
│   │   └── memory.py
│   │
│   ├── schemas/                 # Pydantic schemas (request/response)
│   │   ├── auth.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── skill.py
│   │   └── ...
│   │
│   ├── services/                # Бизнес-логика
│   │   ├── auth_service.py
│   │   ├── agent_service.py
│   │   ├── task_service.py
│   │   ├── skill_service.py     # CRUD скилов + шаринг
│   │   ├── skill_executor.py    # Sandbox-выполнение скилов
│   │   ├── memory_service.py
│   │   └── execution_engine.py
│   │
│   ├── llm/                     # LLM провайдеры (только open-source / локальные)
│   │   ├── base.py              # LLMProvider protocol
│   │   ├── ollama.py            # Ollama (основной)
│   │   └── openai_compatible.py # LM Studio, llama.cpp, text-gen-webui и др.
│   │
│   ├── core/                    # Утилиты, безопасность
│   │   ├── security.py          # JWT, hashing
│   │   ├── dependencies.py      # FastAPI dependencies
│   │   └── exceptions.py        # Custom exceptions
│   │
│   └── migrations/              # Alembic миграции
│       └── ...
│
├── tests/
│   ├── test_auth.py
│   ├── test_agents.py
│   ├── test_tasks.py
│   ├── test_skills.py
│   └── ...
│
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── alembic.ini
```

---

## 12. Docker Compose

```yaml
services:
  backend:       # FastAPI app (port 8000)
  frontend:      # Vue 3 app (port 3000) → proxy to backend
  postgres:      # PostgreSQL (port 5432)
  redis:         # Redis (port 6379)
  chromadb:      # Vector DB (port 8001) — open-source, Apache 2.0
```

**Makefile команды:**
```
make install   - first install. Download ollama. Ask do you want download model, ask which. Basic by default Qwen 2.5 coder 14B (Show memory tat it will need)
make run       — docker compose up -d --build
make stop      — docker compose down
make restart   — docker compose restart
make update    — git pull && docker compose up -d --build
make test      — docker compose exec backend pytest
make lint      — docker compose exec backend ruff check .
make logs      — docker compose logs -f backend
make migrate   — docker compose exec backend alembic upgrade head
```

---

## 13. Frontend — Структура страниц

| Страница             | Путь                        | Описание                                |
|---------------------|-----------------------------|-----------------------------------------|
| Login               | /login                      | Авторизация                             |
| Dashboard           | /                           | Обзор: статусы агентов, активные задачи |
| Agents List         | /agents                     | Список агентов + действия               |
| Agent Create/Edit   | /agents/new, /agents/:id    | Форма создания/редактирования           |
| Agent Detail        | /agents/:id/detail          | Статистика, логи, задачи агента         |
| Agent Logs          | /agents/:id/logs            | Real-time логи (WebSocket)              |
| Agent Tasks         | /agents/:id/tasks           | Задачи агента (переиспользуемый компонент) |
| Agent Skills        | /agents/:id/skills          | Скилы агента + подключение из каталога  |
| Skills Catalog      | /skills                     | Каталог всех скилов + CRUD              |
| Skill Create/Edit   | /skills/new, /skills/:id    | Форма создания/редактирования скила     |
| Common Tasks        | /tasks                      | Общие задачи (тот же компонент)         |
| Task Create/Edit    | /tasks/new, /tasks/:id      | Форма задачи                            |
| Settings            | /settings                   | Пароль + модели + API Keys + общие настройки |
| Settings — Models   | /settings/models            | CRUD моделей                            |
| Settings — API Keys | /settings/api-keys          | Управление API ключами (для VSCode)     |
| System Logs         | /system/logs                | Системные логи (real-time + фильтры)    |

---

## 14. VSCode Integration (Интеграция с VSCode)

Все AI-ассистенты в VSCode (Claude, Gemini, Copilot и др.) могут **полностью управлять системой** через REST API, используя API Key.

### 14.1 Что может VSCode-агент
- **Логи:** просмотр системных логов и логов любого агента в реальном времени (REST + WebSocket)
- **Агенты:** создавать, настраивать, запускать, останавливать агентов
- **Задачи:** создавать и управлять задачами (common + agent)
- **Скилы:** создавать скилы, подключать к агентам, шарить между агентами
- **Настройки:** управлять моделями, проверять подключения
- **Память:** просматривать и искать по памяти агентов
- **Мониторинг:** проверять health системы, получать статистику
- **Дебаг:** читать логи для диагностики проблем с агентами

### 14.2 Аутентификация из VSCode
```bash
# Все запросы через заголовок X-API-Key
curl -H "X-API-Key: ak_xxxxxxxxxxxxxxxxxxxx" http://localhost:8000/api/agents

# WebSocket с API Key
wscat -c "ws://localhost:8000/ws/system/logs?api_key=ak_xxxxxxxxxxxxxxxxxxxx"
```

### 14.3 Удобные эндпоинты для VSCode
Помимо стандартных API, есть эндпоинты оптимизированные для программного доступа:

```
GET    /api/system/health            — быстрая проверка: система жива?
GET    /api/system/stats             — сводка: агенты, задачи, скилы, ошибки
GET    /api/system/logs?level=error&limit=50  — последние 50 ошибок системы
GET    /api/agents/{id}/logs?level=error&limit=20 — последние ошибки агента
GET    /api/agents?status=running    — только запущенные агенты
GET    /api/tasks?status=failed      — только упавшие задачи
GET    /api/system/openapi.json      — OpenAPI schema для автоматической интеграции
```

> **Принцип:** Любое действие, доступное во Frontend, доступно и через API. VSCode-агент — это полноценный клиент системы.

---

## 15. Безопасность

- Все API-эндпоинты (кроме /auth/login) защищены JWT **или** API Key
- Два способа аутентификации: JWT (frontend) и API Key (VSCode / внешние клиенты)
- Пароли хранятся как bcrypt-хеши
- API ключи локальных LLM-серверов (если настроены) шифруются в БД (Fernet — open-source cryptography lib)
- Rate limiting на login (5 попыток / минута)
- CORS настроен на конкретные origins
- Валидация всех входных данных через Pydantic
- SQL injection protection через ORM (SQLAlchemy)

---

## 16. Очередь реализации (Приоритеты)

### Фаза 1 — MVP
1. Аутентификация (JWT login/logout + API Key)
2. CRUD моделей (Settings)
3. CRUD агентов
4. Базовый LLM интерфейс (Ollama)
5. CRUD задач (common + agent)
6. Системные логи + логи агентов (REST API)
7. Простой execution engine (один запрос — один ответ)
8. Docker Compose
9. OpenAPI schema (для VSCode интеграции)

### Фаза 2 — Core Features
1. WebSocket (real-time логи, статусы)
2. Система скилов (CRUD, системные скилы, подключение к агентам)
3. Расширенный execution engine (multi-step, tool calls, вызов скилов)
4. Шаринг скилов между агентами
5. Система памяти (short-term через Redis/Valkey)
6. Cron-задачи / scheduling
7. Статистика и метрики

### Фаза 3 — Advanced
1. Long-term memory + ChromaDB + Ollama embeddings
2. Skill system (модульные навыки)
3. OpenAI-compatible провайдер (LM Studio, llama.cpp, text-gen-webui)
4. Экспорт/импорт конфигов агентов
5. Уведомления и алерты

---

## 17. Open-source стек (все компоненты бесплатные)

| Компонент          | Решение                    | Лицензия       | Назначение                          |
|-------------------|---------------------------|----------------|-------------------------------------|
| Backend framework | FastAPI                   | MIT            | API сервер                          |
| Frontend          | Vue 3 + Vuetify 3         | MIT            | UI                                  |
| Database          | PostgreSQL                | PostgreSQL Lic | Основное хранилище                  |
| Cache / Queue     | Redis 7 / Valkey          | BSD / BSD      | Кэш, очереди, pub/sub              |
| Vector DB         | ChromaDB                  | Apache 2.0     | Память агентов, семантический поиск |
| LLM Runtime       | Ollama                    | MIT            | Запуск локальных моделей            |
| LLM Models        | Qwen, Llama, Mistral и др.| Open-source    | Языковые модели                     |
| Embeddings        | nomic-embed-text (Ollama) | Apache 2.0     | Генерация эмбеддингов локально      |
| ORM               | SQLAlchemy                | MIT            | Работа с БД                         |
| Migrations        | Alembic                   | MIT            | Миграции БД                         |
| Auth              | PyJWT + bcrypt            | MIT            | Аутентификация                      |
| Containerization  | Docker + Docker Compose   | Apache 2.0     | Деплой                              |
| Linting           | Ruff                      | MIT            | Линтинг и форматирование            |
| Testing           | Pytest                    | MIT            | Тестирование                        |

> **Принцип:** Никаких платных API или облачных сервисов. Всё работает локально / self-hosted.

