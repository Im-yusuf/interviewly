#!/usr/bin/env python3
"""Check a CV the way an applicant tracking system (ATS) reads it. Standard library only.

Give it the PDF you'll send. It extracts the text like a parser would and reports what
makes CVs parse badly or rank low:

  content    name and contact details at the top, standard section names, dates on every
             role in one format, bullet length, pronouns, odd symbols, punctuation, length
  keywords   coverage of the job's keywords (with common variants), in the text an ATS sees
  pdf        real text (not an image), characters that read the same in every parser, no
             words split at a hyphen, embedded fonts with Unicode maps, clickable links,
             page count, no images, columns or header/footer text, title and tags

With --source (the Markdown the PDF was made from), it also checks that every word, link
and bold phrase of the source made it into the PDF. A .md file on its own gets the content
and keyword checks only.

Usage:
  ats_check.py CV.pdf [--source CV.md] [--keywords "Python,FastAPI,PostgreSQL"] [--max-pages 2] [--json]
Exit code is 1 when anything fails, so a script can loop until it's clean.
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_text  # noqa: E402

# Section names parsers know, in English, French, German, Spanish, Portuguese, Italian, Dutch and Turkish
# (lower case; see section_key)
EXPERIENCE_SECTIONS = {
    "experience", "work experience", "professional experience", "employment", "employment history", "projects",
    "expérience", "expériences", "expérience professionnelle", "expériences professionnelles", "parcours professionnel",
    "projets", "berufserfahrung", "erfahrung", "berufliche erfahrung", "beruflicher werdegang", "projekte",
    "experiencia", "experiencia laboral", "experiencia profesional", "proyectos", "experiência", "experiências",
    "experiência profissional", "projetos", "projectos", "esperienza", "esperienze", "esperienza professionale",
    "esperienze professionali", "esperienza lavorativa", "progetti", "werkervaring", "ervaring", "projecten",
    "deneyim", "deneyimler", "iş deneyimi", "profesyonel deneyim", "projeler",
}
STANDARD_SECTIONS = EXPERIENCE_SECTIONS | {
    "summary", "profile", "professional summary", "personal projects", "education", "skills", "technical skills",
    "certifications", "awards", "publications", "volunteering", "languages", "interests", "achievements",
    "leadership", "research",
    # French
    "résumé", "profil", "profil professionnel", "à propos", "projets personnels", "formation", "formations",
    "éducation", "diplômes", "compétences", "compétences techniques", "certifications", "langues",
    # German
    "zusammenfassung", "kurzprofil", "über mich", "ausbildung", "bildung", "bildungsweg", "studium", "kenntnisse",
    "fähigkeiten", "fachkenntnisse", "technische kenntnisse", "kompetenzen", "zertifikate", "zertifizierungen",
    "sprachen", "sprachkenntnisse",
    # Spanish
    "resumen", "perfil", "perfil profesional", "sobre mí", "educación", "formación", "formación académica",
    "habilidades", "habilidades técnicas", "competencias", "conocimientos", "certificaciones", "certificados",
    "idiomas",
    # Portuguese
    "resumo", "perfil profissional", "sobre mim", "educação", "formação", "formação académica", "formação acadêmica",
    "competências", "competências técnicas", "certificações", "línguas",
    # Italian
    "sommario", "riepilogo", "profilo", "profilo professionale", "istruzione", "formazione", "istruzione e formazione",
    "competenze", "competenze tecniche", "certificazioni", "lingue", "conoscenze linguistiche",
    # Dutch
    "samenvatting", "profiel", "over mij", "opleiding", "opleidingen", "vaardigheden", "competenties", "kennis",
    "certificaten", "certificeringen", "talen", "talenkennis",
    # Turkish
    "özet", "hakkımda", "eğitim", "eğitim bilgileri", "yetenekler", "beceriler", "yetkinlikler", "teknik beceriler",
    "sertifikalar", "diller", "yabancı diller",
}
SKILLS_SECTION = re.compile(r"skill|comp[eé]t[eéê]n|kompetenz|kenntnis|f[äa]e?higkeit|habilidad|vaardighe|yetenek|beceri|yetkinlik")


def section_key(name):
    """A section name as STANDARD_SECTIONS spells it: lower case, no trailing colon, Turkish İ as i."""
    name = unicodedata.normalize("NFC", name.replace("İ", "i")).lower().replace("\u0307", "")
    return re.sub(r"\s+", " ", name).strip(" :")


def is_skills_section(name):
    return bool(SKILLS_SECTION.search(section_key(name or "")))
MONTH = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
DATE_STYLES = {
    "Mon YYYY": re.compile(rf"\b{MONTH}\s+(19|20)\d\d\b", re.I),
    "MM/YYYY": re.compile(r"\b(0?[1-9]|1[0-2])/(19|20)\d\d\b"),
    "YYYY": re.compile(r"\b(19|20)\d\d\b"),
}
PRESENT = re.compile(r"\b(present|current|now)\b", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
PROFILE = re.compile(r"(linkedin\.com/in/[\w-]+|github\.com/[\w-]+)", re.I)
PRONOUNS = re.compile(r"\b(I|me|my|myself)\b")
ODD_SYMBOLS = re.compile(r"[☀-➿\U0001F300-\U0001FAFF★☆➤➔►▶✓✔]")
BAD_CHARS = {
    "a ligature": re.compile(r"[ﬀ-ﬆ]"),
    "a replacement character": re.compile("�"),
    "a private-use character": re.compile(r"[-]"),
    "a control character": re.compile(r"[\x00-\x08\x0b-\x1f\x7f]"),
    "an invisible character": re.compile(r"[­​-‍⁠﻿]"),
}
BULLET = re.compile(r"^[•●▪■◦‣∙·*\-–]\s+")
VARIANTS = {
    "postgresql": ["postgres", "postgresql"], "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"], "kubernetes": ["kubernetes", "k8s"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
    "node.js": ["node.js", "nodejs", "node"], "amazon web services": ["aws", "amazon web services"],
    "machine learning": ["machine learning", "ml"], "rest": ["rest", "restful", "rest api"],
}
WORDS_PER_PAGE = 650
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def norm(text):
    """Lower case, letters (any script), digits and + # / . kept, everything else a space."""
    text = unicodedata.normalize("NFC", text.replace("İ", "i")).lower()
    return "".join(c if c in "+#/. " or unicodedata.category(c)[0] in "LNM" else " " for c in text)


