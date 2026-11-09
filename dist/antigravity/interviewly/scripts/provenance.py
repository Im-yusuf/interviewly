#!/usr/bin/env python3
"""Who wrote what in a git repository: the user, AI assistants, or other people. Standard library only.

Reads `git log` and reports, for the repository and for each file that still exists:
  - lines added by the user's own commits, by their commits that credit an AI assistant
    (a Co-Authored-By trailer or a "Generated with" line), and by other people and bots
  - which AI tool config files are present (CLAUDE.md, AGENTS.md, .cursorrules, ...)
  - very large single commits (often generated or imported code)

Lockfiles, minified and vendored files, build output and files marked linguist-generated or
linguist-vendored in .gitattributes are left out of the shares. A path inside a repository is
read as that folder of it. Shallow and partial clones are flagged, and nothing is ever fetched.

These are signals, not proof: squash merges, missing trailers and pasted code all hide
how code was written. The user confirms what it means.

Usage: provenance.py REPO [--me-file PATH | --me "name or email, ..."] [--subdir PATH] [--top N]
                     [--max-commits N] [--json]
Without identities, the authors are listed so the user can say which ones are them. --me-file
reads a JSON list of identities, or one per line ("-" reads standard input, for a quoted heredoc).
--me can be repeated; separate identities with ";" instead of "," when a name contains a comma.
"""
import argparse
import json
import os
import posixpath
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

# All patterns run in linear time: commit messages come from the repo and can be huge.
CO_AUTHOR = re.compile(r"^[ \t]*co-authored-by[ \t]*:(.*)$", re.I | re.M)
AI_MESSAGE = re.compile(
    r"^[^\w\n]*(?:generated|created|written) (?:with|by|using) \[?(?:claude|cursor|copilot|codex|aider|gemini|chatgpt|"
    r"devin|windsurf|codeium|cline|junie|lovable|bolt|v0)\b|^[^\w\n]*🤖[ \t]*generated|^aider: ", re.I | re.M)
BOT_AUTHOR = re.compile(r"\[bot\]|github-actions|dependabot|renovate|devin-ai|copilot-swe|noreply@anthropic", re.I)
# A co-author's name counts as an AI tool only when every word is a tool, vendor or model word ("Claude Opus 4.5",
# "GitHub Copilot", "aider (gpt-4o)"), so "Devin Patel" or "Ana Cline" stay human.
AI_NAMES = {"claude", "copilot", "cursor", "devin", "codex", "openai", "chatgpt", "gpt", "gemini", "aider", "windsurf",
            "codeium", "cline", "codewhisperer", "tabnine", "lovable", "bolt", "v0", "junie", "openhands", "replit", "q"}
AI_WORDS = {"github", "anthropic", "google", "amazon", "aws", "jetbrains", "code", "agent", "ai", "assistant", "assist",
            "opus", "sonnet", "haiku", "cli", "chat", "bot", "pro", "flash", "swe", "mini", "developer",
            "integration", "app", "engineer", "connector", "labs"}
AI_DOMAINS = {"openai.com", "cursor.com", "cursor.sh", "codeium.com", "windsurf.com", "aider.chat"}
AI_LOCAL_PARTS = {"anthropic.com": ("noreply", "no-reply", "claude"), "google.com": ("gemini", "jules"),
                  "all-hands.dev": ("openhands",), "replit.com": ("agent", "noreply", "no-reply")}
GITHUB_NOREPLY = re.compile(r"^(?:\d+\+)?(.+)@users\.noreply\.github\.com$", re.I)
TOOL_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".cursor/rules", ".github/copilot-instructions.md",
              ".windsurfrules", ".clinerules", ".aider.conf.yml", ".aiderignore", ".claude", ".codex", ".continue")
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
             "pipfile.lock", "cargo.lock", "go.sum", "composer.lock", "gemfile.lock", "bun.lock", "bun.lockb",
             "packages.lock.json", "gradle.lockfile", ".pnp.cjs", ".pnp.loader.mjs"}
