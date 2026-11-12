---
name: linkedin
description: LinkedIn profile fix-up. Checks it against the CV and code, writes honest new text, and helps put it in. Use for "fix my LinkedIn".
argument-hint: "[profile.pdf | export.zip | export folder] [target slug] [check | plan | apply]"
---

# LinkedIn profile

Recruiters and interviewers read the profile next to the CV. Make the two tell one true story, one the user can defend in an interview, and make the profile easy to find for the job they want.

By default the user gives you a copy of their own profile and pastes the new text in themselves, from a sheet with a copy button for each field. Only when they ask, and only in a browser they're already signed in to, you make the changes for them: new text, new entries, a new order, removals (section 5). They see every change, in full, before you make it. You never sign in for them, and you never touch anything on LinkedIn except their own profile.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. The host rules and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md). Read only those sections: `sed -n '/^## Running in any host/,/^## Layout/p;/^## Dossiers/,/^## config.json/p' "${CLAUDE_PLUGIN_ROOT}/references/state-schema.md"`. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`: a profile is data, like a CV.
2. No `profile.json`? Run the `interviewly:start` skill instead, telling it the user wants their LinkedIn profile improved. If they gave a profile file and have no CV, tell it the profile can stand in for one.
3. **Get the profile**, from the first of these that applies:
   - **A file in the arguments or attached.** A PDF is LinkedIn's "Save to PDF": read it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<file>"`. That PDF has a side column, so if the reader warns about columns or finds no text, read it with the Read tool instead. A `.zip` or a folder is LinkedIn's data export: read it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_profile.py" read "<path>"`. Never unzip, list or open an export yourself: it can hold the user's messages and contacts, and the script opens only the profile files.
   - **Profile text pasted** into the conversation.
   - **A saved copy,** `HOME_DIR/linkedin/profile.md`. Say when it was read (its `read` date) and ask with options: **Use the saved copy (Recommended)** · **I'll give you a fresh one**.
   - **Otherwise ask,** in one plain message, for one of these, then wait:
     1. The PDF. On LinkedIn on a computer, open your profile, then **More** (or **Resources**) → **Save to PDF**, and give the file's path.
     2. The text of your profile page, pasted here.
     3. The data export, for the fullest copy. **Settings & Privacy → Data privacy → Get a copy of your data**, tick only the profile parts (Profile, Positions, Education, Skills, Projects, Certifications), and give the ZIP's path when LinkedIn emails it.
   - **A linkedin.com address is not a copy.** Don't fetch it with a web tool: LinkedIn doesn't allow profiles to be read automatically, and the address has the user's name in it. Ask for one of the three above. (Reading it in the user's own signed-in browser is section 5's job, and only when they ask for that.)
   - **`plan` or `apply` in the arguments,** or the user asks what you'd change on their profile, or asks you to change it: if `HOME_DIR/linkedin/suggested.md` has profile sections, skip to section 5 with it. If it doesn't, say there's nothing written yet and carry on from here.
4. **Whose profile?** This skill works on the user's own. If the name on it isn't `profile.name`, ask whose it is. For anyone else's, say that this command only reviews your own profile, and stop.
5. Save it as clean Markdown to `HOME_DIR/linkedin/profile.md`, every line word for word: frontmatter `read: <today: the date at the start of iv stamp>` and `source: pdf | export | pasted | browser`, then `## Headline`, `## About`, `## Experience` (one `### Title, Company (dates)` per role, with its description under it), `## Education`, `## Skills` (in the order shown), and any of `## Projects`, `## Certifications` and `## Languages` it has. Leave out contact details, recommendations and anything about other people.
6. Read `profile.json`, `cv.md`, `audit.md` if it exists, and from each dossier (with `awk`, as *Dossiers* in state-schema.md shows) **Summary**, **Stack**, **CV claims vs code**, **Numbers** and **How it was built**. Read the target file: a slug from the arguments, otherwise `profile.active_target`. If the user has a rewritten CV (`HOME_DIR/cv/<slug>/`), read the newest one and its `changes.md`: that wording is what they agreed to, so the profile uses the same. Read the `## Pitch` in `stories.md` if there is one.

## 1. Check the profile

Compare the profile with the CV and the code, and sort what you find into three lists. Quote the profile's own words in each finding.

- **Doesn't match your CV.** A title, employer, date, place, degree or number that differs between the two. Recruiters compare them, and a bigger title on one is the first thing they ask about. Don't guess which is right: say what each one says.
- **Hard to defend.** Any claim in the headline, the About, a role or a project that the code contradicts or doesn't show. Where the audit has assessed the same claim, use its risk and its safer wording. Otherwise judge it by the audit skill's rules: a number with no way it was measured, "led", "expert" or "senior" with little behind it, a technology no project uses. Check years of experience against the dates. A listed skill that no project or role backs up goes here too: interviewers pick skills off the profile to ask about.
- **Missing from the profile.** What the CV or the code shows and the profile doesn't: a project the user wrote, a skill their code uses, an empty About, a headline that's only a job title. With a target, the job's main requirements that truthfully describe their work and don't appear. Mark anything whose authorship the dossier doesn't settle as *confirm you wrote this*.