def unspaced(ch):
    """Scripts written without spaces between words (Chinese, Japanese, Thai): no word boundary to check."""
    return "\u0e00" <= ch <= "\u0e7f" or "\u3040" <= ch <= "\u30ff" or "\u3400" <= ch <= "\u9fff" or "\uf900" <= ch <= "\ufaff"


def keyword_pattern(form):
    """The regex for one keyword form in norm()-ed text, or None when nothing of it is left (e.g. only symbols)."""
    core = norm(form).strip()
    if not core:
        return None
    before = "" if unspaced(core[0]) else r"(?<![^\s+#/.])"
    after = "" if unspaced(core[-1]) else r"(?![^\s+#/.])"
    return before + re.escape(core) + after


def keyword_found(keyword, haystack):
    key = keyword.strip().replace("İ", "i").lower()
    forms = set(VARIANTS.get(key, [key]))
    for canonical, alts in VARIANTS.items():
        if key in alts:
            forms |= set(alts) | {canonical}
    patterns = [keyword_pattern(f) for f in forms]
    return any(re.search(p, haystack) for p in patterns if p)


def strip_md(text):
    """Visible text of a Markdown line: link labels, no emphasis marks."""
    text = LINK.sub(r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*|`([^`]+)`", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<![\w*\\])\*([^*\s](?:[^*]*[^*\s])?)\*(?![\w*])|(?<![\w_\\])_([^_\s](?:[^_]*[^_\s])?)_(?![\w_])",
                  lambda m: m.group(1) or m.group(2), text)
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", text)


def md_links(md):
    """Every link the PDF should carry: [label](url), bare emails and profile addresses."""
    out = [(strip_md(label), url) for label, url in LINK.findall(md)]
    bare = LINK.sub(" ", md)
    out += [(e, "mailto:" + e) for e in EMAIL.findall(bare)]
    out += [(p, "https://" + p) for p in re.findall(r"(?<![\w/@.])(?:www\.)?(?:linkedin\.com|github\.com|gitlab\.com)/[^\s|,;()]*[^\s|,;().]", bare)]
    out += [(u, u) for u in re.findall(r"\bhttps?://[^\s<>()|]*[^\s<>()|.,;:]", bare)]
    return out


def url_key(url):
    url = url.strip().lower()
    url = re.sub(r"^(https?://)?(www\.)?", "", url)
    return url.rstrip("/")


def original_links(path):
    """[(label, url)] of every link in the user's original CV file (PDF, Word, ODT, RTF or Markdown)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return [(l["text"], l["uri"]) for l in pdf_text.Document(path).links]
    import cv_to_text
    converters = {".docx": cv_to_text.docx_to_text, ".odt": cv_to_text.odt_to_text, ".rtf": cv_to_text.rtf_to_text}
    text = (converters[path.suffix.lower()](path) if path.suffix.lower() in converters
            else path.read_text(encoding="utf-8-sig", errors="replace"))
    body, _, listed = text.partition("\n\nLinks in the file:\n")
    found = md_links(body)
    if not found and listed:
        found = [tuple(x.strip() for x in line[2:].rsplit(": ", 1)) for line in listed.splitlines() if ": " in line]
    return found


def links_kept(original, source):
    """Links the original CV had that the new one lost, or has on fewer lines."""
    before, after = {}, {}
    try:
        links = original_links(original)
    except Exception as e:   # an unreadable original shouldn't stop the other checks
        return "warn", f"couldn't read the links in the original CV: {e}"
    for label, url in links:
        before.setdefault(url_key(url), [label, url, 0])[2] += 1
    for _, url in md_links(source):
        after[url_key(url)] = after.get(url_key(url), 0) + 1
    gone = [f"{label or url} ({url})" for key, (label, url, n) in before.items() if key not in after]
    fewer = [f"{label or url} ({n} → {after[key]})" for key, (label, url, n) in before.items() if 0 < after.get(key, 0) < n]
    if not before:
        return "pass", "the original CV has no links"
    if not gone and not fewer:
        return "pass", f"all {len(before)} links from the original CV are kept"
    detail = []
    if gone:
        detail.append(f"in the original but not the new CV: {'; '.join(gone)}")
    if fewer:
        detail.append(f"linked on fewer lines than in the original: {'; '.join(fewer)}")
    return "warn", ". ".join(detail) + " (keep them unless the user chose to drop them)"


# ---------- structure ----------

def structure_from_markdown(md):
    s = {"name": "", "top": [], "sections": [], "roles": [], "bullets": [], "lines": []}
    section = None
    for raw in md.splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", line):
            continue
        if line.startswith("# "):
            s["name"] = strip_md(line[2:]).strip()
            text = s["name"]
        elif line.startswith("## "):
            section = strip_md(line[3:]).strip()
            s["sections"].append(section)
            text = section
        elif line.startswith("###"):
            text = strip_md(line.lstrip("#").strip())
            s["roles"].append(text)
        elif re.match(r"[-*+•] ", line):
            text = strip_md(line[2:].strip())
            if not is_skills_section(section):
                s["bullets"].append(text)
        else:
            text = strip_md(line)
        s["lines"].append(text)
    s["top"] = s["lines"][:6]
    s["text"] = "\n".join(s["lines"])
    return s


def structure_from_pdf(doc):
    """Best guess at the structure of a PDF that wasn't made from Markdown."""
    lines = [l for l in doc.lines if l.text.strip()]
    s = {"name": lines[0].text if lines else "", "top": [l.text for l in lines[:6]],
         "sections": [], "roles": [], "bullets": [], "lines": [l.text for l in lines], "text": doc.text()}
    sizes = sorted(l.size for l in lines) or [10]
    body = sizes[len(sizes) // 2]
    text_x = None
    for l in lines[1:]:
        t = l.text.strip()
        words = t.split()
        if BULLET.match(t):
            s["bullets"].append(BULLET.sub("", t))
            after = [g for g in l.glyphs if g.text.strip()][1:2]
            text_x = after[0].x0 if after else l.x0
            continue
        if text_x is not None and abs(l.x0 - text_x) < 3 and not l.bold:
            s["bullets"][-1] += " " + t
            continue
        text_x = None
        if len(words) <= 4 and not re.search(r"\d", t) and (t.isupper() or (l.bold and l.size > body * 1.05)):
            s["sections"].append(t.title() if t.isupper() else t)
        elif any(p.search(t) for p in DATE_STYLES.values()) and len(words) <= 25 and (l.bold or l.gaps):
            s["roles"].append(t)
    return s


# ---------- checks ----------

def content_checks(s, add, pages=None):
    name = s["name"]
    name_ok = 2 <= len(name.split()) <= 5 and not re.search(r"\d|@", name)
    add("pass" if name_ok else "fail", "name", f"first line reads {name!r}" + ("" if name_ok else ": put your full name on the first line"))

    top = " ".join(s["top"])
    found = {"email": EMAIL.search(top), "phone": PHONE.search(top), "profile link": PROFILE.search(top)}
    missing = [k for k, v in found.items() if not v]
    detail = "email, phone and a profile link near the top" if not missing else f"not found near the top: {', '.join(missing)}"
    if "profile link" in missing and re.search(r"\b(linkedin|github)\b", top, re.I):
        detail += " (write the address out, e.g. linkedin.com/in/your-name, not just 'LinkedIn')"
    add("fail" if found["email"] is None else "warn" if missing else "pass", "contact", detail)

    sections = s["sections"]
    unknown = [x for x in sections if section_key(x) not in STANDARD_SECTIONS]
    lowered = {section_key(x) for x in sections}
    has_core = bool(lowered & EXPERIENCE_SECTIONS)
    if not sections:
        add("fail", "sections", "no section headings found; use standard ones such as Experience, Education, Skills")
    else:
        detail = ", ".join(sections)
        if unknown:
            detail += f". Non-standard: {', '.join(unknown)} (ATS may not know where these belong)"
        add("warn" if unknown or not has_core or not any(is_skills_section(x) for x in sections) else "pass",
            "sections", detail)

    roles = s["roles"]
    undated = [r for r in roles if not any(p.search(r) for p in DATE_STYLES.values())]
    styles = {n for r in roles for n, p in DATE_STYLES.items() if p.search(r) and n != "YYYY"}
    year_only = [r for r in roles if DATE_STYLES["YYYY"].search(r) and not any(DATE_STYLES[k].search(r) for k in ("Mon YYYY", "MM/YYYY"))]
    if year_only and styles:
        styles.add("YYYY")
    present_forms = {m.group(0) for r in roles for m in [PRESENT.search(r)] if m}
    issues = []
    if undated:
        issues.append(f"no dates on: {'; '.join(r[:40] for r in undated[:3])}")
    if len(styles) > 1:
        issues.append(f"mixed date formats ({', '.join(sorted(styles))}); pick one, e.g. 'Sep 2024 – Present'")
    if len(present_forms) > 1:
        issues.append(f"'present' written {len(present_forms)} ways")
    add("warn" if issues else "pass", "dates", "; ".join(issues) or f"{len(roles)} roles, consistent dates")

    bullets = s["bullets"]
    issues = []
    long_ones = [b for b in bullets if len(b.split()) > 32]
    if long_ones:
        issues.append(f"{len(long_ones)} bullet(s) over 32 words")
    if any(PRONOUNS.search(b) for b in bullets):
        issues.append(f"{sum(bool(PRONOUNS.search(b)) for b in bullets)} bullet(s) use I/me/my")
    odd = [l for l in s["lines"] if ODD_SYMBOLS.search(l)]
    if odd:
        issues.append(f"unusual symbols or emoji on {len(odd)} line(s)")
    if len({b.endswith(".") for b in bullets}) > 1:
        issues.append("some bullets end with a full stop and some don't")
    if not bullets:
        issues.append("no bullet points found")
    add("warn" if issues else "pass", "bullets", "; ".join(issues) or f"{len(bullets)} bullets, concise and consistent")

    words = len(s["text"].split())
    if pages is None:
        est = words / WORDS_PER_PAGE
        add("warn" if est > 2.1 else "pass", "length", f"about {words} words, roughly {est:.1f} page(s)" + (": aim for two pages at most" if est > 2.1 else ""))


def pdf_checks(doc, add, source=None, max_pages=2):
    text, raw = doc.text(), doc.text(raw=True)
    words = re.findall(r"\w+", text)
    if len(words) < 50:
        add("fail", "text", f"only {len(words)} words of real text: the PDF is probably an image or a scan, which an ATS can't read")
        return
    add("pass", "text", f"{len(words)} words of selectable text")

    issues, fail = [], False
    lines_text, lines_raw = text.splitlines(), raw.splitlines()
    if raw != text:
        fail = True
        if len(lines_text) == len(lines_raw):
            diffs = [(r, t) for r, t in zip(lines_raw, lines_text) if r != t]
            issues.append(f"{len(diffs)} line(s) read differently in parsers that ignore ActualText, e.g. {diffs[0][0][:50]!r}")
        else:
            extra = len(lines_raw) - len(lines_text)
            issues.append(f"spaces in some fonts map to line breaks, so many parsers see {extra} extra line breaks "
                          f"(e.g. a name or phrase split in two)")
    for what, pattern in BAD_CHARS.items():
        hits = [l for l in lines_raw if pattern.search(l)]
        if hits:
            fail = True
            issues.append(f"{what} on {len(hits)} line(s), e.g. {hits[0][:50]!r}")
    splits = [(a, b) for a, b in zip(doc.lines, doc.lines[1:])
              if a.page == b.page and re.search(r"[A-Za-z]-$", a.text) and re.match(r"[a-z]", b.text)]
    if splits:
        a, b = splits[0]
        issues.append(f"{len(splits)} word(s) split at a hyphen across lines, e.g. {a.text.split()[-1]!r} + {b.text.split()[0]!r}")
    drawn, read = doc.drawing_order_text().split(), text.split()
    moved = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, read, drawn, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            moved.append(" ".join(read[i1:i2]))
    if moved:
        issues.append(f"{len(moved)} passage(s) are drawn out of reading order, so parsers that read in drawing order "
                      f"see them out of place, e.g. {moved[0][:40]!r}")
    add("fail" if fail else "warn" if issues else "pass", "characters",
        "; ".join(issues) or "every character reads the same in every parser; no ligatures, no words split across lines")

    issues, fail = [], False
    loose = [f.base for f in doc.fonts if not f.embedded]
    unmapped = [f.base for f in doc.fonts if not f.has_tounicode and (f.type0 or f.encoding)]
    if unmapped:
        fail = True
        issues.append(f"no Unicode map for {', '.join(sorted(set(unmapped)))}: its text may come out as gibberish")
    if loose:
        issues.append(f"not embedded: {', '.join(sorted(set(loose)))} (looks different on other machines)")
    add("fail" if fail else "warn" if issues else "pass", "fonts",
        "; ".join(issues) or f"{len({f.base for f in doc.fonts})} font(s), all embedded with Unicode maps")

    issues, fail = [], False
    have = {url_key(l["uri"]) for l in doc.links}
    bad = [l["uri"] for l in doc.links if not re.match(r"(https?|mailto|tel):", l["uri"], re.I)]
    if bad:
        fail = True
        issues.append(f"links that won't open for a recruiter: {', '.join(bad[:3])}")
    if source:
        want = md_links(source)
        missing = [f"{label} ({url})" for label, url in want if url_key(url) not in have]
        if missing:
            fail = True
            issues.append(f"not clickable in the PDF: {'; '.join(dict.fromkeys(missing))}")
    elif not doc.links and (EMAIL.search(text) or PROFILE.search(text)):
        issues.append("the email and profile addresses aren't clickable")
    if doc.orphan_links:
        issues.append(f"{doc.orphan_links} link(s) aren't attached to a page, so many viewers won't make them clickable")
    empty = [l["uri"] for l in doc.links if not l["text"]]
    if empty:
        issues.append(f"{len(empty)} link(s) cover no visible text")
    add("fail" if fail else "warn" if issues else "pass", "links",
        "; ".join(issues) or f"{len(doc.links)} clickable link(s), all pointing where the text says")

    n = len(doc.pages)
    size = (round(doc.pages[0].width), round(doc.pages[0].height))
    paper = {(595, 842): "A4", (612, 792): "Letter"}.get(size, f"{size[0]}x{size[1]} pt")
    if n > max_pages:
        add("fail", "pages", f"{n} pages ({paper}); the limit is {max_pages}")
    else:
        add("warn" if paper not in ("A4", "Letter") else "pass", "pages",
            f"{n} page(s), {paper}" + ("" if paper in ("A4", "Letter") else ": use A4 or US Letter"))

    issues, fail = [], False
    images = sum(p.images for p in doc.pages)
    if images:
        issues.append(f"{images} image(s) or icon(s): any text in them is invisible to an ATS")
    columned = [l for l in doc.lines if any(x < doc.pages[l.page - 1].width * 0.6 for x in l.gaps)]
    if len(columned) > 5 and len(columned) > 0.15 * len(doc.lines):
        fail = True
        issues.append("text sits side by side in columns: many ATS read across both columns and mix them up")
    junk = [l.text for l in doc.lines if re.search(r"file://|^page \d+( of \d+)?$|^\d+\s*/\s*\d+$|\b\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}", l.text, re.I)]
    if junk:
        fail = True
        issues.append(f"browser or page header/footer text: {junk[0][:50]!r}")
    small = [l for l in doc.lines if l.size < 8 and len(l.text) > 20]
    if small:
        issues.append(f"{len(small)} line(s) in text smaller than 8pt")
    add("fail" if fail else "warn" if issues else "pass", "layout",
        "; ".join(issues) or "single column, no images, no header or footer text")

    if source:
        tokens = lambda t: [w for w in (x.strip(".,;:!?()[]{}\"'“”‘’|•·–—").lower() for x in t.replace("•", " ").split()) if w]
        src = tokens(structure_from_markdown(source)["text"])
        got = tokens(text)
        missing, extra = [], []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, src, got, autojunk=False).get_opcodes():
            if op in ("delete", "replace"):
                missing.append(" ".join(src[i1:i2]))
            if op in ("insert", "replace"):
                extra.append(" ".join(got[j1:j2]))
        moved = [m for m in missing if m in extra]
        if moved:
            add("fail", "fidelity", f"{len(moved)} passage(s) come out in a different order than in the source, e.g. "
                f"{moved[0][:60]!r}: a parser reads them out of place (often a date beside a heading that wraps)")
        elif missing:
            add("fail", "fidelity", f"{len(missing)} passage(s) of the source missing or changed in the PDF, e.g. {missing[0][:60]!r}"
                + (f" (PDF has {extra[0][:40]!r})" if extra else ""))
        elif extra:
            add("warn", "fidelity", f"text in the PDF that isn't in the source, e.g. {extra[0][:60]!r}")
        else:
            add("pass", "fidelity", f"all {len(src)} words of the source are in the PDF, in order")

        bold_src = [strip_md(b) for line in source.splitlines() if not line.startswith("#")
                    for b in re.findall(r"\*\*(.+?)\*\*", line)]
        bold_pdf = Counter(w for line in doc.lines for w in tokens(" ".join(x for x, b in line.words() if b)))
        lost = []
        for phrase in bold_src:
            ws = tokens(phrase)
            if any(bold_pdf[w] <= 0 for w in ws):
                lost.append(phrase)
            for w in ws:
                bold_pdf[w] -= 1
        if bold_src and len(lost) == len(bold_src):
            add("fail", "bold", f"none of the {len(bold_src)} bold phrases in the source are bold in the PDF")
        elif lost:
            add("warn", "bold", f"{len(lost)} of {len(bold_src)} bold phrase(s) aren't bold in the PDF, e.g. {lost[0][:50]!r}")
        elif bold_src:
            add("pass", "bold", f"all {len(bold_src)} bold phrases are bold in the PDF")

    issues = []
    title = str(doc.info.get("Title", "")).strip()
    if not title:
        issues.append("no document title (some ATS and email previews show it)")
    if not doc.tagged:
        issues.append("not tagged, so screen readers and some parsers can't tell headings from body text")
    if not doc.lang:
        issues.append("no document language set")
    add("warn" if issues else "pass", "document", "; ".join(issues) or f"title {title!r}, tagged, language {doc.lang}")


def analyse(path, keywords=None, source=None, max_pages=2, original=None):
    path = Path(path)
    results = []

    def add(status, check, detail):
        results.append({"status": status, "check": check, "detail": detail})

    src_md = Path(source).read_text(encoding="utf-8-sig") if source else None
    if path.suffix.lower() == ".pdf":
        doc = pdf_text.Document(path)
        if doc.encrypted:
            add("fail", "text", pdf_text.ENCRYPTED)
            return {"file": str(path), "score": 0, "fails": 1, "warnings": 0, "keyword_coverage": None,
                    "results": results}
        s = structure_from_markdown(src_md) if src_md else structure_from_pdf(doc)
        if src_md:
            first = doc.lines[0].text if doc.lines else ""
            if first.strip().lower() != s["name"].lower():
                add("fail", "reading order", f"the PDF's first line reads {first[:40]!r}, but an ATS takes the first line as your name")
        content_checks(s, add, pages=len(doc.pages))
        pdf_checks(doc, add, src_md, max_pages)
        haystack = norm(doc.text())
    else:
        md = path.read_text(encoding="utf-8-sig")
        s = structure_from_markdown(md)
        content_checks(s, add)
        haystack = norm(s["text"])

    new_md = src_md if src_md is not None else (None if path.suffix.lower() == ".pdf" else md)
    if original and Path(original).exists() and new_md is not None:
        status, detail = links_kept(original, new_md)
        add(status, "links kept", detail)

    coverage = None
    keywords = [k for k in keywords or [] if keyword_pattern(k)]   # "C++" stays, "---" or "★" can't be matched
    if keywords:
        present = [k for k in keywords if keyword_found(k, haystack)]
        absent = [k for k in keywords if k not in present]
        coverage = round(100 * len(present) / len(keywords))
        add("pass" if coverage >= 70 else "warn", "keywords",
            f"{coverage}% of the job's keywords ({len(present)}/{len(keywords)})" + (f"; missing: {', '.join(absent)}" if absent else ""))

    fails = sum(r["status"] == "fail" for r in results)
    warns = sum(r["status"] == "warn" for r in results)
    score = max(0, 100 - 20 * fails - 6 * warns)
    return {"file": str(path), "score": score, "fails": fails, "warnings": warns,
            "keyword_coverage": coverage, "results": results}


def main():
    for stream in (sys.stdout, sys.stderr):   # UTF-8 whatever the console's code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cv", help="the PDF to check (or a .md for content checks only)")
    p.add_argument("--source", help="the Markdown the PDF was made from")
    p.add_argument("--keywords", help="comma-separated keywords from the job description")
    p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--original", help="the user's original CV file, to check no link was lost")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    keywords = [k.strip() for k in (args.keywords or "").split(",") if k.strip()]
    for name, value in (("CV", args.cv), ("--source", args.source)):
        if value and not Path(value).is_file():
            sys.exit(f"not found: {value}" + ("" if name == "CV" else f" (the {name} file)"))
    try:
        report = analyse(args.cv, keywords, args.source, args.max_pages, args.original)
    except UnicodeDecodeError as e:
        sys.exit(f"can't read the Markdown as UTF-8 ({e}); save it as UTF-8 and try again")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        marks = {"pass": "✓", "warn": "⚠", "fail": "✗"}
        print(f"ATS readiness: {report['score']}/100 ({report['fails']} to fix, {report['warnings']} to consider)")
        for r in report["results"]:
            print(f"  {marks[r['status']]} {r['check']}: {r['detail']}")
    sys.exit(1 if report["fails"] else 0)


if __name__ == "__main__":
    main()