GENERATED_SUFFIXES = (".lock", ".min.js", ".min.css", ".js.map", ".css.map", ".snap")
GENERATED_DIRS = {"node_modules", "vendor", "third_party", "dist", "build", ".yarn"}
BULK_LINES = 1500
MAX_COMMITS = 20000
MAX_LEFT_OUT = 200  # partial clones: most files whose contents weren't downloaded that can be left out by name
TIME_LIMIT = 90  # seconds for all git calls together, under the Bash tool's 120 s default
# Repo config can name programs that read-only commands run (core.fsmonitor on any index read, gpg.program via
# log.showSignature, an upload-pack, ssh or remote helper on a lazy fetch). Turn them off; run() also blocks every
# transport, because this script never needs the network.
SAFE = ("--no-pager", "-c", "core.fsmonitor=", "-c", "core.quotepath=off", "-c", "log.showSignature=false",
        "-c", "protocol.allow=never", "-c", "color.ui=false")
LOG = ("log", "-z", "--no-merges", "--no-ext-diff", "--no-textconv", "--encoding=UTF-8")
NOTE = "Signals, not proof: squash merges, missing trailers and pasted code hide how code was written."


def run(repo, *args, input=None, timeout=TIME_LIMIT):
    # An empty GIT_ALLOW_PROTOCOL allows no transport, and unlike -c protocol.allow=never it beats a
    # protocol.<name>.allow in the repo's own config. GIT_NO_LAZY_FETCH (git 2.44+) stops lazy fetches outright.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_ALLOW_PROTOCOL="",
               GIT_NO_LAZY_FETCH="1")
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_LITERAL_PATHSPECS",
              "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"):
        env.pop(k, None)  # they would point git elsewhere or turn off the pathspec magic used below
    stdin = {"input": input} if input is not None else {"stdin": subprocess.DEVNULL}
    try:
        return subprocess.run(["git", *SAFE, "-C", str(repo), *args], capture_output=True, env=env,
                              timeout=max(1, timeout), **stdin)
    except FileNotFoundError:
        raise SystemExit("git isn't installed, or isn't on PATH")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"git ran out of time ({TIME_LIMIT} s for the whole analysis) in {repo}: "
                         "run again with --max-commits 5000 or --subdir <folder>")


def git(repo, *args, check=True, **kw):
    """Run a read-only git command and return its stdout as bytes (None on failure when check=False)."""
    result = run(repo, *args, **kw)
    if not result.returncode:
        return result.stdout
    if not check:
        return None
    err = result.stderr.decode("utf-8", "replace").strip().splitlines()
    err = err[-1] if err else f"exit code {result.returncode}"
    if "promisor remote" in err:
        err += " (a partial clone: re-clone it with --filter=blob:limit=1m)"
    raise SystemExit(f"git {' '.join(a for a in args[:2] if not a.startswith('-'))} failed in {repo}: {err}")


def text(raw):
    return raw.decode("utf-8", "replace")


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).split()).casefold()


def split_identities(values):
    """--me values: comma-separated, or ";"- or newline-separated when a name contains a comma."""
    out = []
    for value in values or []:
        parts = re.split(r"[;\n]", value) if re.search(r"[;\n]", value) else value.split(",")
        out += [p.strip() for p in parts if p.strip()]
    return out


def read_identities(path):
    """--me-file: a JSON list of identities, or one per line; "-" reads them from standard input."""
    try:
        raw = sys.stdin.buffer.read() if path == "-" else Path(path).expanduser().read_bytes()
    except OSError as e:
        raise SystemExit(f"can't read --me-file {path}: {e.strerror or e}")
    data = raw.decode("utf-8-sig", "replace")
    if not data.lstrip().startswith("["):
        return [line.strip() for line in data.splitlines() if line.strip()]
    try:
        values = json.loads(data)
    except ValueError as e:
        raise SystemExit(f"--me-file isn't a valid JSON list: {e}")
    if not all(isinstance(v, str) for v in values):
        raise SystemExit("--me-file must hold a JSON list of names and emails")
    return [v.strip() for v in values if v.strip()]