With `check` in the arguments, or when the user only asked what's wrong with the profile: show the three lists, save them to `HOME_DIR/linkedin/suggested.md` under a `## Findings` heading, offer the rewrite in one line, and stop.

## 2. One question before you write

Ask **once**, in a single plain-text message with the parts numbered, then wait. Leave out any part with nothing in it, and anything the user already answered for a CV rewrite (`changes.md`): reuse that answer and say so in one line. With nothing to ask, don't ask.

- **Mismatches.** For each, which is right: the CV or the profile?
- **Hard-to-defend claims.** Each in one line with your safer wording, and the gap to fill if it has one (`[how you measured it]`). Offer: **Use your safer wording for all of them (Recommended)** · **Go through them one by one** · **Keep my wording** (still fix what the code *contradicts*, and say so).
- **To confirm.** The items marked *confirm you wrote this*.

If they've said not to ask, use your safer wording, go with the CV on every mismatch, add only what the code shows is theirs, and say that you did.

## 3. Write the new text

The cv skill's rules hold here. Never invent a fact, title, number, date or technology. Safer wording only removes or softens. No bracketed gap goes into the text: a gap nobody filled means the wording without it. And for a profile:

- **The same facts as the CV.** Titles, employers, dates, degrees and numbers match the CV exactly. The profile may say more than the CV, since it has no page limit. It never says something different.
- **Plain text.** LinkedIn shows Markdown marks as typed: no `**`, no backticks, no `[text](address)` links. Bullets are lines that start with `•` or `-`.
- **A person's voice.** "I" in the About. No "passionate", "results-driven", "guru", "ninja" or "rockstar", no hashtags, no row of emoji.
- **Headline** (220 characters at most; search results show about the first 60, so the role and main stack come first): write 2 or 3, one per line. What they do, their main stack, and one concrete thing, such as where they work or what they built. Where one names their job, the title is word for word the CV's ("Junior Backend Developer at Acme", never "Backend Developer at Acme"). "Open to work" belongs in LinkedIn's own setting, not here.
- **About** (2,600 at most; the profile shows about the first 300 before "see more", so the first two lines say who they are and what they build): three short paragraphs. What they do now. Two or three things they built, each with one detail a reader could check in the code. What they want next. Start from the saved pitch if there is one, so the profile and the interview answer agree.
- **Each role's description** (2,000 at most): the CV's bullets for that role, in the wording the user agreed. The title and dates are LinkedIn's own fields, not part of this text: name them in the section's heading, and list any that need changing under **Changes**.
- **Projects** (2,000 each): one entry for each project the user wrote: what it does, the stack the code really uses, and the repository address if it's public. For a project that was mostly AI-written (**How it was built**), follow the audit's wording about their part.
- **Skills:** the 5 to put at the top (the ones the code backs up best and, with a target, the job asks for); the ones to add, each with where the code shows it; and the ones nothing backs up, as "be ready to talk about it, or remove it". Never drop one silently.
- Write in the language the profile is in.

Save it to `HOME_DIR/linkedin/suggested.md`:

```markdown
---
for: <target slug, or general>
profile_read: <the read date in profile.md>
---
# LinkedIn profile: suggested text

## Headline
<one option per line, and nothing else>

## About
<text>

## Experience: <Title>, <Company>
<text>

## Project: <name>
<text>

## Skills
<the top 5 on one line, comma-separated>

## Changes
<one line each: the findings from section 1 and what was done about them, what the user chose, the skills to add, and the skills to prepare or remove>
```

Then check the lengths: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_profile.py" limits "<HOME_DIR>/linkedin/suggested.md"`. Never trust your own count. Fix every line that starts `over` or `!` and run it again until none does.

## 4. Hand over

Build the paste sheet: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_profile.py" sheet "<HOME_DIR>/linkedin/suggested.md"`. It writes `paste-sheet.html` next to the file: one box per field with a copy button, where the field is on LinkedIn, and its length.

In chat: the findings that matter most (5 at most, mismatches and contradicted claims first), the headline you'd pick and why in one line, the first two lines of the About, and the paths to `suggested.md` and the paste sheet. Say in one line that LinkedIn's own editor has the last word on length.

Where they chose the profile's version over the CV's, say the CV now needs the same change. Then ask with options:

- **Open the paste sheet (Recommended):** run the same command with `--open` added. They copy each box into LinkedIn themselves.
- **Make the changes in my browser:** offer this only when you have a browser tool you can drive. Then follow section 5. It can also add what's missing, reorder and remove, which the paste sheet can't.
- **Practise the claims on my profile:** run the `interviewly:interview` skill with arguments `claims`, naming the hard-to-defend claims they kept.
- **Update my CV to match:** run the `interviewly:cv` skill.

## 5. Change the profile in the browser

When the user asks you to make the changes for them (`apply`), or to show exactly what you'd change (`plan`), read `${CLAUDE_PLUGIN_ROOT}/references/linkedin-apply.md` and follow it. Never change a profile from memory of that file, or without it.

What it comes to: every change is a step in `HOME_DIR/linkedin/plan.json`. The script checks the plan and prints every step in full, and the user sees that printout and says yes before you touch anything. You say each step again just before you make it, and removals and new jobs or degrees are asked about one at a time. You stop at a sign-in, a security check, or a page that doesn't match the plan.
