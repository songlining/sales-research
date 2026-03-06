# SKILL.md Migration: OpenCode → Claude Code — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the sales-research SKILL.md from OpenCode platform to Claude Code, updating all tool references, parallelism patterns, and config while preserving 100% of the domain knowledge content.

**Architecture:** The SKILL.md is a single 1560-line markdown file with two layers: platform instructions (~20%) and domain knowledge (~80%). We surgically replace the platform layer while leaving domain content untouched. Changes are grouped into 7 logical tasks, each modifying a specific section of the file.

**Tech Stack:** Markdown, Claude Code Agent tool, Chrome DevTools MCP, WebSearch/WebFetch built-ins

---

### Task 1: Preflight Check Section — MCP Config Update

**Files:**
- Modify: `SKILL.md:57-113` (Preflight Check section, specifically the `.mcp.json` check and output directory)

**Step 1: Update the `.mcp.json` check (Section 3 of Preflight)**

Replace lines 57-84 (the `.mcp.json` check block) with Claude Code MCP configuration check:

````markdown
### 3. Chrome DevTools MCP Server

Verify the chrome-devtools MCP server is configured for Claude Code:

```bash
# Check if chrome-devtools MCP is already configured
claude mcp list 2>/dev/null | grep -i chrome
```

- ✅ Shows `chrome-devtools` entry → continue
- 🔧 Not listed → add it:
  ```bash
  claude mcp add chrome-devtools -s user -- npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222
  ```
  Alternatively, create or update `.mcp.json` in the project root (Claude Code reads this too):
  ```bash
  cat > .mcp.json << 'MCPEOF'
  {
    "mcpServers": {
      "chrome-devtools": {
        "command": "npx",
        "args": [
          "chrome-devtools-mcp@latest",
          "--browserUrl=http://127.0.0.1:9222"
        ]
      }
    }
  }
  MCPEOF
  ```
  Then tell the user:
  > I've configured the Chrome DevTools MCP server. **Please restart your Claude Code session** so it picks up the new MCP server, then repeat your request.
  **Stop here** — the MCP server won't load until Claude Code restarts.
````

**Step 2: Update the CLAUDE.md check header (Section 5)**

Change line 98 from:
```
### 5. CLAUDE.md (user context — optional but recommended)
```
To:
```
### 5. CLAUDE.md (user context — Claude Code reads this automatically)
```

**Step 3: Verify changes**

Run: `grep -n "opencode\|OpenCode\|\.mcp\.json" SKILL.md | head -20`
Expected: No more "OpenCode" references in the preflight section. `.mcp.json` only appears as a fallback option.

**Step 4: Commit**

```bash
git add SKILL.md
git commit -m "migrate: update preflight check for Claude Code MCP config"
```

---

### Task 2: Parallel Subagent Architecture — Complete Rewrite

**Files:**
- Modify: `SKILL.md:199-309` (Parallel Subagent Architecture section)

**Step 1: Replace the Agent Roles table**

Replace lines 213-219 (the agent roles table) with:

```markdown
| Agent | Type | Responsibility | Browser Needed? |
|-------|------|---------------|----------------|
| **Main Agent (you)** | Orchestrator | Sales Navigator search, profile extraction, deep-dives via browser. Coordinates all work. | **YES** — exclusive browser access |
| **Web Research Agent(s)** | `Agent(subagent_type="general-purpose", run_in_background=true)` | Company tech stack, news, job postings, press releases, AI/ML strategy, competitive landscape | No |
| **Vault Explorer Agent** | `Agent(subagent_type="Explore", run_in_background=true)` | Check existing customer data in local files (CLAUDE.md, HashiCorp/by-customer/) | No |
```

**Step 2: Replace the "How to Delegate" section and example code**

Replace lines 249-295 (the delegation section with TypeScript-style `task()` calls) with:

````markdown
### How to Delegate

**The orchestrating agent (you) should:**

1. **Fire web research agents IMMEDIATELY** after getting criteria — don't wait for Sales Navigator
2. **Dispatch ALL background agents in a SINGLE message** — Claude Code runs them in true parallel only when sent together
3. **Start Sales Navigator browsing yourself** — you have exclusive browser access
4. **Collect web research results** as they complete — use `TaskOutput` to retrieve results by agent ID
5. **Write to brief incrementally** — update the brief file after each deep-dive, don't batch