def person(value):
    """'Name <email>' -> (name, email); anything else -> (value, "")."""
    value = value.strip()
    if value.endswith(">") and "<" in value:
        name, _, email = value[:-1].rpartition("<")
        return name.strip(), email.strip()
    return value, ""


def matches(name, email, me):
    """The identities in me (normalised) that are this author. Exact and case-insensitive: one with "@" is an email,
    "Name <email>" is both, anything else a name or GitHub username. aider's " (aider)" name suffix is ignored."""
    name, email = norm(name), norm(email)
    name = name[:-7].rstrip() if name.endswith("(aider)") else name
    handle = GITHUB_NOREPLY.match(email)
    handle = handle.group(1) if handle else None
    found = []
    for ident in me:
        ident_name, ident_email = person(ident)
        if not ident_email and "@" in ident_name:
            ident_name, ident_email = "", ident_name
        other = GITHUB_NOREPLY.match(ident_email) if ident_email else None
        if (ident_email and (ident_email == email or (other and other.group(1) == handle))) or (
                ident_name and ident_name in (name, handle)):
            found.append(ident)
    return found


def is_me(name, email, me):
    return bool(matches(name, email, [norm(m) for m in me]))


def ai_words(s, bot=False):
    words = re.findall(r"[a-z0-9.]+", re.sub(r"\([^()]*\)", " ", s.casefold()))
    if bot:  # a GitHub app such as devin-ai-integration[bot]; pre-commit-ci[bot] and dependabot[bot] aren't AI
        return any(w in AI_NAMES or w == "jules" for w in words)
    return bool(words) and any(w in AI_NAMES for w in words) and all(
        w in AI_NAMES or w in AI_WORDS or any(c.isdigit() for c in w) for w in words)


def ai_email(email):
    local, _, domain = email.casefold().rpartition("@")
    if domain == "users.noreply.github.com":
        handle = re.sub(r"^\d+\+", "", local)
        return handle == "copilot" or (handle.endswith("[bot]") and ai_words(handle[:-5], bot=True))
    return domain in AI_DOMAINS or local.startswith(AI_LOCAL_PARTS.get(domain, ("\0",)))


def is_ai_coauthor(value):
    """A Co-authored-by value: an AI tool's email, or an AI tool's name with no email or a noreply one."""
    name, email = person(value)
    if email and ai_email(email):
        return True
    return ai_words(name) and (not email or email.casefold().split("@")[0] in ("noreply", "no-reply"))


def co_authors(body):
    """(name, email) for each Co-authored-by trailer."""
    return [person(v) for v in CO_AUTHOR.findall(body)]


def is_ai_commit(body):
    return any(is_ai_coauthor(v) for v in CO_AUTHOR.findall(body)) or bool(AI_MESSAGE.search(body))


def ignored(path, subdir, attrs):
    """Lockfiles and generated or vendored files. .gitattributes can say otherwise; --subdir overrides the folders."""
    if attrs.get(path) is not None:
        return attrs[path]
    rel = path[len(subdir) + 1:] if subdir and path.startswith(subdir + "/") else path
    parts = rel.casefold().split("/")
    return parts[-1] in LOCKFILES or parts[-1].endswith(GENERATED_SUFFIXES) or any(p in GENERATED_DIRS for p in parts[:-1])


