# Threads Retrospective Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual, read-only command that imports every Threads post available to the current account, including post insights and comments, into one Markdown retrospective per post in the local Obsidian content library.

**Architecture:** Extend the existing `ThreadsApiClient` with normalized post and insight reads, then keep Markdown rendering/upsert logic in a separate retrospective module. A small runtime orchestrator handles per-post fault isolation and index generation, while the existing CLI supplies credentials and the destination directory. The content repository receives only schema documentation and generated Markdown; credentials and raw API payloads remain in the execution repository process.

**Tech Stack:** Python 3 standard library, `unittest`, existing `urllib`-based Threads client, Markdown with YAML-style front matter.

---

## File map

Execution repository `C:\jq\AI\Thread OS\Threads-bot system`:

- Modify `threads_bot_system/threads_api.py`: normalize complete post records and six supported post insight metrics.
- Create `threads_bot_system/retrospective_markdown.py`: render, locate, and update retrospective Markdown while preserving the manual section.
- Create `threads_bot_system/retrospective_runtime.py`: orchestrate full-history reads, per-post failures, atomic writes, and index generation.
- Modify `threads_bot_system/cli.py`: add the manual `import-retrospectives` command.
- Modify `tests/test_threads_api.py`: cover post pagination, field parsing, insight parsing, and missing metrics.
- Create `tests/test_retrospective_markdown.py`: cover rendering, stable upsert, filename rules, and manual-section preservation.
- Create `tests/test_retrospective_runtime.py`: cover all-post processing, partial failures, and index ordering.
- Modify `tests/test_cli.py`: cover command routing, default output directory, and JSON summary.

Content repository `D:\Obsidian\Threads os`:

- Modify `CONTENT_SCHEMA.md`: add the controlled `retrospective` type and fields.
- Create `content/retrospectives/README.md`: generated index header; the real import replaces its generated list.

### Task 1: Read complete posts and insights from Threads

**Files:**
- Modify: `threads_bot_system/threads_api.py`
- Modify: `tests/test_threads_api.py`

- [ ] **Step 1: Write failing post-pagination and insight tests**

Add tests that construct `ThreadsApiClient` with a fake `request_impl`, return two `/threads` pages with `id,text,timestamp,permalink`, and return an `/insights` payload containing explicit zero and non-zero values.

```python
def test_fetch_user_posts_pages_and_parses_complete_records(self) -> None:
    responses = iter([
        {"data": [{"id": "post-1", "text": "First", "timestamp": "2026-07-01T01:00:00Z", "permalink": "https://threads.net/post-1"}], "paging": {"cursors": {"after": "next"}}},
        {"data": [{"id": "post-2", "text": "Second", "timestamp": "2026-07-02T01:00:00Z", "permalink": "https://threads.net/post-2"}], "paging": {"cursors": {}}},
    ])
    client = ThreadsApiClient("user-1", "token-1", request_impl=json_responder(responses))
    posts = client.fetch_user_posts()
    self.assertEqual([post.post_id for post in posts], ["post-1", "post-2"])
    self.assertEqual(posts[0].text, "First")
    self.assertEqual(posts[1].permalink, "https://threads.net/post-2")

def test_fetch_post_insights_distinguishes_zero_from_missing(self) -> None:
    payload = {"data": [
        {"name": "views", "values": [{"value": 120}]},
        {"name": "likes", "values": [{"value": 0}]},
    ]}
    client = ThreadsApiClient("user-1", "token-1", request_impl=json_responder(iter([payload])))
    insights = client.fetch_post_insights("post-1")
    self.assertEqual(insights["views"], 120)
    self.assertEqual(insights["likes"], 0)
    self.assertIsNone(insights["shares"])
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```powershell
python -m unittest tests.test_threads_api -v
```

Expected: FAIL because `fetch_user_posts`, `fetch_post_insights`, and normalized post types do not exist.

- [ ] **Step 3: Add normalized post types and read methods**

Add these public types and methods to `threads_api.py`:

```python
POST_INSIGHT_METRICS = ("views", "likes", "replies", "reposts", "quotes", "shares")