**Example delegation pattern:**

Dispatch ALL of these in a single message (critical for parallelism):

```
Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Research [Company] tech stack",
  prompt="[CONTEXT]: Researching [Company] for sales engagement across the HashiCorp portfolio (Terraform, Vault, Packer, Boundary, Consul, Nomad, Vault Radar, Waypoint). Use WebSearch and WebFetch to find: cloud provider(s) and migration status, infrastructure tooling (IaC, CI/CD, observability), containerization/Kubernetes adoption, managed service providers. Return findings as structured markdown with evidence sources."
)

Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Find [Company] job postings",
  prompt="[CONTEXT]: Looking for evidence of HashiCorp tool usage at [Company]. Use WebSearch to find job postings mentioning: Terraform, Vault, Packer, Consul, Nomad, Boundary, Waypoint, Vault Radar, HCP (HashiCorp Cloud Platform). Also search for competitor tools: CyberArk, Pulumi, OpenTofu, Venafi. Return structured findings with job posting URLs."
)

Agent(
  subagent_type="Explore",
  run_in_background=True,
  description="Check existing customer data",
  prompt="[CONTEXT]: Check for existing intel on [Company]. Read CLAUDE.md for customer table entries. Check HashiCorp/by-customer/[Company]/ for prior research briefs. Return: existing product usage, prior contacts found, any stale data that needs refresh."
)

Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Research [Company] recent news",
  prompt="[CONTEXT]: Looking for recent press, conference talks, blog posts from [Company] engineers. Use WebSearch to find: recent earnings/financial performance, executive changes, layoffs/hiring surges, regulatory actions, data breaches, M&A activity, product launches, partnerships. Classify each as POSITIVE/NEGATIVE/NEUTRAL. Focus on last 6 months. Return structured markdown."
)

Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Research [Company] good/bad news",
  prompt="[CONTEXT]: Researching recent media coverage for [Company] to identify positive and negative business news. Use WebSearch across: mainstream financial media (AFR, Bloomberg, Reuters, CNBC), industry press (iTnews, ZDNet, CRN, The Register), social media sentiment (Reddit, HackerNews). Classify each finding as POSITIVE, NEGATIVE, or NEUTRAL with brief impact assessment. Focus on last 6 months but flag major events in past 12 months."
)

Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Research [Company] AI/ML strategy",
  prompt="[CONTEXT]: Researching [Company] AI/ML maturity for HashiCorp sales positioning. Use WebSearch to find: AI/ML platform investments (SageMaker, Vertex AI, Databricks, MLflow), LLM provider usage (OpenAI, Anthropic, Azure OpenAI, Bedrock), agentic AI adoption, GPU infrastructure, AI governance policies, AI-related hires and job postings. Classify maturity as Exploring/Building/Scaling/Transforming. Map findings to HashiCorp products."
)

Agent(
  subagent_type="general-purpose",
  run_in_background=True,
  description="Research [Company] competitive landscape",
  prompt="[CONTEXT]: Researching what competitor products [Company] uses that overlap with HashiCorp. Use WebSearch to find evidence of: CyberArk/Delinea/BeyondTrust (Vault competitors), Venafi/AppViewX/Keyfactor (Vault PKI competitors), Pulumi/OpenTofu/Bicep/CloudFormation (Terraform competitors), Teleport/Zscaler ZPA (Boundary competitors), Istio/Linkerd (Consul competitors). Check job postings, conference talks, blog posts, case studies. Return structured findings."
)
```

**Collecting results:**

After dispatching background agents, start Sales Navigator browsing immediately. When you need results later:

```
# Each Agent call returns a task_id (agent ID). Use it to collect results:
TaskOutput(task_id="<agent_id_from_tech_stack_agent>", block=true, timeout=120000)
TaskOutput(task_id="<agent_id_from_job_postings_agent>", block=true, timeout=120000)
# ... etc for each agent

# Claude Code automatically notifies you when background agents complete.
# You do NOT need to poll — just call TaskOutput when you're ready to use the results.
```
````

**Step 3: Update "Constraints on Parallelism"**

Replace lines 299-304 with:

