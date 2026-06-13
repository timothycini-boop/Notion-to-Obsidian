# Notion-to-Obsidian
Back up your Notion workspace to GitHub as Markdown each week. Useful for disaster recovery, offline reading, or building a Zettelkasten-style vault in Obsidian.

I built this because Notion is great until you can't get to it. All my important stuff lives there. If Notion goes down or my account gets locked, I lose access. And Notion's own export gives you JSON and CSV that's fine for a worst-case restore but useless otherwise.

This makes a second copy of your workspace in Markdown — readable, searchable, owned. It runs weekly via GitHub Actions for free. Drop it into Obsidian and you get an offline vault with relations preserved as wikilinks, plus Obsidian's graph view: an interactive map of how everything in your workspace connects. Notion doesn't offer that.

One-way only. Notion stays the source of truth.

## Setup

You need a free GitHub account, a Notion workspace, and about an hour the first time.

### 1. Make your own copy

Click **Use this template** at the top → **Create a new repository**. Set it to **Private** — your backup content lives in it.

### 2. Create a Notion integration

`notion.so/my-integrations` → **+ New integration**. Name it "GitHub Backup", pick your workspace, leave type as Internal. Submit.

On the next screen, set **Capabilities** to **Read content** only. Copy the **Internal Integration Token** (long string starting with `ntn_`) and keep it somewhere safe — you'll need it in step 4.

### 3. Share your pages with the integration

A fresh integration sees nothing. For each top-level page in your sidebar:

`•••` menu → Connections → Add connections → find your integration → confirm.

Sub-pages inherit, so top-level is enough.

### 4. Add your token to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.

- Name: `NOTION_TOKEN` (exact, case matters)
- Secret: the token from step 2

### 5. Run it

**Actions tab → Notion Backup → Run workflow → Run workflow**.

First run is 15-30 minutes for a large workspace. When the green check appears, your `backup/` folder is populated. It runs itself every Sunday from then on.

### 6. (Optional) Open in Obsidian

Install [GitHub Desktop](https://desktop.github.com), clone the repo locally. Install [Obsidian](https://obsidian.md), open the `backup` subfolder as a vault.

Weekly: open GitHub Desktop, Fetch → Pull.

Once you're in Obsidian, open the **Graph View** (sidebar icon, or `Cmd+G`) to see your workspace as a connected network. Worth doing once just to see what your scaffolding actually looks like from above.

## Configuration

- **Schedule**: edit the `cron` line in `.github/workflows/backup.yml`. Use crontab.guru if you don't read cron.
- **Exclude databases**: add names (exactly as they appear in `backup/`) to `EXCLUDED_DATABASES` in `backup.py`.
- **Or disconnect in Notion**: remove the integration's connection from the database directly. Cleaner for permanent exclusions.

## Limitations

- **One-way.** Markdown edits don't go back to Notion.
- **Common blocks supported.** Paragraphs, headings, lists, code, callouts, quotes, to-dos all fine. Exotic blocks (synced blocks, equations, embeds) show as comments noting the type.
- **Linked databases partial.** Inline databases back up cleanly. Linked-database *views* embedded in pages sometimes show as unresolved.
- **Slow on large workspaces.** 2,000+ pages takes 20-30 min per run. Well within GitHub Actions' free 2,000 min/month for private repos.
- **Not official.** Not a Notion product. They've changed their API mid-build before and will again.

## Licence

MIT.
