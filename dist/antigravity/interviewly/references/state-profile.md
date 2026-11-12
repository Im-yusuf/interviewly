# State: the profile

`HOME_DIR/profile.json` says who the user is, and lists their skills and CV claims. Setup writes it.

## profile.json

```json
{
  "version": 1,
  "name": "Sam Rivera",
  "headline": "Backend developer, 2 years, Python",
  "target_level": "mid",
  "cv_path": "/Users/sam/Documents/cv.pdf",
  "cv_language": "en-GB",
  "github": "samrivera-example",
  "git_identities": ["Sam Rivera", "sam@example.com", "samrivera-example@users.noreply.github.com"],
  "updated": "2026-11-01",
  "active_target": "acme-backend-engineer",
  "skills": [
    {
      "name": "FastAPI",
      "slug": "fastapi",
      "category": "web-framework",
      "status": "strong",
      "cv_evidence": ["Built a task-management REST API with FastAPI and SQLAlchemy"],
      "code_evidence": ["fastapi-todo: app/main.py, app/routers/todos.py"],
      "projects": ["fastapi-todo"]
    }
  ],
  "claims": [
    {
      "id": "c1",
      "text": "Reduced p95 latency by 60% by moving database access to async",
      "project": "fastapi-todo",
      "type": "metric"
    }
  ]
}
```

- **Changing it**: read the file first and change only your own fields. Keep everything else, in particular `active_target`, `github`, `git_identities`, `cv_path` and every `gap` skill.
- `target_level`: `intern` | `junior` | `mid` | `senior` | `staff`. A "graduate" or "new grad" role is `junior`; students and placements are `intern`. When the active target has a `level`, that sets an interview's difficulty instead (see `state-targets.md`).
- `cv_path`: the CV file the user gave, or `null` when they had none. Setup then writes a minimal `cv.md` from the user's own answers only: the name and contact line, Education, and any jobs, internships or volunteering (title, organisation, dates, and their own words about each). Projects come from the code. `/interviewly:cv new` builds a full CV from it, then makes that CV the new `cv.md` and `cv_path`.
- `git_identities`: the names and emails the user commits under, confirmed in setup. `scripts/provenance.py --me-file -` reads them as a JSON list through a quoted heredoc and uses them to split each repo's history into the user's own lines, the user's lines in AI-credited commits, and other people's. Each dossier then gets **How it was built** and **Explain-risk** sections (see `agents/project-analyst.md`), which `/interviewly:larp-it`, the interview and the audit use.
- `cv_language`: the language the CV is written in, as a BCP 47 tag (`en-GB`, `en-US`, `fr-FR`, `de-DE`). Setup records it; the cv skill writes section headings in it and passes it to `cv_to_pdf.py --lang`.
- `github`: the user's GitHub username, if they gave one during setup.
- `active_target`: a slug in `targets/`, or `null`.
- `skills[].category`: one of the categories in `question-patterns.md`.
- `skills[].status`:
  - `strong`: on the CV and visible in code.
  - `cv-only`: on the CV, not found in any analysed code. These are the riskiest in interviews.
  - `code-only`: in the code but not on the CV. The CV may be underselling it, but only if the user wrote that code: setup notes in `code_evidence` when it's mostly other people's or AI-credited, and the dossier's **How it was built** and **Explain-risk** say more. Check before suggesting it for the CV.
  - `gap`: neither on the CV nor in any analysed code, but a job asks for it. `/interviewly:prep` adds it when the user preps a technology they don't have yet, so its topics count towards readiness.
- `claims[]`: setup's list of every CV bullet that states a number, a leadership or ownership role, a scope ("used by 10k users") or an expertise level, numbered `c1`, `c2` and so on. `type`: `metric` | `leadership` | `scope` | `technology` | `expertise`. It never holds risk or evidence: the audit stores those only in `audit.json`, keyed by the ids `iv audit-plan` gives each CV line (`c-<hash>`). Read risk from `audit.md` or `audit.json`, never from here.