@dataclass(frozen=True, slots=True)
class ThreadsPost:
    post_id: str
    text: str
    timestamp: str
    permalink: str | None

@dataclass(frozen=True, slots=True)
class ThreadsPostPage:
    posts: list[ThreadsPost]
    next_after: str | None

def fetch_user_posts(self, limit: int = 100) -> list[ThreadsPost]:
    posts: list[ThreadsPost] = []
    after: str | None = None
    while True:
        page = self.fetch_user_posts_page(limit=limit, after=after)
        posts.extend(page.posts)
        if not page.next_after:
            return posts
        after = page.next_after

def fetch_post_insights(self, post_id: str) -> dict[str, int | None]:
    params = urlencode({"metric": ",".join(POST_INSIGHT_METRICS), "access_token": self.access_token})
    payload = self._request_json("GET", f"{self.base_url}/{post_id}/insights?{params}")
    result: dict[str, int | None] = {name: None for name in POST_INSIGHT_METRICS}
    for item in payload.get("data", []):
        if not isinstance(item, dict) or item.get("name") not in result:
            continue
        values = item.get("values", [])
        if isinstance(values, list) and values and isinstance(values[0], dict):
            value = values[0].get("value")
            if isinstance(value, int) and not isinstance(value, bool):
                result[str(item["name"])] = value
    return result
```

Implement `fetch_user_posts_page()` with fields `id,text,timestamp,permalink`, cursor parsing identical to the existing media-page logic, and a `_parse_post()` helper that requires `id` and `timestamp` while allowing empty text and missing permalink. Keep `fetch_user_threads()` unchanged for reply monitoring compatibility.

- [ ] **Step 4: Run API tests**

Run:

```powershell
python -m unittest tests.test_threads_api -v
```

Expected: all `tests.test_threads_api` tests PASS, including existing publishing and reply tests.

- [ ] **Step 5: Commit the API read capability**

```powershell
git add threads_bot_system/threads_api.py tests/test_threads_api.py
git commit -m "Add Threads post and insight reads"
```

### Task 2: Render and safely update retrospective Markdown

**Files:**
- Create: `threads_bot_system/retrospective_markdown.py`
- Create: `tests/test_retrospective_markdown.py`

- [ ] **Step 1: Write failing renderer and preservation tests**

Define fixtures with a normalized post, insights, and comments. Assert `render_retrospective()` writes `不可用` for `None`, preserves integer zero, and `merge_manual_section()` returns the exact existing text from `## 人工复盘` onward.

```python
def test_render_uses_unavailable_for_missing_but_keeps_zero(self) -> None:
    text = render_retrospective(post(), {"views": 10, "likes": 0, "replies": None, "reposts": None, "quotes": None, "shares": None}, [], synced_at="2026-07-14T12:00:00+00:00")
    self.assertIn("- 点赞：0", text)
    self.assertIn("- 回复：不可用", text)

def test_merge_preserves_manual_section_verbatim(self) -> None:
    existing = "managed old\n## 人工复盘\n\n我的判断\n- 保留这一行\n"
    generated = "managed new\n## 人工复盘\n\n### 为什么有效或无效\n"
    merged = merge_manual_section(generated, existing)
    self.assertEqual(merged, "managed new\n## 人工复盘\n\n我的判断\n- 保留这一行\n")
```

- [ ] **Step 2: Run the focused module tests and confirm failure**

```powershell
python -m unittest tests.test_retrospective_markdown -v
```

Expected: FAIL because `retrospective_markdown` does not exist.

- [ ] **Step 3: Implement focused Markdown helpers**

Create:

