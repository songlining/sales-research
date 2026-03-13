# How To: Run Sales Research with AI

This guide walks you through setting up and running the **Sales Research** skill on your MacBook. It uses an AI agent (via Claude Code CLI) to automate company prospecting — pulling contact data from LinkedIn Sales Navigator, enriching it with web research, and producing a ready-to-use intelligence brief.

**What you'll get**: A Markdown file with tiered contacts, org charts, product ownership analysis, conversation hooks, mutual connection paths, AI/ML opportunity mapping, and competitive landscape — all compiled automatically.

---

## What You Need Before Starting

| Requirement | Do you have it? |
|-------------|-----------------|
| A MacBook (macOS) | ✅ |
| LinkedIn Sales Navigator subscription (active, logged in) | ✅ |
| Google Chrome installed | Probably — check `/Applications/Google Chrome.app` |
| ~30 minutes for first-time setup | ⏱️ |

---

## Part 1: One-Time Setup (First Time Only)

Do these steps once. After that, you can skip straight to [Part 2](#part-2-running-a-research-session).

### Step 1: Install Homebrew (Mac's package manager)

Open **Terminal** (press `Cmd + Space`, type `Terminal`, hit Enter).

Paste this and press Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It will ask for your Mac password (the one you use to log in). Type it — you won't see characters appear, that's normal. Press Enter.

> **Already have it?** Type `brew --version` in Terminal. If you see a version number, skip this step.

After installation, follow any instructions Homebrew prints about adding it to your PATH. Usually it says something like:

```bash
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### Step 2: Install Node.js

In Terminal:

```bash
brew install node
```

Verify it worked:

```bash
node --version
```

You should see something like `v22.x.x` or higher.

### Step 3: Install Claude Code CLI

In Terminal:

```bash
npm install -g @anthropic-ai/claude-code
```

Verify it worked:

```bash
claude --version
```

> **If `npm install` doesn't work**, check the latest install instructions at [https://docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code) — the install method may have changed.

### Step 4: Authenticate Claude Code

Claude Code connects directly to the Anthropic API using your API key or an Anthropic account.

1. Open Terminal and run Claude Code from any folder:

   ```bash
   cd ~/sales-research
   claude
   ```

2. On first launch, Claude Code will prompt you to authenticate. Follow the on-screen instructions — you can either:
   - Log in with your Anthropic account (opens a browser window), or
   - Provide an API key

3. Once authenticated, close Claude Code for now (press `Ctrl+C` or type `/exit`) — we'll come back to it after finishing setup.

> **Why Claude Code?** It's purpose-built for agentic workflows — it can control a browser via MCP, dispatch parallel research agents, and produce structured output, all from a single CLI session.

### Step 5: Set Up Your Research Folder

Create a folder where research artifacts and briefs will be saved. This guide uses an Obsidian vault structure, but any folder works.

```bash
mkdir -p ~/sales-research/.claude/skills/sales-research
```

### Step 6: Copy the Skill Files

You need two files from this repository. Your team lead (Larry) should share these with you:
1. **`SKILL.md`** — The AI's instruction manual for sales research
2. **`IMPLEMENTATION_SUMMARY.md`** — Technical reference (optional, but useful)

Place them in:

```
~/sales-research/.claude/skills/sales-research/
```

So your folder looks like:

```
~/sales-research/
├── .claude/
│   └── skills/
│       └── sales-research/
│           ├── SKILL.md
│           └── IMPLEMENTATION_SUMMARY.md
└── HashiCorp/
    └── by-customer/
```

Create only the root output directory during setup:

```bash
mkdir -p ~/sales-research/HashiCorp/by-customer
```

The skill creates or reuses a canonical customer/company folder under `~/sales-research/HashiCorp/by-customer/` (for example, `~/sales-research/HashiCorp/by-customer/Acme/Acme Corp/`). The first folder may be an existing customer/account folder reused from earlier research or alias resolution, and the customer/company folder names may also be normalized for filesystem safety. You do **not** create those nested folders manually during setup — the skill resolves the path automatically when it saves artifacts. Intermediate artifacts and the final brief live together in that company folder.

### Step 7: Set Up Chrome for Sales Navigator
The AI controls Chrome to browse Sales Navigator on your behalf. It launches Chrome in a special "debug mode" automatically when you start a research session — you don't need to do anything manually.

The only thing you need to ensure is that **Google Chrome is installed** on your Mac (the standard `/Applications/Google Chrome.app` location).

Verify Chrome is installed:

```bash
ls /Applications/Google\ Chrome.app
```

If you see the app listed, you're good. If not, download Chrome from [google.com/chrome](https://www.google.com/chrome/).

### Step 8: Create Your CLAUDE.md File

This file tells the AI about you and your accounts. Create it at the root of your research folder:

```bash
cat > ~/sales-research/CLAUDE.md << 'EOF'
# Memory

## Me
[Your Name], [Your Role] at HashiCorp (Australia), now part of IBM.

## Customers
| Name | Full Name | Key Products |
|------|-----------|-------------|
| Example Co | Example Company | Vault Self-M (100), TFC (5000 RUM) |

(Add your accounts here)
EOF
```

Open it in a text editor and fill in your details:

```bash
open -e ~/sales-research/CLAUDE.md
```

Replace the placeholder content with your real name, role, and customer list. This helps the AI cross-reference existing accounts and personalise research.


### Step 9: Configure the Chrome DevTools MCP

Add the Chrome DevTools MCP server to Claude Code:

```bash
claude mcp add chrome-devtools -s user -- npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222
```

Alternatively, create an `.mcp.json` file in your research folder (Claude Code reads this too):

```bash
cat > ~/sales-research/.mcp.json << 'EOF'
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
EOF
```

---

## Part 2: Running a Research Session

Do these steps every time you want to research a company.

### Step 1: Start Claude Code

Open Terminal, navigate to your research folder, and launch Claude Code:
```bash
cd ~/sales-research
claude
```

### Step 2: Log Into Sales Navigator (First Time Only)

When you start your first research request, the AI will automatically launch a debug Chrome window. This is a **separate Chrome profile** — it won't affect your regular Chrome bookmarks, history, or logins.

In the debug Chrome window that opens:
1. Go to **https://www.linkedin.com/sales/**
2. Log in with your LinkedIn credentials
3. Make sure you can see the Sales Navigator search page
> **This login persists.** The debug Chrome profile saves your session at `~/.chrome-debug-profile/`. You won't need to log in again unless LinkedIn expires your session (usually ~1 year). Next time, the AI launches debug Chrome and you're already logged in.
### Step 3: Tell It What to Research

Type your research request naturally. Examples:

> **Basic:**
> ```
> Research AMP — I need to find their DevOps and cloud engineering leadership
> ```

> **With specific products:**
> ```
> Research Woolworths — focus on people who might own Terraform and Vault.
> They're a big AWS shop, look for platform engineering and security teams too.
> ```

> **Meeting prep:**
> ```
> Prepare for my meeting with ASX. Find the infrastructure team,
> who owns their Vault deployment, and any mutual connections I can use for intros.
> ```

> **Broad prospecting:**
> ```
> Build a contact list for NAB — I want to find DevOps, cloud, security,
> and platform engineering people. Check if they use any HashiCorp products.
> ```

### Step 4: Let It Work

The AI will:

1. **Connect to your debug Chrome** and navigate Sales Navigator
2. **Run multiple search passes** with different filters (leadership, specialists, security team, etc.)
3. **Extract contact data** from search results
4. **Deep-dive top profiles** — clicking into each one for career history, skills, mutual connections
5. **Run web research in parallel** — tech stack, job postings, news, competitors
6. **Compile everything** into a structured intelligence brief
7. **Save the artifacts and brief** in the resolved canonical company folder under `~/sales-research/HashiCorp/by-customer/` — for example, `~/sales-research/HashiCorp/by-customer/Acme/Acme Corp/`, with the final brief saved alongside the intermediate notes as `Acme Corp Sales Intelligence Brief.md`

This typically takes **10–20 minutes** depending on the size of the company. You can watch the AI work in the debug Chrome window — it's clicking through Sales Navigator in real time.

### Step 5: Review Your Brief

When it's done, open `~/sales-research/HashiCorp/by-customer/`, then open the resolved customer/company folder the skill created or reused for that run. The first folder may be an existing canonical customer/account folder reused from earlier research or alias resolution, and the customer/company folder names may also be normalized for filesystem safety:

```bash
open ~/sales-research/HashiCorp/by-customer/
```

For example, you might open `~/sales-research/HashiCorp/by-customer/Acme/Acme Corp/`. Or if you use Obsidian, open your `~/sales-research` folder as a vault and the company folder will show the intermediate notes and final brief together.

---

## Troubleshooting

### "Chrome is already running on port 9222"

This means debug Chrome is already open. You're good — the AI will use it.

### "Port 9222 is not responding"

Close **all** Chrome windows (including your regular Chrome), then ask the AI to try again. Only one Chrome instance can use port 9222.
Alternatively, check if something is already on port 9222:
```bash
lsof -i :9222
```

Kill it if needed:

```bash
kill $(lsof -ti :9222)
```

### "Login page appears" / "Session expired"

Your LinkedIn session expired. In the debug Chrome window:

1. Go to https://www.linkedin.com/sales/
2. Log in again
3. Go back to Claude Code and type `continue`

### AI says "No browser detected" or MCP connection errors
1. Ask the AI to launch debug Chrome (it does this automatically, but you can say "launch Chrome")
2. Check that the Chrome DevTools MCP is configured: run `claude mcp list` and look for `chrome-devtools`
3. Restart Claude Code: exit and run `claude` again

### 0 search results on Sales Navigator

The company name might not match exactly. Try:
- The full legal name (e.g., "AMP Limited" instead of "AMP")
- Checking the company page on Sales Navigator manually first
- Asking the AI to broaden the search criteria

### AI is slow or stuck

LinkedIn rate-limits bot-like behaviour. The AI deliberately waits 2–3 seconds between actions. If it seems stuck:
- Wait 30 seconds — it may be rate-limited
- Check the debug Chrome window — can you see what it's doing?
- If truly stuck, type `stop` in Claude Code and try a simpler request

### "CAPTCHA appeared"

LinkedIn detected automated browsing. In the debug Chrome window:
1. Solve the CAPTCHA manually
2. Go back to Claude Code and type `continue`

---

## Tips for Best Results

1. **Be specific about what you need.** "Research NAB's platform engineering team for Terraform" gets better results than just "Research NAB."

2. **Mention products of interest.** The AI tailors its search keywords to the products you care about (Vault, Terraform, Boundary, etc.).

3. **Ask for deep-dives on specific people.** After the initial research, you can say "deep-dive John Smith" to get the full profile treatment.

4. **Build incrementally.** You can run research across multiple sessions. The AI appends to existing briefs rather than overwriting them. Say "add more contacts to the AMP brief" or "deep-dive the security team at AMP."

5. **Check the Appendix.** Every brief includes Sales Navigator URLs in the appendix. Click them to go directly to profiles.

6. **Watch for "Follows HashiCorp" contacts.** These are pre-warmed leads — prioritise them for outreach.

7. **Contractors ≠ decision-makers.** The AI flags contractors (Wipro, DXC, Accenture staff embedded at the company). They're useful contacts but won't sign contracts.

---

## Quick Reference

| Task | Command |
|------|---------|
| Start Claude Code | `cd ~/sales-research && claude` |
| Research a company | Type naturally: "Research [Company] — [what you need]" |
| Deep-dive a person | "Deep-dive [Name] from [Company]" |
| Add to existing brief | "Add more contacts to the [Company] brief" |
| Check if Chrome is running | `curl -s http://127.0.0.1:9222/json/version` |
| Kill stuck Chrome | `kill $(lsof -ti :9222)` |
| View a company folder | `open ~/sales-research/HashiCorp/by-customer/` |

---

## Folder Structure After Your First Research Run

After setup, you'll have the skill files and top-level workspace. The fuller customer/company tree below appears once the skill has researched a company.

```
~/sales-research/
├── .claude/
│   └── skills/
│       └── sales-research/
│           ├── SKILL.md              ← AI's research instructions
│           └── IMPLEMENTATION_SUMMARY.md
├── .mcp.json                         ← MCP config for Chrome DevTools (optional if using `claude mcp add`)
├── CLAUDE.md                         ← Your info & customer list
└── HashiCorp/
    └── by-customer/
        └── Acme/                            ← canonical customer folder; created/resolved by the skill
            └── Acme Corp/                   ← canonical company folder; created/resolved by the skill
                ├── contacts-pass-1.md
                ├── tech-landscape-research.md
                ├── meeting-prep-notes.md
                └── Acme Corp Sales Intelligence Brief.md
```

---

## Updating the Skill

When Larry shares updated versions of `SKILL.md` or other files, simply replace them in `~/sales-research/.claude/skills/sales-research/`. No reinstallation needed — the AI reads these files fresh each time.