```markdown
### Constraints on Parallelism

- **Only the MAIN agent can use the browser.** Background agents do NOT have browser access — MCP tools are only available to the orchestrating agent.
- **All background agents must be dispatched in a SINGLE message** for true parallelism. If sent in separate messages, they run sequentially.
- **Web research agents are cheap and fast** — fire 5-7 in parallel without hesitation.
- **Each background agent starts with fresh context** — include ALL necessary information in the `prompt` parameter. They don't see prior conversation history.
- **Brief updates must be serialized** — only the main agent writes to the brief file. Background agents return their findings as text, and the orchestrator integrates them.
- **Rate limit Sales Navigator** — even with parallel web research, the browser agent must still wait 2-3s between Sales Navigator actions.
```

**Step 4: Verify changes**

Run: `grep -n "task(subagent_type\|background_output\|load_skills\|librarian\|Sisyphus" SKILL.md`
Expected: 0 matches (all OpenCode patterns replaced)

**Step 5: Commit**

```bash
git add SKILL.md
git commit -m "migrate: rewrite parallel subagent architecture for Claude Code Agent tool"
```

---

### Task 3: Browser Tool Name Updates — Global Replace

**Files:**
- Modify: `SKILL.md` (throughout, ~30 occurrences)

**Step 1: Replace all inline tool references**

These are the tool references in explanatory text and code blocks. Replace each pattern:

| Find | Replace |
|------|---------|
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

**IMPORTANT:** Only replace references in the pattern `chrome-devtools <tool_name>` (with a space). Do NOT replace occurrences of `chrome-devtools` when it refers to the MCP server name (e.g., in config blocks, the string `"chrome-devtools"` as a server name stays as-is).

**Step 2: Update the Chrome DevTools Commands table (lines 1520-1533)**

Replace the table:

```markdown
## Chrome DevTools Commands Used

| Command | Purpose |
|---------|---------|
| `mcp__chrome-devtools__list_pages` | Detect existing browser session, list open pages |
| `mcp__chrome-devtools__select_page` | Switch to Sales Navigator tab |
| `mcp__chrome-devtools__navigate_page` | Go to Sales Navigator URL |
| `mcp__chrome-devtools__take_snapshot` | Discover page structure (always before interacting) |
| `mcp__chrome-devtools__fill` | Type into filter typeaheads and input fields |
| `mcp__chrome-devtools__click` | Click filters, dropdowns, pagination, profile links |
| `mcp__chrome-devtools__evaluate_script` | Extract structured profile data from DOM via JavaScript |
| `mcp__chrome-devtools__wait_for` | Wait for page/results to load (text-based) |
| `mcp__chrome-devtools__take_screenshot` | Debug when DOM is unrecognizable — visual fallback |
| `mcp__chrome-devtools__new_page` | Open new tab for parallel browsing |
| `mcp__chrome-devtools__hover` | Hover to reveal tooltips and hidden elements |
```

**Step 3: Verify no old references remain**

Run: `grep -n "chrome-devtools " SKILL.md | grep -v "mcp__chrome-devtools__\|\"chrome-devtools\"\|chrome-devtools-mcp\|chrome-devtools MCP"`
Expected: 0 matches (all bare `chrome-devtools <tool>` replaced, but config references like `"chrome-devtools"` server name preserved)

**Step 4: Commit**

```bash
git add SKILL.md
git commit -m "migrate: update all browser tool references to mcp__chrome-devtools__* format"
```

---

### Task 4: Web Research Tool References

**Files:**
- Modify: `SKILL.md:1107-1110` (web research tools section)

**Step 1: Replace the web research tools block**

Replace lines 1107-1110:

```markdown
Use these tools for web research:
- `websearch_web_search_exa` — structured web search
- `webfetch` — fetch specific URLs
- `google_search` — broader web search with URL analysis
```

With:

```markdown
Use these built-in Claude Code tools for web research:
- `WebSearch` — web search with up-to-date results (built into Claude Code, no MCP needed)
- `WebFetch` — fetch and analyze content from specific URLs (built into Claude Code, no MCP needed)
```

**Step 2: Check for other occurrences of old tool names**