```python
MANUAL_HEADING = "## 人工复盘"

def retrospective_id(post_id: str) -> str:
    return f"threads-retrospective-{post_id}"

def retrospective_filename(post: ThreadsPost) -> str:
    published = datetime.fromisoformat(post.timestamp.replace("Z", "+00:00"))
    return f"{published.date().isoformat()}-threads-{post.post_id}.md"

def merge_manual_section(generated: str, existing: str | None) -> str:
    if not existing or MANUAL_HEADING not in existing:
        return generated
    generated_prefix = generated.split(MANUAL_HEADING, 1)[0]
    existing_manual = existing[existing.index(MANUAL_HEADING):]
    return generated_prefix + existing_manual
```

Implement `render_retrospective(post, insights, comments, synced_at)` with the exact design front matter and headings. Escape YAML scalar values safely by serializing user-controlled front-matter strings as JSON strings, which YAML accepts. Sort comments by timestamp, falling back to empty string, then comment ID. Do not include access tokens or raw response data.

- [ ] **Step 4: Add stable lookup tests and implementation**

Test `find_existing_retrospective(root, post_id)` against a file whose filename differs but whose front matter contains `platform_post_id: post-1`. Implement a bounded scan of `root.glob("*.md")`, excluding `README.md`, matching only the front-matter line.

- [ ] **Step 5: Run Markdown tests**

```powershell
python -m unittest tests.test_retrospective_markdown -v
```

Expected: all retrospective Markdown tests PASS.

- [ ] **Step 6: Commit Markdown rendering**

```powershell
git add threads_bot_system/retrospective_markdown.py tests/test_retrospective_markdown.py
git commit -m "Render durable Threads retrospectives"
```

### Task 3: Orchestrate full import, atomic writes, and index generation

**Files:**
- Create: `threads_bot_system/retrospective_runtime.py`
- Create: `tests/test_retrospective_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Create a fake client with three posts where the second post raises from `fetch_post_insights()`. Assert all three posts are written, the second insight failure is reported, the second post shows all metrics as unavailable, comments are fetched for every post, and the index orders post three before post one.

```python
report = run_retrospective_import(fake_client, output_root, now=lambda: fixed_now)
self.assertEqual(report.discovered, 3)
self.assertEqual(report.written, 3)
self.assertEqual(report.failed, 1)
self.assertEqual(report.failures[0].post_id, "post-2")
self.assertEqual(report.failures[0].phase, "insights")
self.assertEqual(len(list(output_root.glob("*-threads-*.md"))), 3)
self.assertLess(index.index("post-3"), index.index("post-1"))
```

Also add a test where a pre-existing file contains handwritten text below `## 人工复盘`; after import, platform values change but the handwritten suffix remains byte-for-byte equal.

- [ ] **Step 2: Run runtime tests and confirm failure**

```powershell
python -m unittest tests.test_retrospective_runtime -v
```

Expected: FAIL because runtime types and `run_retrospective_import()` do not exist.

- [ ] **Step 3: Implement the report and per-post loop**

Create immutable result records:

```python
@dataclass(frozen=True, slots=True)
class RetrospectiveFailure:
    post_id: str
    phase: str
    error: str

@dataclass(frozen=True, slots=True)
class RetrospectiveImportReport:
    discovered: int
    written: int
    updated: int
    failed: int
    failures: list[RetrospectiveFailure]
```

Implement `run_retrospective_import(client, output_root, now=...)` so it creates `output_root`, fetches all posts once, and processes each stage independently. An insights exception records phase `insights`, substitutes all six metrics with `None`, and continues to comments and writing. A comments exception records phase `comments`, writes the post with an empty comment section, and continues. A write exception records phase `write` and leaves the previous target untouched. A basic post-list failure is fatal because no safe per-post unit exists. `failed` is the number of recorded stage failures, while `written` and `updated` count successfully persisted documents; therefore a post can contribute one stage failure and still be written.

- [ ] **Step 4: Implement atomic writes and generated index**