def linguist(top, paths, timeout):
    """path -> True (generated or vendored), False (explicitly not) or None, from one git check-attr call."""
    if not paths:
        return {}
    out = git(top, "check-attr", "-z", "--stdin", "linguist-generated", "linguist-vendored",
              input=b"\0".join(p.encode("utf-8") for p in paths) + b"\0", check=False, timeout=timeout)
    attrs, tokens = {}, text(out or b"").split("\0")
    for path, _, value in zip(tokens[0::3], tokens[1::3], tokens[2::3]):
        if value in ("set", "true"):
            attrs[path] = True
        elif value in ("unset", "false"):
            attrs.setdefault(path, False)
    return attrs


def locate(repo, subdir):
    """The repository's top level, and the folder to analyse relative to it (a path inside a repo becomes one)."""
    repo = Path(repo).expanduser().resolve()
    if not repo.is_dir():
        raise SystemExit(f"{repo} doesn't exist" if not repo.exists() else f"{repo} isn't a folder")
    probe = run(repo, "rev-parse", "--is-bare-repository")
    if probe.returncode:
        err = text(probe.stderr).strip()
        raise SystemExit(f"{repo} isn't a git repository" if "not a git repository" in err or not err
                         else f"can't read {repo} with git: {err.splitlines()[-1]}")
    if text(probe.stdout).strip() == "true":
        top, prefix, shallow = repo, "", "shallow"
    else:
        lines = os.fsdecode(git(repo, "rev-parse", "--show-toplevel", "--show-prefix", "--git-path", "shallow")).split("\n")
        top, prefix, shallow = Path(lines[0]), lines[1].rstrip("/"), lines[2]
    shallow = repo / shallow
    sub = prefix
    if subdir and os.path.isabs(subdir):
        try:
            sub = os.path.relpath(Path(subdir).resolve(), top)
        except ValueError:  # another drive on Windows
            sub = ".."
    elif subdir:  # relative to the folder given, or to the top level when only that has it
        inside = (repo / subdir).exists() or not (top / subdir).exists()
        sub = posixpath.join(prefix, subdir.replace("\\", "/")) if prefix and inside else subdir
    sub = posixpath.normpath(sub.replace("\\", "/")) if sub else ""
    if sub == ".":
        sub = ""
    if sub == ".." or sub.startswith("../") or sub.startswith("/"):
        raise SystemExit(f"--subdir {subdir} is outside the repository {top}")
    return top, sub, shallow


def partial_clone(top, timeout):
    """(filter, remote) for a partial clone, or None: its missing file contents would be fetched one commit at a time."""
    cfg = git(top, "config", "-z", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$",
              check=False, timeout=timeout)
    values = dict(item.partition("\n")[::2] for item in text(cfg or b"").split("\0") if item)
    remotes = [k[7:-9] for k, v in values.items() if k.endswith(".promisor") and v.lower() in ("true", "yes", "on", "1", "")]
    remotes += [values["extensions.partialclone"]] if values.get("extensions.partialclone") else []
    if not remotes:
        return None
    filters = [values.get(f"remote.{r}.partialclonefilter", "") for r in remotes]
    return (filters[0] if len(set(filters)) == 1 else "mixed"), remotes[0]


def missing_objects(top, paths, timeout, *options):
    """Ids of the objects a partial clone lacks, found without fetching anything. With --filter=blob:none, only the
    missing trees (folder listings) and commits, which git log can't do without."""
    objects = git(top, "rev-list", "--objects", "--missing=print", *options, "HEAD", "--", *paths, timeout=timeout)
    return {line[1:] for line in text(objects).splitlines() if line.startswith("?")}


def missing_paths(top, paths, missing, timeout):
    """Paths with at least one version among the missing objects."""
    if not missing:
        return set()
    raw = git(top, *LOG, "--raw", "--no-renames", "--no-abbrev", "--format=", "HEAD", "--", *paths, timeout=timeout)
    found, tokens = set(), iter(raw.split(b"\0"))
    for token in tokens:
        if token.lstrip(b"\n").startswith(b":"):
            meta, path = text(token).split(), text(next(tokens, b""))
            if len(meta) >= 4 and (meta[2] in missing or meta[3] in missing):
                found.add(path)
    return found


