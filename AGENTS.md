# AI Agent Configuration

This file contains configuration for the AI agent working with this project.

## Setup

1. Download **AGENTS.md** and **.env.agent** files from AI Agent settings
2. Place both files in the root of your project
3. Make sure `.env.agent` is added to `.gitignore`

## Authentication

> ⚠️ **CRITICAL:** 
> - API key is stored in `.env.agent` file
> - `.env.agent` file **MUST NEVER** be committed to git!
> - Before any commit, verify that `.env.agent` is in `.gitignore`
> - If `.env.agent` is not in `.gitignore` - add it there IMMEDIATELY!

Use `X-Agent-Key` header for authentication:

```
X-Agent-Key: <key from .env.agent>
```

Or Bearer token:

```
Authorization: Bearer <your_jwt_token>
```

## Project Settings

- **Project ID:** 69a85c35fde3be2f19e9e94d
- **API Base URL:** https://app.akm-advisor.com/api/v1/agent/69a85c35fde3be2f19e9e94d
- **Merge Strategy:** standard - Create MR, wait for review, merge after client approval in chat

### Kanban Workflow:
- **Pickup from:** backlog, todo (in priority order)
- **Move to 'In Progress':** in_progress
- **Move to 'Review':** review
- **Move to 'Done':** done
- **Strict mode:** NO - Can work on any assigned task

### Branches:
  - main [default, protected]: Production branch

## Custom Instructions
(No custom instructions set)

---

## API Reference

Base URL: `https://app.akm-advisor.com/api/v1/agent/69a85c35fde3be2f19e9e94d`

All requests require authentication via `X-Agent-Key` header.

### Project Context

#### GET /context
Get full project context including settings and statistics.

**Response:**
```json
{
  "id": "project_id",
  "key": "PROJ",
  "name": "Project Name",
  "description": "Project description",
  "agent_settings": { ... },
  "total_issues": 42,
  "open_issues": 15,
  "in_progress_issues": 5,
  "done_issues": 22,
  "team_members": [{ "id": "...", "name": "...", "email": "..." }],
  "statuses": ["backlog", "todo", "in_progress", "review", "testing", "done"]
}
```

---

### Issues

#### GET /issues
List all issues with optional filters.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status (backlog, todo, in_progress, review, testing, done) |
| type | string | Filter by type (task, bug, story, subtask) |
| sprint_id | string | Filter by sprint |
| epic_id | string | Filter by epic |
| assignee_id | string | Filter by assignee |
| include_done | boolean | Include completed issues (default: true) |
| limit | integer | Max results (default: 100, max: 500) |
| offset | integer | Skip results for pagination |