Write each finished document to `target.with_suffix(".md.tmp")`, then call `Path.replace(target)`. Remove any temporary file in a `finally` block. Build `README.md` only from files that exist after the loop, sort by parsed `published_at` descending, and include date, first non-empty body line truncated to 80 characters, six metric cells, local link, and permalink.

- [ ] **Step 5: Run runtime tests**

```powershell
python -m unittest tests.test_retrospective_runtime -v
```

Expected: all runtime tests PASS, including continuation after a per-post failure and exact manual-suffix preservation.

- [ ] **Step 6: Commit runtime orchestration**

```powershell
git add threads_bot_system/retrospective_runtime.py tests/test_retrospective_runtime.py
git commit -m "Import Threads retrospectives locally"
```

### Task 4: Add the manual CLI entry point

**Files:**
- Modify: `threads_bot_system/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write a failing CLI routing test**

Patch `_build_threads_client` and `run_retrospective_import`, invoke:

```python
exit_code = main(["import-retrospectives", "--output-root", str(output_root)])
```

Assert the output root reaches the runtime and stdout contains JSON keys `discovered`, `written`, `updated`, `failed`, and `failures`. Assert no Feishu or DeepSeek builder is called.

- [ ] **Step 2: Run the CLI test and confirm failure**

```powershell
python -m unittest tests.test_cli.CliTests.test_import_retrospectives_command_prints_summary -v
```

Expected: FAIL because argparse rejects `import-retrospectives`.

- [ ] **Step 3: Implement the CLI command**

Add:

```python
DEFAULT_RETROSPECTIVE_ROOT = Path(r"D:\Obsidian\Threads os\content\retrospectives")

retrospectives = subparsers.add_parser(
    "import-retrospectives",
    help="Import all available Threads posts into local retrospective Markdown",
)
retrospectives.add_argument(
    "--output-root",
    default=_env("THREADS_RETROSPECTIVE_ROOT", str(DEFAULT_RETROSPECTIVE_ROOT)),
)
```

Route the command to `_run_retrospective_import(Path(args.output_root))`. That function must build only the Threads client, call the runtime, print the report as UTF-8 JSON with `ensure_ascii=False`, and return `0` when the post list succeeds even if individual posts fail. A fatal list/API/configuration failure continues through the CLI's existing exception handler and returns `1`.

- [ ] **Step 4: Run CLI and full execution-repository tests**

```powershell
python -m unittest tests.test_cli -v
python -m unittest discover -s tests -v
```

Expected: all Python tests PASS. Existing reply and publish commands remain unchanged.

- [ ] **Step 5: Commit the entry point**

```powershell
git add threads_bot_system/cli.py tests/test_cli.py
git commit -m "Add manual retrospective import command"
```

### Task 5: Extend the content-library contract

**Files:**
- Modify: `D:\Obsidian\Threads os\CONTENT_SCHEMA.md`
- Create: `D:\Obsidian\Threads os\content\retrospectives\README.md`

- [ ] **Step 1: Add the retrospective schema**

Extend the common type list with `retrospective` and add a section requiring:

```markdown
## Retrospective Fields

- `type`: `retrospective`.
- `id`: `threads-retrospective-<platform_post_id>`.
- `platform`: `threads`.
- `platform_post_id`: required real Threads post ID and stable import key.
- `published_at`: timezone-aware ISO 8601 timestamp returned by Threads.
- `synced_at`: timezone-aware ISO 8601 timestamp of the last successful local refresh.
- `permalink`: optional Threads permalink.

The importer owns `原文`, `数据表现`, and `评论`. Content below `## 人工复盘` is user-owned and must be preserved byte-for-byte during refresh.
```

Do not alter existing statuses or fields for ideas, posts, comments, or replies.

- [ ] **Step 2: Add the generated index header**

Create:

```markdown
# Threads 内容复盘

本目录由本地手动导入命令维护。每篇历史帖子对应一份复盘文档；再次同步会刷新平台数据并保留 `## 人工复盘` 下的手写内容。

