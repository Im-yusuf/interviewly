#!/usr/bin/env python3
"""Who wrote what in a git repository: the user, AI assistants, or other people. Standard library only.

Reads `git log` and reports, for the repository and for each file that still exists:
  - lines added by the user's own commits, by their commits that credit an AI assistant
    (a Co-Authored-By trailer or a "Generated with" line), and by other people and bots
  - which AI tool config files are present (CLAUDE.md, AGENTS.md, .cursorrules, ...)
  - very large single commits (often generated or imported code)

These are signals, not proof: squash merges, missing trailers and pasted code all hide
how code was written. The user confirms what it means.

Usage: provenance.py REPO [--me "name or email, ..."] [--subdir PATH] [--top N] [--json]
Without --me, the authors are listed so the user can say which ones are them.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

AI_TRAILER = re.compile(
    r"^co-authored-by:.*\b(claude|anthropic|copilot|cursor|devin|codex|openai|chatgpt|gpt-|gemini|aider|"
    r"windsurf|codeium|cline|amazon q|codewhisperer|tabnine|replit|lovable|bolt|v0)\b", re.I | re.M)
AI_MESSAGE = re.compile(r"generated with \[?(claude|cursor|copilot|codex|aider)|🤖 generated|^aider: ", re.I | re.M)
BOT_AUTHOR = re.compile(r"\[bot\]|github-actions|dependabot|renovate|devin-ai|copilot-swe|noreply@anthropic", re.I)
TOOL_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".cursor/rules", ".github/copilot-instructions.md",
              ".windsurfrules", ".clinerules", ".aider.conf.yml", ".aiderignore", ".claude", ".codex", ".continue")
BULK_LINES = 1500
RECORD, FIELD = "\x1e", "\x1f"


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise SystemExit(f"git {' '.join(args[:2])} failed in {repo}: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout.decode("utf-8", "replace")


def is_me(name, email, me):
    who = f"{name} {email}".lower()
    return any(m and m in who for m in me)


def analyse(repo, me=(), subdir=None, top=25):
    repo = Path(repo).expanduser().resolve()
    if not (repo / ".git").exists() and not git(repo, "rev-parse", "--is-inside-work-tree").strip() == "true":
        raise SystemExit(f"{repo} isn't a git repository")
    me = [m.strip().lower() for m in me if m.strip()]
    paths = ["--", subdir] if subdir else []
    log = git(repo, "log", "--no-merges", "--date=short", "--numstat",
              f"--format={RECORD}%H{FIELD}%an{FIELD}%ae{FIELD}%ad{FIELD}%B{FIELD}", *paths)
    current = set(git(repo, "ls-files", *(paths[1:] if subdir else [])).splitlines())
    authors, files, bulk = {}, {}, []
    totals = {"mine": 0, "mine_ai": 0, "others": 0, "bots": 0}
    commits = ai_commits = 0
    for record in log.split(RECORD)[1:]:
        head = record.split(FIELD)
        if len(head) < 6:
            continue
        sha, name, email, date, body, stats = head[0], head[1], head[2], head[3], head[4], head[5]
        commits += 1
        ai = bool(AI_TRAILER.search(body) or AI_MESSAGE.search(body))
        bot = bool(BOT_AUTHOR.search(f"{name} {email}"))
        mine = is_me(name, email, me) if me else False
        kind = "bots" if bot else ("mine_ai" if ai else "mine") if mine else ("others" if me else ("mine_ai" if ai else "mine"))
        ai_commits += ai
        added_here = 0
        for line in stats.strip().splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or not parts[0].isdigit():
                continue  # binary files show "-"
            added, path = int(parts[0]), parts[2]
            if "=>" in path:  # renames: count against the new path
                path = re.sub(r"\{[^{}]*=> ([^{}]*)\}", r"\1", path).replace("//", "/")
                path = path.split(" => ")[-1]
            added_here += added
            if path in current:
                f = files.setdefault(path, {"path": path, "mine": 0, "mine_ai": 0, "others": 0, "bots": 0, "last": date})
                f[kind] += added
                f["last"] = max(f["last"], date)
        totals[kind] += added_here
        a = authors.setdefault(email.lower(), {"name": name, "email": email, "commits": 0, "added": 0, "ai_commits": 0})
        a["commits"] += 1
        a["added"] += added_here
        a["ai_commits"] += ai
        if added_here >= BULK_LINES:
            bulk.append({"commit": sha[:10], "date": date, "author": name, "added": added_here,
                         "subject": body.strip().splitlines()[0][:80] if body.strip() else ""})
    for f in files.values():
        total = sum(f[k] for k in ("mine", "mine_ai", "others", "bots"))
        f["added"] = total
        f["ai_share"] = round(100 * f["mine_ai"] / total) if total else 0
    tools = [t for t in TOOL_FILES if (repo / t).exists()]
    total = sum(totals.values())
    return {
        "repo": str(repo), "subdir": subdir, "identities": me, "commits": commits, "ai_commits": ai_commits,
        "lines_added": total, "share": {k: round(100 * v / total) if total else 0 for k, v in totals.items()},
        "tool_files": tools,
        "authors": sorted(authors.values(), key=lambda a: -a["added"])[:10],
        "bulk_commits": sorted(bulk, key=lambda b: -b["added"])[:5],
        "files": sorted(files.values(), key=lambda f: -f["added"])[:top],
        "note": "Signals, not proof: squash merges, missing trailers and pasted code hide how code was written.",
    }


def summary(r):
    s = r["share"]
    lines = [f"{r['repo']}{' (' + r['subdir'] + ')' if r['subdir'] else ''}: {r['commits']} commits, "
             f"{r['ai_commits']} credit an AI assistant"]
    if r["identities"]:
        lines.append(f"lines added: you {s['mine']}%, you with AI {s['mine_ai']}%, others {s['others']}%, bots {s['bots']}%")
    else:
        lines.append("authors (say which are you, then run again with --me):")
        lines += [f"  {a['name']} <{a['email']}>: {a['commits']} commits, +{a['added']} lines" for a in r["authors"]]
    if r["tool_files"]:
        lines.append("AI tool files: " + ", ".join(r["tool_files"]))
    for b in r["bulk_commits"]:
        lines.append(f"large commit {b['commit']} ({b['date']}, +{b['added']}): {b['subject']}")
    lines.append("biggest files (added lines: you / you with AI / others):")
    lines += [f"  {f['path']}: {f['mine']} / {f['mine_ai']} / {f['others']}" for f in r["files"][:12]]
    lines.append(r["note"])
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo")
    p.add_argument("--me", default="", help="comma-separated names or emails that are the user")
    p.add_argument("--subdir", help="only this folder of the repository")
    p.add_argument("--top", type=int, default=25, help="how many files to list")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    report = analyse(args.repo, args.me.split(","), args.subdir, args.top)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else summary(report))


if __name__ == "__main__":
    main()
