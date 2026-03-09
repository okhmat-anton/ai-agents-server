# Skills We Need

Analysis of existing skills and proposals for new ones.

## Existing Skills (32)

| # | Skill | Category | Purpose |
|---|-------|----------|---------|
| 1 | code_execute | code | Execute Python code in sandbox |
| 2 | shell_exec | code | Execute shell commands |
| 3 | project_run_code | code | Run Python file from a project |
| 4 | file_read | files | Read files from filesystem |
| 5 | file_write | files | Write files to filesystem |
| 6 | project_file_read | files | Read a file from a project |
| 7 | project_file_write | files | Write a file to a project |
| 8 | project_list_files | files | List all files in a project |
| 9 | json_parse | data | Parse/transform JSON |
| 10 | web_fetch | web | HTTP GET/POST requests |
| 11 | web_fetch_copy | web | Duplicate of web_fetch (remove?) |
| 12 | web_scrape | web | Parse HTML with CSS selectors |
| 13 | video_watch | web | Fetch video transcripts (YouTube, TikTok, etc.) |
| 14 | memory_store | memory | Save to ChromaDB vector store |
| 15 | memory_search | memory | Semantic search through memory |
| 16 | memory_deep_process | memory | Build knowledge graph from memory |
| 17 | recall_knowledge | memory | Search & aggregate learned knowledge |
| 18 | study_material | memory | Deep study of material with notes |
| 19 | text_summarize | general | Summarize text via LLM |
| 20 | fact_save | knowledge | Save facts/hypotheses |
| 21 | fact_read | knowledge | Read facts from KB |
| 22 | fact_extract | knowledge | Extract facts from text via LLM |
| 23 | event_save | events | Record events in timeline |
| 24 | event_read | events | Read events from timeline |
| 25 | creator_context | general | Get info about the creator/owner |
| 26 | sound_generate | audio | Text-to-Speech (OpenAI/MiniMax) |
| 27 | speech_recognize | audio | Speech-to-Text (Whisper) |
| 28 | project_context_build | project | Build full project context |
| 29 | task_context_build | project | Build full task context |
| 30 | project_task_comment | project | Add comment to task |
| 31 | project_update_task | project | Update task status/assignee |
| 32 | my_test_skill | custom | Test/template skill |

---

## Gap Analysis

### What's missing by area:

1. **Web Search** — agents can fetch URLs but cannot *search* the internet
2. **Messaging** — Telegram service exists in backend, but no skill to send messages proactively
3. **Image/Vision** — no ability to analyze images or generate them
4. **Git** — projects exist, but no git operations (clone, commit, diff, push)
5. **Data formats** — only JSON; no CSV, XML, YAML, PDF, Excel support
6. **Scheduling from skills** — can't create/schedule tasks or reminders from within a skill
7. **Notifications** — no way to notify the owner outside of chat
8. **Code intelligence** — can execute code, but can't review, search, or refactor it
9. **Math/Calculations** — no dedicated math engine
10. **Translation** — no language translation skill
11. **API integration** — no generic authenticated API caller

---

## Proposed New Skills

### Priority 1 — High Impact, Agents Need These Most

#### `web_search`
> **Category:** web | **Complexity:** medium
>
> Search the internet via Google/DuckDuckGo/SearXNG API. Returns titles, snippets, and URLs.
>
> **Input:** `query`, `engine` (google/duckduckgo/searxng), `limit` (default 10), `language`
>
> **Why:** Agents currently can fetch a known URL but cannot *discover* information. This is the single biggest gap — without search, agents are blind to the web.

#### `telegram_send`
> **Category:** messaging | **Complexity:** low
>
> Send a message to a Telegram chat/user via the existing Telegram service. Supports text, markdown, images, files.
>
> **Input:** `messenger_id`, `chat_id`, `text`, `parse_mode` (markdown/html), `file_path` (optional)
>
> **Why:** Telegram service already exists but agents can only *receive* messages. Proactive outbound messaging enables alerts, reports, status updates.

#### `notification_send`
> **Category:** general | **Complexity:** low
>
> Send a notification to the creator/owner via configured channel (Telegram, email, webhook, or in-app).
>
> **Input:** `title`, `message`, `priority` (low/normal/high/urgent), `channel` (auto/telegram/email/webhook)
>
> **Why:** Agents run tasks autonomously but have no way to alert the owner when something important happens (task finished, error occurred, decision needed).

#### `image_analyze`
> **Category:** ai | **Complexity:** medium
>
> Analyze an image using a vision-capable LLM (GPT-4V, LLaVA, etc.). Describe content, extract text (OCR), answer questions about the image.
>
> **Input:** `image_url` or `image_path`, `question` (optional), `model` (optional)
>
> **Why:** Agents receive images in Telegram but can't understand them. Vision is essential for multimodal agent capability.

#### `git_operations`
> **Category:** code | **Complexity:** medium
>
> Clone repos, create branches, commit, push, pull, diff, view log. Operate on project directories.
>
> **Input:** `operation` (clone/commit/push/pull/diff/log/branch/checkout/status), `project_slug`, `repo_url`, `branch`, `message`, `files`
>
> **Why:** Projects have file operations but no version control. Agents writing code need to commit and push their work.

#### `project_search_code`
> **Category:** code | **Complexity:** low
>
> Search through project files by text/regex. Like grep across the codebase.
>
> **Input:** `project_slug`, `query`, `is_regex` (default false), `file_pattern` (e.g. "*.py"), `max_results`
>
> **Why:** Agents can list and read files, but can't search for specific code patterns across a project. Essential for understanding larger codebases.