<!-- generated-retrospective-index -->
```

- [ ] **Step 3: Verify only intended content-library paths changed**

```powershell
git status --short
git diff -- CONTENT_SCHEMA.md content/retrospectives/README.md
```

Expected: the diff for this task contains only the schema extension and new index. Existing user-modified content and publish snapshots remain unstaged.

- [ ] **Step 4: Commit only the content-library contract files**

```powershell
git add CONTENT_SCHEMA.md content/retrospectives/README.md
git commit -m "Define Threads retrospective content"
```

### Task 6: Verify locally with fixtures, then perform the real full import

**Files:**
- Generated/updated: `D:\Obsidian\Threads os\content\retrospectives\README.md`
- Generated: `D:\Obsidian\Threads os\content\retrospectives\*-threads-*.md`

- [ ] **Step 1: Run all non-network verification**

```powershell
Set-Location 'C:\jq\AI\Thread OS\Threads-bot system'
python -m unittest discover -s tests -v
Set-Location 'D:\Obsidian\Threads os'
python -m unittest discover -s tests -v
```

Expected: both repositories' test suites PASS.

- [ ] **Step 2: Confirm the sensitive external-transfer boundary**

Before the next step, obtain explicit user confirmation that the existing `THREADS_ACCESS_TOKEN` may be sent to `https://graph.threads.net` to perform the requested read-only import. Do not print the token. This confirmation is required because the credential leaves the local machine as part of API authentication.

- [ ] **Step 3: Load the existing local Threads configuration without changing storage**

Use the existing authorized local credential file or current environment setup. Preserve plaintext storage and do not migrate, redact, rotate, commit, or copy credentials into the content library.

Verify only presence, not values:

```powershell
if (-not $env:THREADS_USER_ID) { throw 'THREADS_USER_ID is not loaded' }
if (-not $env:THREADS_ACCESS_TOKEN) { throw 'THREADS_ACCESS_TOKEN is not loaded' }
```

- [ ] **Step 4: Run the real read-only full import**

```powershell
Set-Location 'C:\jq\AI\Thread OS\Threads-bot system'
python -m threads_bot_system import-retrospectives --output-root 'D:\Obsidian\Threads os\content\retrospectives'
```

Expected: exit code `0`; JSON summary reports `discovered > 0`; `written + updated` equals the number of successfully processed posts; any partial failures include post ID and phase without a token.

- [ ] **Step 5: Verify generated files and preservation boundaries**

```powershell
$root = 'D:\Obsidian\Threads os\content\retrospectives'
$posts = Get-ChildItem -LiteralPath $root -Filter '*-threads-*.md' -File
if ($posts.Count -eq 0) { throw 'No retrospective files were generated' }
Get-Content -LiteralPath (Join-Path $root 'README.md') -TotalCount 30
git -C 'D:\Obsidian\Threads os' status --short
```

Expected: at least one post file and a populated index exist; pre-existing unrelated dirty paths remain unchanged; no credential, raw response, cache, or temporary file is present.

- [ ] **Step 6: Spot-check three records**

Choose the newest, oldest, and one post with replies. Compare ID, text, timestamp, permalink, available insight values, and comment count against the API results captured in memory during the same command, without saving raw payloads. Mark any field that the API did not return as `不可用`, not `0`.

- [ ] **Step 7: Run the import a second time to prove idempotence**

Add a harmless sentence below `## 人工复盘` in one generated document, rerun the command, and verify:

- the retrospective file count does not increase;
- the edited sentence remains byte-for-byte present;
- `synced_at` and platform-managed data refresh;
- no existing formal post or publish snapshot changes.

- [ ] **Step 8: Commit generated retrospectives only if the user explicitly requests it**

The full import writes local content but does not imply authorization to place retrieved content in Git history. Leave generated files uncommitted by default. If the user explicitly approves committing them, stage only `content/retrospectives/` and verify no credential is present before committing.
