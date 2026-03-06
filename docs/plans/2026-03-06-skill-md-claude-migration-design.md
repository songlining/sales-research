# SKILL.md Migration: OpenCode → Claude Code

> **Date**: 2026-03-06
> **Branch**: `claude`
> **Scope**: SKILL.md only (Howto.md and IMPLEMENTATION_SUMMARY.md deferred)
> **Approach**: Platform-Optimized Migration — keep all domain content, rewrite platform sections

## Decision Record

| Question | Decision |
|----------|----------|
| Browser tool | `mcp__chrome-devtools__*` (multi-tab parallel support, `select_page`, `evaluate_script`) |
| Parallelism | Background Agents via `Agent(run_in_background=true)` + `TaskOutput` |
| Scope | SKILL.md only |
| Domain content | Keep all as-is (~80% of file unchanged) |
| Migration approach | Platform-Optimized (Approach 2) |

## Sections to Change

### 1. Preflight Check (~lines 21-113)

**Changes:**
- `.mcp.json` check → verify chrome-devtools MCP is configured in Claude Code
- Missing config fix: `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222` (or create `.mcp.json` in project root which Claude Code also reads)
- "restart OpenCode" → "restart Claude Code session" (or note that Claude Code may hot-reload MCP)
- Remove OpenCode-specific reference in CLAUDE.md check header

### 2. Parallel Subagent Architecture (~lines 199-309)

**Complete rewrite.** Map OpenCode agent types to Claude Code:

| OpenCode | Claude Code |
|----------|------------|
| `task(subagent_type="librarian", run_in_background=true, load_skills=[])` | `Agent(subagent_type="general-purpose", run_in_background=true, description="...", prompt="...")` |
| `task(subagent_type="explore", run_in_background=true, load_skills=[])` | `Agent(subagent_type="Explore", run_in_background=true, description="...", prompt="...")` |
| `task(subagent_type="deep", ...)` — browser work | Main agent handles browser directly |
| `task(subagent_type="writing", ...)` | Main agent or `Agent(subagent_type="general-purpose")` |
| `background_output(task_id=...)` | `TaskOutput(task_id="<agent_id>", block=true, timeout=60000)` |

**Key Claude Code patterns:**
- All background agents must be dispatched in a **single message** for true parallelism
- Agent returns a `task_id` (agent ID) which is used with `TaskOutput` to collect results
- Claude Code automatically notifies when background agents complete — no polling
- Each agent gets fresh context; include all necessary info in the `prompt` parameter
- `description` is 3-5 words; `prompt` is the full task specification

**Delegation code example rewritten to Claude Code syntax.**

### 3. Browser Tool References (Throughout file, ~30 occurrences)

Global find-and-replace of tool name references:

| Current | Migrated |
|---------|----------|
| `chrome-devtools list_pages` | `mcp__chrome-devtools__list_pages` |
| `chrome-devtools select_page` | `mcp__chrome-devtools__select_page` |
| `chrome-devtools navigate_page` | `mcp__chrome-devtools__navigate_page` |
| `chrome-devtools take_snapshot` | `mcp__chrome-devtools__take_snapshot` |
| `chrome-devtools fill` | `mcp__chrome-devtools__fill` |
| `chrome-devtools click` | `mcp__chrome-devtools__click` |
| `chrome-devtools evaluate_script` | `mcp__chrome-devtools__evaluate_script` |
| `chrome-devtools wait_for` | `mcp__chrome-devtools__wait_for` |
| `chrome-devtools take_screenshot` | `mcp__chrome-devtools__take_screenshot` |
| `chrome-devtools new_page` | `mcp__chrome-devtools__new_page` |
| `chrome-devtools hover` | `mcp__chrome-devtools__hover` |

Also update inline code blocks and tables that reference these tools.

### 4. Web Research Tools (~line 1107-1110)

Replace:
```
websearch_web_search_exa — structured web search
webfetch — fetch specific URLs
google_search — broader web search with URL analysis
```

With:
```
WebSearch — built-in Claude Code web search
WebFetch — built-in Claude Code URL fetcher and analyzer
```

### 5. Error Handling (~lines 1481-1494)

- "restart OpenCode" → "restart Claude Code session"
- Add note about Claude Code tool permission prompts on first MCP use
- MCP connection error guidance updated for Claude Code

### 6. Chrome DevTools Commands Table (~lines 1520-1533)

Update table with Claude Code tool names (`mcp__chrome-devtools__*` prefix).

### 7. Misc References

- "OpenCode" → "Claude Code" throughout (~5-10 occurrences)
- "Sisyphus agent" reference → remove (OpenCode-specific)
- Example code blocks: update `task()` syntax to `Agent()` syntax

## Sections UNCHANGED (~80%)

- Frontmatter (name, description, triggers)
- Research Priority Order
- Sales Navigator search strategy (passes 1-5+)
- Profile extraction JavaScript (evaluate_script body stays the same)
- Deep-dive profile template
- Product Ownership Analysis
- Org Chart Reconstruction
- Mutual Connection & Introduction Path Analysis
- Phase 2: Web Research (all subsections — tech stack, business news, AI/ML, competition)
- All competitive intel sections (IBM Verify, OpenShift/Ansible, CyberArk, Venafi, PKI/CLM, OpenTofu/Pulumi/Bicep)
- Phase 3: Intelligence Brief (full output template)
- Phase 4: File to Vault
- Example Usage (update tool names in the narrative)
- Limitations
- Tips

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Missed tool reference (old name left behind) | Medium | Grep for `chrome-devtools ` (with space) after migration |
| Agent dispatch pattern wrong | Low | Test with a real research session |
| Browser detection flow broken | Low | Detection logic is the same, only tool names change |
| Domain content accidentally modified | Low | Diff against original to verify only platform sections changed |

## Verification Plan

1. `grep -c "opencode\|OpenCode" SKILL.md` → should be 0
2. `grep -c "chrome-devtools " SKILL.md` → should be 0 (no bare `chrome-devtools ` references without `mcp__` prefix)
3. `grep -c "background_output\|load_skills\|subagent_type=\"librarian\"\|subagent_type=\"explore\"\|subagent_type=\"deep\"" SKILL.md` → should be 0
4. `grep -c "websearch_web_search_exa\|google_search\|webfetch" SKILL.md` → should be 0
5. Diff shows ~80% unchanged lines
