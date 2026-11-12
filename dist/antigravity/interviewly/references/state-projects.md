# State: projects and dossiers

`HOME_DIR/projects/` holds `index.json`, with one entry per project, and one dossier per analysed project.

## projects/index.json

```json
[
  {
    "slug": "fastapi-todo",
    "name": "Taskly API",
    "path": "/Users/sam/code/fastapi-todo",
    "code": true,
    "repo_url": "https://github.com/samrivera-example/taskly",
    "public": true,
    "stack": ["Python", "FastAPI", "SQLAlchemy", "SQLite", "Docker", "pytest"],
    "cv_bullets": ["Built a task-management REST API with FastAPI and SQLAlchemy"],
    "analysed": "2026-11-01",
    "dossier": "projects/fastapi-todo.md"
  }
]
```

**Changing it**: read the file first, add or replace entries by `slug`, and never drop the others.

`dossier: null` means the project hasn't been analysed yet (see *Missing dossiers* in `common.md`). `code: false` marks a project known only from the CV (for example, work at a company whose code the user can't share). Its dossier is built from the CV alone. For a project inside a bigger repo (a monorepo or a team repo), `path` is the repo's top level and `subdir` is the project's folder inside it. `repo_url` is set when the code came from GitHub or another git host. Never save one with a `user:token@` part: strip it, and tell the user to re-clone without the token (git keeps the URL in the clone's `.git/config`). `public` is `true` only when GitHub says the repo is public: `gh`'s `visibility` is `PUBLIC` (`isPrivate` false), or the repo came from the unauthenticated public API listing. Everything else (a pasted git URL, a local folder, an entry without the field) counts as private.

## Dossiers

`projects/<slug>.md`, written by the project-analyst agent (the format is in `agents/project-analyst.md`). After its frontmatter come these `## ` sections: Summary, Stack, Architecture, Components, Key flows, Decisions and trade-offs, Non-obvious details, Weak spots, Probe points, CV claims vs code, Numbers, How it was built, Explain-risk. A CV-only dossier (`code: no`) has only Summary, CV claims vs code, Probe points and Weak spots.

Dossiers are long. Read only the sections a skill names, for example:

```bash
awk '/^## /{p=/^## (Summary|CV claims vs code|Numbers)$/} p' "<HOME_DIR>/projects/<slug>.md"
```

Without `awk`, read the file and use only those sections.