Run: `grep -n "websearch_web_search_exa\|google_search\|webfetch" SKILL.md`
Expected: 0 matches

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "migrate: update web research tools to Claude Code built-ins"
```

---

### Task 5: Error Handling Updates

**Files:**
- Modify: `SKILL.md:1481-1494` (Error Handling table)

**Step 1: Update the error handling table**

Replace the row about MCP and add a Claude Code-specific row:

Find:
```
| No browser detected by MCP | Launch debug Chrome automatically via bash (see Browser Detection section) |
```
Replace with:
```
| No browser detected by MCP | Launch debug Chrome automatically via bash (see Browser Detection section). If `mcp__chrome-devtools__list_pages` returns an error, the MCP server may not be connected — check `claude mcp list` and restart if needed. |
```

Find:
```
| Debug Chrome not starting | Tell user to close all Chrome windows, then try again |
```
Replace with:
```
| Debug Chrome not starting | Tell user to close all Chrome windows, then try again |
| MCP tool permission prompt | Claude Code may ask the user to approve MCP tool usage on first invocation. This is normal — approve and continue. |
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "migrate: update error handling for Claude Code MCP behavior"
```

---

### Task 6: Remaining OpenCode References — Global Cleanup

**Files:**
- Modify: `SKILL.md` (scattered references)

**Step 1: Find and replace all remaining OpenCode references**

Run: `grep -n -i "opencode\|open.code" SKILL.md`

For each match:
- If it says "restart OpenCode" → replace with "restart Claude Code session"
- If it says "OpenCode was launched" → replace with "Claude Code was launched"
- If it references OpenCode CLI → replace with Claude Code CLI
- If it references "Sisyphus agent" or "orchestrating/main/Sisyphus agent" → replace with "orchestrating agent (you)" or "main agent"

**Step 2: Update the Parallel Execution Pattern diagram header**

Line 199: Change "Parallel Subagent Architecture" subsection intro if it mentions OpenCode-specific agent types.

**Step 3: Verify clean state**

Run the full verification suite:

```bash
# No OpenCode references
grep -c -i "opencode" SKILL.md
# Expected: 0

# No bare chrome-devtools tool references (only mcp__chrome-devtools__* and server name)
grep "chrome-devtools " SKILL.md | grep -v "mcp__chrome-devtools__\|\"chrome-devtools\"\|chrome-devtools-mcp\|chrome-devtools MCP" | wc -l
# Expected: 0

# No old subagent patterns
grep -c "background_output\|load_skills\|subagent_type=\"librarian\"\|subagent_type=\"explore\"\|subagent_type=\"deep\"\|subagent_type=\"writing\"" SKILL.md
# Expected: 0

# No old web tool references
grep -c "websearch_web_search_exa\|google_search\|webfetch" SKILL.md
# Expected: 0
```

**Step 4: Commit**

```bash
git add SKILL.md
git commit -m "migrate: clean up remaining OpenCode references throughout SKILL.md"
```

---

### Task 7: Final Review and Validation

**Files:**
- Read: `SKILL.md` (full file — verify domain content intact)

**Step 1: Spot-check domain sections are unchanged**

Read and verify these sections are identical to the original:
- Product Ownership Analysis section
- Org Chart Reconstruction section
- AI/ML & Agentic AI Strategy section
- Competition Analysis section (CyberArk, Venafi, OpenTofu/Pulumi/Bicep)
- Intelligence Brief output template
- Deep-dive profile template

**Step 2: Verify the file is syntactically valid markdown**

Check for broken formatting:
- All code fences properly closed (matching ``` pairs)
- All tables have consistent column counts
- No orphaned markdown artifacts

**Step 3: Run a quick size comparison**

```bash
wc -l SKILL.md
# Expected: approximately 1560 lines (same as original, ±50 lines from section rewrites)
wc -c SKILL.md
# Expected: approximately 94KB (same as original, ±5KB)
```

**Step 4: Final commit**

```bash
git add SKILL.md docs/plans/
git commit -m "docs: add migration design and implementation plan"
```

---

## Execution Notes

- **Task order matters:** Tasks 1-6 can be done in any order (they modify different sections), but Task 7 (validation) must be last.
- **Tasks 1-6 are parallelizable:** They touch non-overlapping sections of the file. If using subagent-driven development, tasks 3 (global tool rename) should be done AFTER tasks 1-2 to avoid conflicts in the sections being rewritten.
- **Recommended order:** Task 2 (biggest rewrite) → Task 1 (preflight) → Task 3 (global tool rename) → Task 4 (web tools) → Task 5 (error handling) → Task 6 (cleanup) → Task 7 (validation)