---

### Priority 2 — Very Useful, Fills Important Gaps

#### `image_generate`
> **Category:** ai | **Complexity:** medium
>
> Generate images via DALL-E 3, Stable Diffusion, or Flux API.
>
> **Input:** `prompt`, `provider` (openai/stability/flux), `size` (1024x1024), `style` (natural/vivid), `quality` (standard/hd)
>
> **Why:** Creative tasks, thumbnail generation, diagrams, social media content.

#### `translate`
> **Category:** general | **Complexity:** low
>
> Translate text between languages using LLM or DeepL/Google Translate API.
>
> **Input:** `text`, `from_language` (auto-detect), `to_language`, `engine` (llm/deepl/google)
>
> **Why:** Multilingual agents, translating research materials, communicating with users in different languages.

#### `csv_parse`
> **Category:** data | **Complexity:** low
>
> Parse, filter, aggregate, and transform CSV data. Convert to/from JSON.
>
> **Input:** `file_path` or `text`, `operation` (parse/filter/aggregate/convert), `columns`, `filter_expr`, `output_format` (json/csv/table)
>
> **Why:** Data analysis is common; CSV is the most universal data format. Agents can't work with spreadsheet data currently.

#### `pdf_read`
> **Category:** files | **Complexity:** low
>
> Extract text and metadata from PDF files. Supports multi-page, tables, OCR for scanned PDFs.
>
> **Input:** `file_path` or `url`, `pages` (all/range), `extract_tables` (bool), `ocr` (bool)
>
> **Why:** PDFs are everywhere — research papers, reports, contracts, documentation. Agents need to read them.

#### `email_send`
> **Category:** messaging | **Complexity:** medium
>
> Send emails via SMTP or API (SendGrid, Mailgun). Supports HTML, attachments.
>
> **Input:** `to`, `subject`, `body`, `html` (bool), `attachments` (file paths), `reply_to`
>
> **Why:** Email remains the primary business communication channel. Reports, alerts, outreach.

#### `schedule_reminder`
> **Category:** general | **Complexity:** medium
>
> Create a one-time or recurring reminder. Triggers a callback to the agent at the specified time.
>
> **Input:** `title`, `message`, `trigger_at` (datetime or cron), `recurring` (bool), `agent_id`
>
> **Why:** Agents can have scheduled tasks, but can't programmatically create reminders for themselves during a conversation.

---

### Priority 3 — Nice to Have, Advanced Features

#### `yaml_parse`
> **Category:** data | **Complexity:** low
>
> Parse, validate, and transform YAML. Convert to/from JSON.
>
> **Input:** `text` or `file_path`, `operation` (parse/validate/convert)

#### `xml_parse`
> **Category:** data | **Complexity:** low
>
> Parse XML, query with XPath, convert to JSON.
>
> **Input:** `text` or `file_path`, `xpath` (optional), `output_format`

#### `regex_extract`
> **Category:** data | **Complexity:** low
>
> Extract data from text using regex patterns. Named groups, multi-match, replace.
>
> **Input:** `text`, `pattern`, `operation` (extract/match/replace), `replacement`

#### `api_call`
> **Category:** web | **Complexity:** medium
>
> Generic REST API caller with auth support (API key, Bearer token, OAuth). Handles pagination.
>
> **Input:** `url`, `method`, `headers`, `body`, `auth_type`, `auth_credentials`, `pagination`
>
> **Why:** web_fetch is basic. A proper API caller handles auth, headers, retry, and pagination.

#### `math_calculate`
> **Category:** data | **Complexity:** low
>
> Evaluate mathematical expressions, unit conversions, statistics. Uses sympy/numpy.
>
> **Input:** `expression`, `operation` (eval/simplify/solve/statistics/convert), `data` (for stats)

#### `code_review`
> **Category:** code | **Complexity:** medium
>
> Review code for bugs, security issues, style, and suggest improvements using LLM.
>
> **Input:** `code` or `file_path`, `language`, `focus` (bugs/security/style/performance/all)

#### `docker_manage`
> **Category:** system | **Complexity:** medium
>
> Manage Docker containers — list, start, stop, logs, build images.
>
> **Input:** `operation` (list/start/stop/restart/logs/build/exec), `container`, `image`, `command`

#### `rss_read`
> **Category:** web | **Complexity:** low
>
> Parse RSS/Atom feeds. Return latest entries with titles, links, summaries, dates.
>
> **Input:** `url`, `limit` (default 20), `since` (datetime filter)

#### `whatsapp_send`
> **Category:** messaging | **Complexity:** medium
>
> Send WhatsApp messages via Business API or similar integration.
>
> **Input:** `phone_number`, `text`, `media_url`

#### `calendar_manage`
> **Category:** general | **Complexity:** medium
>
> Read/create/update calendar events via Google Calendar or CalDAV.
>
> **Input:** `operation` (list/create/update/delete), `title`, `start`, `end`, `description`

---

## Cleanup Notes

- **web_fetch_copy** is a duplicate of **web_fetch** — should be removed
- **my_test_skill** is a placeholder — can be removed or kept as template

---

## Implementation Priority Roadmap

```
Phase 1 (Critical):     web_search, telegram_send, notification_send
Phase 2 (Important):    image_analyze, git_operations, project_search_code
Phase 3 (Useful):       image_generate, translate, csv_parse, pdf_read
Phase 4 (Extended):     email_send, schedule_reminder, api_call, code_review
Phase 5 (Nice-to-have): yaml/xml/regex parsers, math, docker, rss, calendar
```