def fold(paths, sub, limit):
    """The paths, or the folders holding them (the deepest level that fits), as at most limit entries inside sub;
    None when even the top folders are too many."""
    shallowest = sub.count("/") + 2 if sub else 1
    for depth in range(max(p.count("/") + 1 for p in paths), shallowest - 1, -1):
        groups = sorted({"/".join(p.split("/")[:depth]) for p in paths})
        if len(groups) <= limit:
            return groups
    return None


def parse_numstat(raw):
    """sha -> [(added lines or None for binary, path, old path if renamed)] from `git log -z --numstat --format=%x1e%H`."""
    stats, sha, tokens = {}, None, iter(raw.split(b"\0"))
    for token in tokens:
        token = token.lstrip(b"\n")
        if token.startswith(b"\x1e"):
            sha = text(token[1:])
            stats[sha] = []
            continue
        parts = token.split(b"\t", 2)
        if sha is None or len(parts) != 3:
            continue
        path, old = parts[2], None
        if not path:  # a rename: the old and new paths follow
            old, path = next(tokens, b""), next(tokens, b"")
        stats[sha].append((int(parts[0]) if parts[0].isdigit() else None, text(path), old and text(old)))
    return stats


def analyse(repo, me=(), subdir=None, top=25, max_commits=MAX_COMMITS):
    deadline = time.monotonic() + TIME_LIMIT

    def left():
        return deadline - time.monotonic()

    root, sub, shallow_file = locate(repo, subdir)
    me = list(dict.fromkeys(norm(m) for m in me if m.strip()))
    report = {"repo": str(root), "subdir": sub or None, "identities": me, "commits": 0, "ai_commits": 0,
              "lines_added": 0, "share": {k: 0 for k in ("mine", "mine_ai", "others", "bots")}, "ignored_lines": 0,
              "ignored_files": [], "tool_files": [], "authors": [], "bulk_commits": [], "files": [],
              "truncated": False, "shallow": False, "partial_clone": None, "warnings": [], "note": NOTE}
    report["tool_files"] = [t for t in TOOL_FILES if (root / t).exists()] + [
        f"{sub}/{t}" for t in TOOL_FILES if sub and (root / sub / t).exists()]
    if git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}", check=False, timeout=left()) is None:
        report["warnings"].append("no commits yet on the current branch: nothing to attribute")
        return report
    paths = [f":(literal){sub}"] if sub else []
    cap = [f"--max-count={max_commits + 1}"] if max_commits > 0 else []
    partial = partial_clone(root, left())
    blobs = missing_objects(root, paths, left()) if partial else set()
    if blobs and missing_objects(root, paths, left(), "--filter=blob:none"):
        raise SystemExit(f"{root} is a partial clone ({partial[0] or 'unknown filter'}) without all of its folder "
                         "listings, so reading its history would download them: clone it again with "
                         "--filter=blob:limit=1m, then run this again")
    log = git(root, *LOG, "--date=short", "--format=%H%x00%an%x00%ae%x00%ad%x00%B", *cap, "HEAD", "--", *paths,
              timeout=left()).split(b"\0")
    commits = [[text(t) for t in log[i:i + 5]] for i in range(0, len(log) - 4, 5)]
    if any(not re.fullmatch(r"[0-9a-f]{40,64}", c[0]) for c in commits):
        raise SystemExit(f"unexpected git log output in {root}")
    if not commits:
        report["warnings"].append(f"no commits touch {sub}" if sub else "only merge commits: nothing to attribute")
        return report
    if max_commits > 0 and len(commits) > max_commits:
        commits = commits[:max_commits]
        report["truncated"] = True
        report["warnings"].append(f"history capped at the latest {max_commits} commits (from {commits[-1][3]}): "
                                  "older ones are left out; --max-commits 0 reads them all")
    boundary = set()
    if shallow_file.is_file():
        boundary = set(shallow_file.read_text(encoding="ascii", errors="replace").split())
        report["shallow"] = True
        oldest = min((c[3] for c in commits if c[0] in boundary), default="the oldest commit here")
        report["warnings"].append(f"shallow clone: history before {oldest} is missing and that commit's lines are "
                                  f'left out; run git -C "{root}" fetch --unshallow for the full picture')

    exclude, count_lines = [], True
    if partial:
        flt, remote = partial
        missing = missing_paths(root, paths, blobs, left())
        left_out, size_limit = sorted(missing), flt.startswith("blob:limit=")
        groups = fold(left_out, sub, MAX_LEFT_OUT) if missing and size_limit else None
        if groups:
            exclude, folders, left_out = [f":(exclude,literal){p}" for p in groups], groups != left_out, groups
            report["warnings"].append(f"partial clone ({flt}): {len(missing)} large file(s) not downloaded, left out "
                                      f"of the counts{' with the folders they are in' if folders else ''}: "
                                      + ", ".join(groups[:5]))
        elif missing and size_limit:  # a bigger limit is the fix, not the one it already has
            count_lines = False
            report["warnings"].append(f"partial clone ({flt}): {len(missing)} files are over its size limit, too many "
                                      "to leave out, so lines aren't counted. To count them, clone it again without "
                                      "--filter, then run this again")
        elif missing:
            fix = "re-clone it with --filter=blob:limit=1m"
            if re.fullmatch(r"[\w./ ~:+,=@-]+", str(root)) and re.fullmatch(r"[\w.-]+", remote):  # safe to paste
                fix = (f'run git -C "{root}" config remote.{remote}.partialclonefilter blob:limit=1m && '
                       f'git -C "{root}" fetch --refetch {remote} (git 2.36+), or {fix}')
            count_lines = False
            report["warnings"].append(f"partial clone ({flt or 'unknown filter'}): file contents weren't downloaded,"
                                      f" so lines aren't counted (that would fetch once per commit). To count "
                                      f"them, {fix}, then run this again")
        report["partial_clone"] = {"filter": flt, "left_out": left_out[:20], "lines_counted": count_lines}

    stats = {}
    if count_lines:
        stats = parse_numstat(git(root, *LOG, "--numstat", "--format=%x1e%H", *cap, "HEAD", "--",
                                  *(paths or ([":/"] if exclude else [])), *exclude, timeout=left()))
    seen = sorted({p for entries in stats.values() for _, p, _ in entries})
    attrs = linguist(root, seen, left())
    current = set(text(git(root, "--literal-pathspecs", "ls-tree", "-r", "-z", "--name-only", "--full-name", "HEAD",
                           "--", *([sub] if sub else []), timeout=left())).split("\0")) - {""}

    authors, files, bulk, skipped, moved, hits = {}, {}, [], {}, {}, set()
    totals = {"mine": 0, "mine_ai": 0, "others": 0, "bots": 0}
    for sha, name, email, date, body in commits:
        report["commits"] += 1
        bot = bool(BOT_AUTHOR.search(f"{name} {email}"))
        agent = bot and (ai_email(email) or ai_words(name.replace("[bot]", " "), bot=True))  # e.g. copilot-swe-agent
        ai = agent or is_ai_commit(body) or norm(name).endswith("(aider)")
        who = matches(name, email, me) if me else []
        if agent and me and not who:  # an agent's commit that credits the user who asked for it
            who = [i for n, e in co_authors(body) for i in matches(n, e, me)]
        hits.update(who)
        mine = bool(who) and (agent or not bot)
        kind = "bots" if bot and not mine else ("mine_ai" if ai else "mine") if mine else (
            "others" if me else ("mine_ai" if ai else "mine"))
        report["ai_commits"] += ai
        added_here = 0
        for added, path, old in ([] if sha in boundary else stats.get(sha, [])):
            path = moved.get(path, path)  # newest first: older lines of a moved file count against its current path
            if old:
                moved[old] = path
            if added is None:
                continue  # binary files
            if ignored(path, sub, attrs):
                skipped[path] = skipped.get(path, 0) + added
                continue
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
    unmatched = [i for i in me if i not in hits]
    if me and not hits:
        report["warnings"].append("none of the identities matches a commit author exactly (case and spacing don't "
                                  "matter): run without identities to list the authors")
    elif unmatched:
        names = ", ".join(f"'{i}'" for i in unmatched if "@" not in i)
        report["warnings"].append(f"{len(unmatched)} of the {len(me)} identities match no commit author"
                                  f"{' (' + names + ')' if names else ''}: fine if they're used in other projects; "
                                  "otherwise check them, and pass a name that contains a comma whole, with --me-file")
    total = sum(totals.values())
    report.update({
        "lines_added": total if count_lines else None,
        "share": {k: (round(100 * v / total) if total else 0) if count_lines else None for k, v in totals.items()},
        "ignored_lines": sum(skipped.values()),
        "ignored_files": [p for p, _ in sorted(skipped.items(), key=lambda kv: -kv[1])[:5]],
        "authors": sorted(authors.values(), key=lambda a: (-a["added"], -a["commits"]))[:10],
        "bulk_commits": sorted(bulk, key=lambda b: -b["added"])[:5],
        "files": sorted(files.values(), key=lambda f: -f["added"])[:top],
    })
    return report


