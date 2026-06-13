# Notion-to-Obsidian
Back up your Notion workspace to GitHub as Markdown each week. Useful for disaster recovery, offline reading, or building a Zettelkasten-style vault in Obsidian.

----

I built this because Notion is great right up to the point you can't get to it. All my work systems, contracts, project notes, personal writing, they live there. If Notion goes down, or my account gets locked, or they kill a feature I depend on, or any of a dozen other things, I lose access to material I genuinely need. And Notion's own export only gives you JSON dumps and CSVs that are fine for a worst-case restore but useless for anything else.

I wanted a second copy of my workspace that I actually own, in a format I can read offline, search through, and open in another tool if I want to. This is that.

It runs on GitHub Actions every Sunday at 3am UTC. It walks your Notion workspace, converts every page and database row into Markdown with YAML frontmatter, and commits the result back to your repo. Total cost: $0. Total maintenance: nothing once it's set up, unless you want a fresh copy on your laptop.

The result is a `backup/` folder you can:

- Browse on GitHub
- Clone to your laptop with GitHub Desktop
- Open as a vault in Obsidian — every relation between database rows becomes a clickable wikilink, so your knowledge graph survives the move
- Read on a plane, on a phone, on anything that reads text files

This is a backup, not a sync. One-way (Notion → Markdown). Nothing you change in the Markdown gets pushed back to Notion.

## Setup

You'll need: a free GitHub account, a Notion workspace, and about an hour the first time. After that it runs itself.

### 1. Make your own copy of this repo

Click **Use this template** at the top of this page → **Create a new repository**. Name it whatever you want (`my-notion-backup` works fine). Set it to **Private** — your backup content will live inside it, so it shouldn't be public.

### 2. Create a Notion integration

Go to `notion.so/my-integrations` → **+ New integration**. Name it something recognisable like "GitHub Backup", pick your workspace, leave the type as Internal. Submit.

On the next screen, find **Capabilities** and set it to **Read content** only. Then find the **Internal Integration Token** — it's a long string starting with `ntn_` or `secret_`. Click Show, copy it, paste it somewhere safe temporarily like a password manager. You'll use it in step 4.

### 3. Share your pages with the integration

A fresh Notion integration starts with access to nothing. You have to invite it to each top-level page you want backed up. Sub-pages and child databases inherit, so this is only top-level.

For each page in your sidebar that matters:

- Open the page
- Click the `•••` menu top-right
- Connections → Add connections → search for your integration name → confirm

### 4. Add your token to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.

- Name: `NOTION_TOKEN` (this exact name, case matters)
- Secret: the token you copied in step 2

Click Add. GitHub encrypts the value. Even you can't view it again afterwards — only the workflow can.

### 5. Run it

**Actions tab → Notion Backup → Run workflow → Run workflow** (leave the branch as main).

The first run can take 15-30 minutes depending on how much you have in Notion. When the green check appears, look at your `backup/` folder — there should be one file per page and database row.

It'll also run automatically every Sunday from now on.

### 6. (Optional) Open it in Obsidian

Install [GitHub Desktop](https://desktop.github.com). Clone your repo to a local folder. Install [Obsidian](https://obsidian.md). Open Obsidian → "Open folder as vault" → point at the `backup` subfolder inside the folder GitHub Desktop made.

To pull fresh content after the weekly run: open GitHub Desktop, click **Fetch origin**, then **Pull origin** when something's new.

## Configuration

- **Change the schedule**: edit the `cron` line in `.github/workflows/backup.yml`. Use crontab.guru if you don't speak cron natively.
- **Exclude databases**: add their exact names (as they appear in your `backup/` subfolders) to the `EXCLUDED_DATABASES` list at the top of `backup.py`.
- **Cleaner alternative**: just remove the integration's connection from a database in Notion (the `•••` menu → Connections → remove). That's the simpler way for permanent exclusions and doesn't require touching code.

## Limitations

Honest about what this doesn't do well, since you should know before you depend on it:

- **One-way only.** Edits in Markdown don't sync back to Notion. Notion stays the source of truth.
- **Some block types aren't handled.** Mostly the exotic ones — synced blocks, equations, fancy embeds. They show up as HTML comments noting the unsupported type. Common stuff (paragraphs, headings, lists, code, callouts, quotes, to-dos) is fine.
- **Linked database resolution is partial.** Inline databases back up cleanly. Linked-database *views* embedded in page bodies sometimes show as "unresolved" because Notion's API doesn't always expose what they point to.
- **Big workspaces are slow.** ~2,000+ pages takes 20-30 minutes per run, due to API rate limits (3 requests/second). Free tier of GitHub Actions allows 2,000 minutes/month for private repos, so this isn't a problem in practice.
- **Not official.** This isn't a Notion product. They've changed their API mid-build before (the data sources split in September 2025) and will probably do it again. If something breaks, check Notion's changelog first.

## Licence

MIT. Do whatever you want with the code, just keep the copyright notice.