**Response:**
```json
{
  "items": [
    {
      "id": "issue_id",
      "key": "PROJ-123",
      "summary": "Issue title",
      "description": "Detailed description",
      "type": "task",
      "status": "todo",
      "priority": "high",
      "story_points": 3,
      "assignee_id": "user_id",
      "sprint_id": "sprint_id",
      "epic_id": "epic_id",
      "labels": ["frontend", "urgent"],
      "depends_on": ["PROJ-100"],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:20:00Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

#### POST /issues
Create a new issue.

**Request Body:**
```json
{
  "summary": "Issue title (required)",
  "description": "Detailed description",
  "type": "task",
  "priority": "medium",
  "story_points": 3,
  "epic_id": "epic_id",
  "sprint_id": "sprint_id",
  "assignee_id": "user_id",
  "labels": ["frontend"],
  "depends_on": ["PROJ-100"]
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| summary | string | ✅ | Issue title |
| description | string | | Detailed description (supports markdown) |
| type | string | | task, bug, story, subtask (default: task) |
| priority | string | | lowest, low, medium, high, highest (default: medium) |
| story_points | integer | | Estimation in story points |
| epic_id | string | | Parent epic ID |
| sprint_id | string | | Sprint to assign to |
| assignee_id | string | | User ID to assign |
| labels | array | | List of labels |
| depends_on | array | | List of issue keys this depends on |

#### GET /issues/{issue_id}
Get a single issue by ID.

#### PATCH /issues/{issue_id}
Update an existing issue. Only provided fields will be updated.

**Request Body:** Same fields as POST /issues (all optional)

#### POST /issues/{issue_id}/move
Move issue to a different status on the kanban board.

**Request Body:**
```json
{
  "status": "in_progress",
  "assignee_id": "user_id"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | ✅ | Target status |
| assignee_id | string | | Reassign to user (optional) |

---

### Comments

#### GET /issues/{issue_id}/comments
List all comments on an issue.

**Response:**
```json
{
  "items": [
    {
      "id": "comment_id",
      "content": "Comment text",
      "author_id": "user_id",
      "author_name": "John Doe",
      "is_internal": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### POST /issues/{issue_id}/comments
Add a comment to an issue.

**Request Body:**
```json
{
  "content": "Comment text (required)",
  "is_internal": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | ✅ | Comment text (supports markdown) |
| is_internal | boolean | | Internal note, not visible to clients (default: false) |

---

### Dependencies

#### POST /dependencies
Create a dependency between issues.

**Request Body:**
```json
{
  "from_issue_id": "issue_id_1",
  "to_issue_id": "issue_id_2",
  "type": "blocks"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| from_issue_id | string | ✅ | Source issue ID |
| to_issue_id | string | ✅ | Target issue ID |
| type | string | | blocks, is_blocked_by, relates_to, duplicates (default: blocks) |

#### DELETE /dependencies
Remove a dependency.

**Request Body:**
```json
{
  "from_issue_id": "issue_id_1",
  "to_issue_id": "issue_id_2"
}
```

---

### Sprints

#### GET /sprints
List all sprints in the project.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| active_only | boolean | Only return active sprints |

**Response:**
```json
{
  "items": [
    {
      "id": "sprint_id",
      "name": "Sprint 1",
      "goal": "Complete authentication",
      "start_date": "2024-01-15",
      "end_date": "2024-01-29",
      "status": "active",
      "total_points": 21,
      "completed_points": 13
    }
  ]
}
```

#### POST /sprints
Create a new sprint.

**Request Body:**
```json
{
  "name": "Sprint 1 (required)",
  "goal": "Sprint goal",
  "start_date": "2024-01-15",
  "end_date": "2024-01-29"
}
```

#### POST /sprints/{sprint_id}/add-issues
Add issues to a sprint.

**Request Body:**
```json
{
  "issue_ids": ["issue_id_1", "issue_id_2"]
}
```

---

### Epics

#### GET /epics
List all epics in the project.

**Response:**
```json
{
  "items": [
    {
      "id": "epic_id",
      "key": "PROJ-1",
      "summary": "Epic title",
      "description": "Epic description",
      "status": "in_progress",
      "total_issues": 10,
      "completed_issues": 4
    }
  ]
}
```

---

### Story Points

#### POST /issues/bulk-story-points
Update story points for multiple issues at once.

**Request Body:**
```json
{
  "updates": [
    { "issue_id": "id1", "story_points": 3 },
    { "issue_id": "id2", "story_points": 5 }
  ]
}
```

**Response:**
```json
{
  "updated": 2,
  "errors": []
}
```

---

### Git Integration

#### GET /mergeable-issues
Get issues ready to be merged (typically in review/testing status).

#### POST /issues/{issue_id}/create-branch
Create a feature branch for an issue.

**Request Body:**
```json
{
  "branch_name": "feature/PROJ-123-add-login"
}
```

If branch_name is not provided, it will be auto-generated from issue key and summary.

#### POST /issues/{issue_id}/record-merge
Record that a branch was merged for an issue.

**Request Body:**
```json
{
  "branch_name": "feature/PROJ-123-add-login",
  "merged_at": "2024-01-15T10:30:00Z",
  "commit_sha": "abc123"
}
```

---

## Workflow Example

```bash
# 1. Get project context
curl -H "X-Agent-Key: $AGENT_API_KEY" \
  "${AGENT_API_URL}/context"

# 2. Get issues to work on (from pickup columns)
curl -H "X-Agent-Key: $AGENT_API_KEY" \
  "${AGENT_API_URL}/issues?status=todo&limit=10"

# 3. Pick an issue and move to in_progress
curl -X POST -H "X-Agent-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}' \
  "${AGENT_API_URL}/issues/{issue_id}/move"

# 4. Add a comment about progress
curl -X POST -H "X-Agent-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "Started working on this issue"}' \
  "${AGENT_API_URL}/issues/{issue_id}/comments"

# 5. When done, move to review
curl -X POST -H "X-Agent-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "review"}' \
  "${AGENT_API_URL}/issues/{issue_id}/move"
```

---

## Error Handling

All errors return JSON with `detail` field:

```json
{
  "detail": "Error message"
}
```

**Common HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 401 | Not authenticated |
| 403 | Forbidden (no access) |
| 404 | Resource not found |
| 500 | Internal server error |
