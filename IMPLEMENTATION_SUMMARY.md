# Sales Research Skill — Implementation Summary

## Overview

This skill automates sales intelligence research using **LinkedIn Sales Navigator as the primary tool**, supplemented by web research. It connects to Sales Navigator via Chrome DevTools MCP (browser automation over CDP).

## Architecture Evolution

### Phase 1: Cookie Injection (Replaced)

The original approach injected LinkedIn cookies from the user's real Chrome into MCP's isolated browser instance — a fragile workflow involving Python scripts, SQLite manipulation, AES encryption, and Claude Desktop restarts.

Files removed (archived): `inject_cookies.py`, `refresh-linkedin.sh`

### Phase 2: Debug Chrome via `--browserUrl` (Fallback)

Instead of injecting cookies into MCP's Chrome, we connect MCP to an **already-running Chrome** that has its own persistent session.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     chrome-debug.sh                                  │
│  Launches Chrome with:                                               │
│    --remote-debugging-port=9222                                      │
│    --user-data-dir=~/.chrome-debug-profile                           │
│                                                                      │
│  User logs into LinkedIn once. Session persists in the profile.      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                    CDP over port 9222
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  chrome-devtools-mcp                                  │
│  Connects via --browserUrl=http://127.0.0.1:9222                     │
│  Reuses existing tabs, cookies, and session state.                   │
│  No cookie injection. No encryption. No restarts.                    │
└─────────────────────────────────────────────────────────────────────┘
```

This is now the **fallback** approach — used only when no browser is already connected.

### Phase 3: Existing Browser Session Detection (Feb 2026)

The skill now **detects an existing browser session first** before asking the user to launch anything. This matches the real-world workflow where the user already has Sales Navigator open in their browser.

**Detection flow:**

```
chrome-devtools list_pages
├── Pages returned?
│   ├── Sales Navigator page exists? → Select it, verify auth, proceed
│   └── No Sales Nav page? → Navigate existing page to Sales Navigator
│       ├── Authenticated? → Proceed
│       └── Login page? → Ask user to log in, then retry
└── No pages / MCP not connected
    └── Agent launches debug Chrome automatically (Phase 4)
```

**Key change:** The agent now launches debug Chrome itself via inline bash commands (see Phase 4) — `chrome-debug.sh` is no longer needed as a separate file.

## Sales Navigator API Alternatives (Evaluated Feb 2026)

We investigated whether a programmatic API could replace browser automation:

| Option | Status | Why Not |
|--------|--------|---------|
| **Official SNAP API** | Closed to new partners | LinkedIn's Sales Navigator Application Platform (SNAP) is partnership-only for CRM vendors. Not accepting new partners as of Feb 2026. |
| **Dishant27/linkedin-mcp-server** | 40★ on GitHub | Uses LinkedIn's consumer API — no Sales Nav filters (function, seniority, saved accounts, buyer intent). Very limited search. |
| **IBM/chuk-mcp-linkedin** | 2★ on GitHub | LinkedIn content creation only (posting, drafts). No search or prospecting. |
| **Rayyan9477/linkedin_mcp** | 15★ on GitHub | Job seeker tool (job search, resume generation). Not sales prospecting. |
| **Third-party scrapers (Evaboot, PhantomBuster)** | Available, paid | Still browser-scraping under the hood. $30-100+/month. Adds dependency + account risk. |

**Conclusion:** Browser automation via Chrome DevTools MCP remains the best approach for full Sales Navigator access (advanced filters, saved accounts, buyer intent signals, lead lists) without paying for a third-party scraper or waiting for a closed partnership program.

## Research Workflow

The skill now runs a **two-phase research workflow**:

1. **Phase 1 — Sales Navigator (Primary):** People research via browser automation
   - Two-pass search strategy: broad function filter (leadership) + targeted keywords (specialists)
   - Deep-dive top 3-5 profiles for mutual connections and activity signals
   - Rate-limited pagination (2-3s delays) to avoid bot detection

2. **Phase 2 — Web Research (Supplementary):** Technology & business context
   - Company tech stack, cloud providers, recent initiatives
   - HashiCorp-specific intel (existing product usage, job postings)
   - Business context (news, regulatory, M&A)

3. **Phase 3 — Intelligence Brief:** Tiered output format
   - Tier 1 (Primary Targets), Tier 2 (Influencers), Tier 3 (Extended Network)
   - Technology landscape, conversation strategy, warm intro paths
   - Saved to `HashiCorp/by-customer/[Customer]/[Company] Sales Intelligence [date].md`

## Key Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Full research workflow documentation with Sales Navigator priority |
| `IMPLEMENTATION_SUMMARY.md` | This file — architecture decisions and technical context |
| `Howto.md` | Setup guide for non-technical sales reps |
| `.mcp.json` | MCP config with `--browserUrl=http://127.0.0.1:9222` |
| `archive/chrome-debug.sh` | Archived — original Chrome launcher script (absorbed into SKILL.md) |
| `archive/inject_cookies.py` | Archived — old cookie injection approach |
| `archive/refresh-linkedin.sh` | Archived — old Claude Desktop restart orchestrator |

## MCP Configuration

In `.mcp.json`, the `chrome-devtools` server args include:

```json
{
  "chrome-devtools": {
    "command": "npx",
    "args": [
      "chrome-devtools-mcp@latest",
      "--browserUrl=http://127.0.0.1:9222"
    ]
  }
}
```

## Agent-Managed Chrome Launch (Phase 4 — Feb 2026)

The `chrome-debug.sh` script has been **absorbed into SKILL.md** as inline bash commands. The AI agent now launches Chrome in debug mode itself, eliminating the need for users to run a separate shell script.

**What the agent does (equivalent to the old script):**

1. Checks if port 9222 is already in use (`curl -s http://127.0.0.1:9222/json/version`)
2. Launches Chrome: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.chrome-debug-profile &`
3. Polls the CDP endpoint until Chrome is ready (up to 10 seconds)
4. Detects first-run (no existing profile) and guides the user to log into LinkedIn

**Why:** Simplifies distribution (fewer files to share) and setup (non-technical users don't need to run shell scripts). The script file is archived at `archive/chrome-debug.sh` for reference.

**Original script features preserved:**
- **Idempotent**: Checks if debug Chrome is already running before launching
- **Persistent profile**: Uses `~/.chrome-debug-profile/` — survives Chrome restarts
- **Startup check**: Polls CDP endpoint to confirm Chrome is ready
- **First-run guidance**: Detects fresh profile and prompts user to log in

## Security Notes

- Port 9222 binds to `127.0.0.1` only — not exposed to the network
- Any local process can connect to port 9222 and control the browser
- Don't browse sensitive sites (banking, etc.) in the debug Chrome instance
- The debug profile (`~/.chrome-debug-profile/`) is separate from your regular Chrome profile
- LinkedIn ToS: use responsibly, don't bulk-scrape. 2-3s rate limiting enforced.

## References

- [chrome-devtools-mcp README](https://github.com/nickmilo/chrome-devtools-mcp) — `--browserUrl`, `--autoConnect` flags
- [raf.dev: Chrome Debugging Profile for MCP](https://raf.dev/blog/chrome-debugging-profile-mcp/) — persistent debug profile pattern
- [LinkedIn SNAP docs](https://learn.microsoft.com/en-us/linkedin/sales/) — official Sales Navigator API (closed to new partners)
- Chrome 144+ will support `--autoConnect` via `chrome://inspect/#remote-debugging` (future upgrade path)