def summary(r):
    s, counted = r["share"], r["lines_added"] is not None
    lines = [f"{r['repo']}{' (' + r['subdir'] + ')' if r['subdir'] else ''}: {r['commits']} commits, "
             f"{r['ai_commits']} credit an AI assistant"]
    lines += [f"warning: {w}" for w in r["warnings"]]
    if r["identities"] and r["lines_added"]:
        lines.append(f"lines added: you {s['mine']}%, you with AI {s['mine_ai']}%, others {s['others']}%, bots {s['bots']}%")
    elif not r["identities"] and r["authors"]:
        lines.append("authors (say which are you, then run again with --me):")
        lines += [f"  {a['name']} <{a['email']}>: {a['commits']} commits" + (f", +{a['added']} lines" if counted else "")
                  for a in r["authors"]]
    if r["ignored_lines"]:
        lines.append(f"left out: {r['ignored_lines']} lines in lockfiles and generated or vendored files "
                     f"({', '.join(r['ignored_files'])})")
    if r["tool_files"]:
        lines.append("AI tool files: " + ", ".join(r["tool_files"]))
    elif r["commits"] and not r["ai_commits"]:
        lines.append("AI share: unknown (no AI trailers or tool files; autocomplete and pasted code leave none)")
    for b in r["bulk_commits"]:
        lines.append(f"large commit {b['commit']} ({b['date']}, +{b['added']}): {b['subject']}")
    if r["files"]:
        lines.append("biggest files (added lines: you / you with AI / others):")
        lines += [f"  {f['path']}: {f['mine']} / {f['mine_ai']} / {f['others']}" for f in r["files"][:12]]
    lines.append(r["note"])
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo")
    p.add_argument("--me-file", metavar="PATH",
                   help='names and emails that are the user: a JSON list, or one per line ("-": standard input)')
    p.add_argument("--me", action="append", default=[],
                   help='names or emails that are the user, comma-separated (";" when a name has a comma); repeatable')
    p.add_argument("--subdir", help="only this folder of the repository")
    p.add_argument("--top", type=int, default=25, help="how many files to list")
    p.add_argument("--max-commits", type=int, default=MAX_COMMITS, help="read at most this many recent commits (0: all)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    me = split_identities(args.me) + (read_identities(args.me_file) if args.me_file else [])
    report = analyse(args.repo, me, args.subdir, args.top, args.max_commits)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else summary(report))


if __name__ == "__main__":
    main()
