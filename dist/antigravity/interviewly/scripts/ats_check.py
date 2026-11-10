#!/usr/bin/env python3
"""Check a CV the way an applicant tracking system (ATS) reads it. Standard library only.

Give it the PDF you'll send. It extracts the text like a parser would and reports what
makes CVs parse badly or rank low:

  content    name and contact details at the top, standard section names, dates on every
             job in one format, bullet length, duty-only bullets, pronouns, odd symbols,
             punctuation, length, personal details most employers don't want
  keywords   coverage of the job's keywords (with common variants), as whole words
  pdf        real text (not an image), characters that read the same with and without
             /ActualText, in drawing order and in macOS PDFKit or pdftotext where they're
             installed, no words split at a hyphen, embedded fonts with Unicode maps, links
             that open, page count, no images, columns or header/footer text, title and tags

With --source (the Markdown the PDF was made from), it also checks that every word, link
and bold phrase of the source made it into the PDF. A .md file on its own gets the content,
link and keyword checks only. The score says how well software reads the CV, not how a
recruiter will judge it.

Usage:
  ats_check.py CV.pdf [--source CV.md] [--keywords-file FILE] [--max-pages 2] [--json]
--keywords-file takes one keyword per line or comma-separated, and "-" reads them from standard input:
keywords from a job ad never go on a command line. (--keywords "Python,FastAPI" still works.)
Exit code is 1 when anything fails, so a script can loop until it's clean.
"""
import argparse
import difflib
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

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
# English section names by stem, beyond the list above. Checked in order, so "Career Summary" is a summary,
# "Volunteer Experience" is volunteering and "Research Experience" is experience.
SECTION_KINDS = (
    ("summary", r"summary|profile|objective|about|personal statement|overview|introduction"),
    ("volunteering", r"volunteer"),
    ("experience", r"experience|employment|work history|internship|career|positions"),
    ("projects", r"project|portfolio"),
    ("skills", r"skill|competenc|technolog|tech stack|stack|tools|expertise|proficienc"),
    ("education", r"education|training|coursework|courses|academic|qualification|studies"),
    ("awards", r"award|honou?r|achievement|prize|scholarship"),
    ("certifications", r"certif|licen[cs]|accreditation"),
    ("publications", r"publication|talk|research|patent|presentation|conference"),
    ("languages", r"language"),
    ("interests", r"interest|hobb|activit|extracurricular"),
    ("leadership", r"leadership"),
    ("references", r"reference|referee"),
    ("contact", r"contact|personal (?:details|information)"),
)


def section_key(name):
    """A section name as STANDARD_SECTIONS spells it: lower case, no trailing colon, Turkish İ as i."""
    name = unicodedata.normalize("NFC", name.replace("İ", "i")).lower().replace("\u0307", "")
    return re.sub(r"\s+", " ", name).strip(" :")


def section_kind(name):
    """What a section holds ("experience", "projects", "skills", "education", ...), "other" for another name
    parsers know, or None for a name they won't place."""
    key = section_key(name or "")
    if key in EXPERIENCE_SECTIONS:
        return "projects" if re.search(r"pro[jy]e|progett", key) else "experience"
    if SKILLS_SECTION.search(key):
        return "skills"
    for kind, stems in SECTION_KINDS:
        if re.search(rf"\b(?:{stems})", key):
            return kind
    return "other" if key in STANDARD_SECTIONS else None


def is_skills_section(name):
    return section_kind(name) == "skills"


# Month names and abbreviations in the languages above, matched as whole words before a year
MONTHS = """jan january janv janvier januar jänner jän janeiro januari ene enero gen gennaio oca ocak
feb february fév fev févr fevr février fevrier februar febrero fevereiro febbraio februari şub şubat
mar march mars märz marz mär maerz mrz marzo março maart mrt mart
apr april avr avril abr abril aprile nis nisan
may mai mayo maio maggio mag mei mayıs
jun june juin juni junio junho giu giugno haz haziran
jul july juil juillet juli julio julho lug luglio tem temmuz
aug august août aout agosto ago augustus ağu ağustos
sep sept september septembre septiembre setiembre set setembro settembre eyl eylül
oct october octobre okt oktober octubre out outubro ott ottobre eki ekim
nov november novembre noviembre novembro kas kasım
dec december déc décembre decembre dez dezember diciembre dic dicembre dezembro ara aralık""".split()
MONTH = "(?:" + "|".join(sorted(set(MONTHS), key=len, reverse=True)) + r")\.?"
DATE_STYLES = {
    "Mon YYYY": re.compile(rf"\b{MONTH}\s+(19|20)\d\d\b", re.I),
    "MM/YYYY": re.compile(r"\b(0?[1-9]|1[0-2])/(19|20)\d\d\b"),
    "YYYY": re.compile(r"\b(19|20)\d\d\b"),
}
PRESENT = re.compile(r"\b(present|current|now|today|heute|aktuell|derzeit|actuel(?:le)?|actuellement|aujourd'hui|"
                     r"présent|en cours|actualidad|actualmente|presente|atual|attuale|oggi|heden|huidig|günümüz|"
                     r"halen|devam ediyor)\b", re.I)
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
YEARS_ONLY = re.compile(r"[\s(]*(?:(?:\d{1,2}[./])?(?:19|20)\d\d[\s().-]*)+")   # "2019 - 2024", "01.2020 - 06.2024"
PROFILE = re.compile(r"(?:linkedin\.com/in/|github\.com/|gitlab\.com/|bitbucket\.org/|behance\.net/|dribbble\.com/"
                     r"|stackoverflow\.com/users/)[\w-]+|https?://[\w-]+(?:\.[\w-]+)+|(?<![@\w.-])www\.[\w-]+(?:\.[\w-]+)+",
                     re.I)
SITE_LABEL = re.compile(r"(?:www\.)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?")   # a link whose text is its address
# "I" but not "I/O" or "Phase I"; my, me and myself, but not ME (engineering) or MY (Malaysia)
PRONOUNS = re.compile(r"(?<![\w/])(?<!Phase )(?<!Level )(?<!Type )(?<!Part )(?<!Stage )(?<!Tier )I(?![\w/]|-\w)"
                      r"|(?<![\w/])[Mm](?:e|y|yself)(?![\w/]|-\w)")
DUTY = re.compile(r"(responsible for|helped|assisted|worked on|involved in|participated in|tasked with|"
                  r"duties included|in charge of)\b", re.I)
PERSONAL = re.compile(r"\b(date of birth|birth ?date|d\.?o\.?b\b|born (?:on|in)\b|age\s*:|nationality|marital status|"
                      r"gender\s*:|religion\s*:|photo(?:graph)?\s*:|geburtsdatum|familienstand|staatsangehörigkeit|"
                      r"date de naissance|nationalité|situation familiale|fecha de nacimiento|estado civil|"
                      r"nacionalidad|data di nascita|stato civile|doğum tarihi|medeni hal)", re.I)
GENERIC_TITLE = re.compile(r"curriculum vitae|cv|r[ée]sum[ée]|lebenslauf|curr[ií]culo|özgeçmiş", re.I)
ODD_SYMBOLS = re.compile(r"[☀-➿\U0001F300-\U0001FAFF★☆➤➔►▶✓✔]")
INVISIBLE = re.compile("[\u00ad\u200b\u2060\ufeff]")   # soft hyphen, zero-width space, word joiner, byte-order mark
BAD_CHARS = {
    "a ligature": re.compile(r"[ﬀ-ﬆ]"),
    "a replacement character": re.compile("�"),
    "a private-use character": re.compile(r"[-]"),
    "a control character": re.compile(r"[\x00-\x08\x0b-\x1f\x7f]"),
    "an invisible character": INVISIBLE,
}
# Hebrew, Arabic and Indic scripts, and Chinese and Japanese. A browser writes these into a PDF as presentation
# forms, look-alike radicals or in visual order, so a parser that ignores ActualText reads them differently and
# this checker can't compare them with the source. No edit to the Markdown changes that: it is a warning.
HARD_SCRIPTS = re.compile("[\u0590-\u08ff\u0900-\u0dff\u2e80-\u2fdf\u3000-\u9fff\uf900-\ufaff\ufb1d-\ufdff\ufe70-\ufeff]")
BY_EYE = " (how a browser writes this script into a PDF: nothing in the Markdown changes it, so check those words by eye)"
BULLET = re.compile(r"^[•●▪■◦‣∙·*\-–]\s+")
VARIANTS = {
    "postgresql": ["postgres", "postgresql"], "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"], "kubernetes": ["kubernetes", "k8s"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
    "node.js": ["node.js", "nodejs", "node"], "amazon web services": ["aws", "amazon web services"],
    "machine learning": ["machine learning", "ml"], "rest": ["rest", "restful", "rest api", "rest apis"],
    "go": ["go", "golang"], "react": ["react", "react.js", "reactjs"], "vue": ["vue", "vue.js", "vuejs"],
    "express": ["express", "express.js", "expressjs"], "c#": ["c#", "csharp"], "c++": ["c++", "cpp"],
    ".net": [".net", "dotnet"], "google cloud": ["google cloud", "gcp", "google cloud platform"],
}
# Keywords that are also everyday words or letters ("go-live", "R&D", "the rest of", "react to", "Spring 2024"):
# they count only as a whole word in their usual capitals, in the text as written ("React-based" and "Go's" too),
# or in any case in a skills section's list ("languages: python, go")
LETTER = r"(?<!Series )(?<!Plan )(?<!Grade )(?<!Type )(?<!Phase )(?<!Level )(?<!Class )(?<!Vitamin )"
CASED = {
    "c": LETTER + r"C(?!-(?:suite|level)\b)", "r": LETTER + "R", "go": r"Go(?!-(?:live|to)\b)", "rest": "REST",
    "swift": "Swift", "express": "Express", "spring": r"Spring(?! (?:19|20)\d\d| semester| term)", "react": "React",
    "node": "Node", "rust": "Rust", "dart": "Dart", "spark": "Spark", "excel": "Excel",
}
WORDS_PER_PAGE = 650
SHORT_CV = 100
URL = r"(?:[^()\s]|\([^()\s]*\))+"   # may hold one level of brackets, as in wiki/Foo_(bar)
LINK = re.compile(r"(?<!!)\[([^\]]+)\]\((" + URL + r")\)")   # not an image: ![photo](me.jpg)
LOCAL_HOST = re.compile(r"localhost|.+\.(?:localhost|local|internal|lan|home\.arpa)", re.I)


class Unreadable(Exception):
    """A PDF that can't be parsed: a damaged or crafted file."""


def plain(text):
    """Text without what the PDF writer drops or redraws (pdf_render.tidy): format characters such as soft hyphens,
    zero-width characters and direction marks go, and a non-breaking hyphen is a hyphen."""
    return "".join(c for c in text.replace("\u2011", "-") if unicodedata.category(c) != "Cf")


def norm(text):
    """Lower case, letters (any script), digits and + # / . kept, invisible characters dropped, everything else a space."""
    text = unicodedata.normalize("NFC", plain(text).replace("İ", "i")).lower()
    return "".join(c if c in "+#/. " or unicodedata.category(c)[0] in "LNM" else " " for c in text)


def fold(text):
    """Text for comparing what a parser reads with the source: NFC, lower case (Turkish İ as i), no invisible
    characters, any run of spaces (no-break ones too) as one space. ß and ı stay as they are, so a name printed
    as GROSS or IŞIK still differs from Groß or Işık."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", plain(text).replace("İ", "i")).lower()).strip()


def tokens(text):
    return [w for w in (x.strip(".,;:!?()[]{}\"'“”‘’|•·–—") for x in fold(text).replace("•", " ").split()) if w]


def unspaced(ch):
    """Scripts written without spaces between words (Chinese, Japanese, Thai): no word boundary to check."""
    return "\u0e00" <= ch <= "\u0e7f" or "\u3040" <= ch <= "\u30ff" or "\u3400" <= ch <= "\u9fff" or "\uf900" <= ch <= "\ufaff"


def keyword_pattern(form):
    """The regex for one keyword form in norm()-ed text, or None when nothing of it is left (e.g. only symbols)."""
    core = norm(form).strip()
    if not core:
        return None
    before = "" if unspaced(core[0]) else r"(?<![^\s+#/.])"
    if unspaced(core[-1]):
        after = ""
    elif core[-1] in "+#":
        after = r"(?![^\W\d_]|[+#])"      # "C++" and "C++17"
    else:
        after = r"(?![^\s/.]|\.[^\W_])"   # "Python," and "Python/Django"; but "C" isn't in "C#", nor "Node" in "Node.js"
    return before + re.escape(core) + after


def keyword_forms(keyword):
    """(forms to find in norm()-ed text, case-sensitive patterns to find in the text as written)."""
    key = keyword.strip().replace("İ", "i").lower()
    forms = {key}
    for canonical, alts in VARIANTS.items():
        if key == canonical or key in alts:
            forms |= set(alts) | {canonical}
    return forms - set(CASED), [CASED[f] for f in sorted(forms) if f in CASED]


def keyword_found(keyword, haystack, raw=None, skills=""):
    """Whether the keyword or a common variant is in the text, as a whole word. haystack is norm(text); raw is the
    text as written, for keywords that are also everyday words or letters (Go, R, REST), and skills the lines of
    its skills sections, where those count in any case."""
    forms, cased = keyword_forms(keyword)
    if any(re.search(p, haystack) for p in map(keyword_pattern, forms) if p):
        return True
    raw = haystack if raw is None else raw
    before = r"(?<![\w.\-&@#+])"
    return (any(re.search(before + c + r"(?![\w+#&@]|\.\w|['’](?!s\b)\w)", raw) for c in cased)
            or any(re.search(before + c + r"(?![\w+#&@]|[-.'’]\w)", skills, re.I) for c in cased))


def web_link(url):
    """True for a link a recruiter can open: http(s) to a public host, mailto: or tel:. Not a local file,
    localhost, a private address or a script."""
    url = url.strip()
    m = re.match(r"(?i)https?://([^/?#]*)", url)
    if not m:
        return bool(re.match(r"(?i)(mailto|tel):\S", url))
    host = m.group(1).rsplit("@", 1)[-1]
    host = (host[1:host.find("]")] if host.startswith("[") else host.split(":")[0]).rstrip(".")
    if not host or LOCAL_HOST.fullmatch(host):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host   # a bare name ("intranet") only resolves inside one network


def find_phone(text):
    """A phone number: at least 8 digits, and not a year range such as 2019 - 2024."""
    for m in PHONE.finditer(text):
        if sum(c.isdigit() for c in m.group(0)) >= 8 and not YEARS_ONLY.fullmatch(m.group(0)):
            return m
    return None


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
    bare = re.sub(r"`[^`]*`", " ", LINK.sub(" ", md))   # cv_to_pdf doesn't link what's inside a code span
    out += [(e, "mailto:" + e) for e in EMAIL.findall(bare)]
    out += [(p, "https://" + p) for p in re.findall(r"(?<![\w/@.])(?:www\.)?(?:linkedin\.com|github\.com|gitlab\.com)/[^\s|,;()]*[^\s|,;().*`]", bare)]
    out += [(u, u) for u in re.findall(r"\bhttps?://[^\s<>()|]*[^\s<>()|.,;:*`]", bare)]
    return out


def url_key(url):
    url = unquote(url.strip()).lower()   # a PDF may carry zo%C3%AB where the source says zoë
    url = re.sub(r"^(https?://)?(www\.)?", "", url)
    return url.rstrip("/")


def original_links(path):
    """[(label, url)] of every link in the user's original CV file (PDF, Word, ODT, RTF or Markdown)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return joined_links((l["text"], l["uri"]) for l in pdf_text.Document(path).links)
    import cv_to_text
    converters = {".docx": cv_to_text.docx_to_text, ".odt": cv_to_text.odt_to_text, ".rtf": cv_to_text.rtf_to_text}
    text = (converters[path.suffix.lower()](path) if path.suffix.lower() in converters
            else path.read_text(encoding="utf-8-sig", errors="replace"))
    body, _, listed = text.partition("\n\nLinks in the file:\n")
    found = joined_links(md_links(body))
    have = {url_key(url) for _, url in found}
    for line in listed.splitlines():   # "- label: url": links the body's text doesn't show
        label, sep, url = line[2:].rpartition(": ")
        if sep and url_key(url) not in have:
            found.append((label.strip(), url.strip()))
            have.add(url_key(url))
    return found


def joined_links(links):
    """[(label, url)] with neighbouring pieces of one link (it wrapped onto a second line, or part of it is bold)
    counted as one link."""
    out = []
    for label, url in links:
        if out and url_key(out[-1][1]) == url_key(url):
            out[-1] = (f"{out[-1][0]} {label}".strip(), out[-1][1])
        else:
            out.append((label, url))
    return out


def links_kept(original, source):
    """Links the original CV had that the new one lost, or has on fewer lines."""
    before, after = {}, {}
    try:
        links = original_links(original)
    except Exception as e:   # an unreadable original shouldn't stop the other checks
        return "warn", f"couldn't read the links in the original CV: {e}"
    for label, url in links:
        if web_link(url):   # a link to a local file or localhost was never one a recruiter could open
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
    s = {"name": "", "top": [], "sections": [], "roles": [], "role_sections": [], "bullets": [], "lines": [],
         "images": len(re.findall(r"!\[[^\]]*\]\(", md))}
    section, raws, skills = None, [], []
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
            s["role_sections"].append(section)
        elif re.match(r"[-*+•] ", line):
            text = strip_md(line[2:].strip())
            if not is_skills_section(section):
                s["bullets"].append(text)
        else:
            text = strip_md(line)
        s["lines"].append(text)
        raws.append(line)
        if is_skills_section(section) and not line.startswith(("# ", "## ")):
            skills.append(text)
    s["top"] = s["lines"][:6]
    s["top_links"] = [(strip_md(label), url) for line in raws[:6] for label, url in LINK.findall(line)]
    s["text"], s["skills_text"] = "\n".join(s["lines"]), "\n".join(skills)
    return s


def structure_from_pdf(doc):
    """Best guess at the structure of a PDF that wasn't made from Markdown."""
    lines = [l for l in doc.lines if l.text.strip()]
    s = {"name": "", "top": [l.text for l in lines[:6]], "sections": [], "roles": [], "role_sections": [],
         "bullets": [], "lines": [l.text for l in lines], "text": doc.text(), "images": 0}
    top = " ".join(s["top"])
    s["top_links"] = [(l["text"], l["uri"]) for l in doc.links if l["page"] == 1 and l["text"] and l["text"] in top]
    if lines:   # the name: the first line, or much bigger text just below it ("CV" above the name), without a
        # sidebar heading that shares its line
        biggest = max(lines[:4], key=lambda l: l.size)
        line = biggest if biggest.size >= 1.4 * lines[0].size else lines[0]
        glyphs = [g for g in line.glyphs if g.size >= line.size - 0.5]
        s["name"] = pdf_text.Line(line.page, glyphs).text if glyphs else line.text
    sizes = sorted(l.size for l in lines) or [10]
    body = sizes[len(sizes) // 2]
    text_x, skills = None, []
    for l in lines[1:]:
        t = l.text.strip()
        words = t.split()
        in_skills = bool(s["sections"]) and is_skills_section(s["sections"][-1])
        if in_skills:
            skills.append(t)
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
            if in_skills:   # the next section's heading
                skills.pop()
            s["sections"].append(t.title() if t.isupper() else t)
        elif any(p.search(t) for p in DATE_STYLES.values()) and len(words) <= 25 and (l.bold or l.gaps):
            s["roles"].append(t)
            s["role_sections"].append(s["sections"][-1] if s["sections"] else None)
    s["skills_text"] = "\n".join(skills)
    return s


# ---------- checks ----------

def content_checks(s, add, pages=None):
    name = s["name"].strip()
    if not name or re.search(r"\d|@", name) or len(name.split()) > 8 or GENERIC_TITLE.fullmatch(name):
        add("fail", "name", f"the name reads {name!r}: put your full name on the first line")
    else:
        add("pass", "name", f"the name reads {name!r}" + (" (one word: fine if that's your full name)" if len(name.split()) == 1 else ""))

    top = " ".join(s["top"])
    site = any(SITE_LABEL.fullmatch(label.strip()) and re.match(r"(?i)https?://", url) for label, url in s.get("top_links", []))
    found = {"email": EMAIL.search(top), "phone": find_phone(top), "profile link": PROFILE.search(top) or site}
    missing = [k for k, v in found.items() if not v]
    detail = "email, phone and a profile link near the top" if not missing else f"not found near the top: {', '.join(missing)}"
    if "profile link" in missing and re.search(r"\b(linkedin|github|gitlab|portfolio|website)\b", top, re.I):
        detail += " (write the address out, e.g. linkedin.com/in/your-name, not just 'LinkedIn')"
    add("fail" if found["email"] is None else "warn" if missing else "pass", "contact", detail)

    sections = s["sections"]
    kinds = [section_kind(x) for x in sections]
    unknown = [x for x, k in zip(sections, kinds) if k is None]
    if not sections:
        add("fail", "sections", "no section headings found; use standard ones such as Experience, Education, Skills")
    else:
        detail = ", ".join(sections)
        if unknown:
            detail += f". Non-standard: {', '.join(unknown)} (ATS may not know where these belong)"
        add("warn" if unknown or not {"experience", "projects"} & set(kinds) or "skills" not in kinds else "pass",
            "sections", detail)

    # Dates matter for jobs: an undated project, or a degree given by year, is fine
    roles = s["roles"]
    where = s.get("role_sections") or [None] * len(roles)
    jobs = [r for r, sec in zip(roles, where) if section_kind(sec) in (None, "experience")]
    undated = [r for r in jobs if not any(p.search(r) for p in DATE_STYLES.values())]
    styles = {n for r in jobs for n, p in DATE_STYLES.items() if p.search(r) and n != "YYYY"}
    year_only = [r for r in jobs if DATE_STYLES["YYYY"].search(r) and not any(DATE_STYLES[k].search(r) for k in ("Mon YYYY", "MM/YYYY"))]
    if year_only and styles:
        styles.add("YYYY")
    present_forms = {m.group(0) for r in roles for m in [PRESENT.search(r)] if m}
    issues = []
    if undated:
        issues.append(f"no dates on: {'; '.join(r[:40] for r in undated[:3])} (ask the user; never guess dates)")
    if len(styles) > 1:
        issues.append(f"mixed date formats in the jobs ({', '.join(sorted(styles))}): use one format, months for every job "
                      f"where you know them, or years only; never add dates you don't have")
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
    duties = [b for b in bullets if DUTY.match(b)]
    if duties:
        issues.append(f"{len(duties)} bullet(s) list a duty rather than what was done, e.g. {duties[0][:40]!r}: say what "
                      f"they did and what came of it, from the code or the user (never invent results)")
    odd = [l for l in s["lines"] if ODD_SYMBOLS.search(l)]
    if odd:
        issues.append(f"unusual symbols or emoji on {len(odd)} line(s)")
    if len({b.endswith(".") for b in bullets}) > 1:
        issues.append("some bullets end with a full stop and some don't")
    if not bullets:
        issues.append("no bullet points found")
    add("warn" if issues else "pass", "bullets", "; ".join(issues) or f"{len(bullets)} bullets, concise and consistent")

    personal = [l for l in s["lines"] if PERSONAL.search(l)] + ["a photo"] * bool(s.get("images"))
    if personal:
        add("warn", "personal details", f"{len(personal)} line(s) with personal details, e.g. {personal[0][:40]!r}: jobs in the "
            f"UK, US, Ireland, Canada and Australia expect no date of birth, age, marital status, nationality, gender, "
            f"religion or photo (some countries, such as Germany, still use them; ask the user)")
    else:
        add("pass", "personal details", "no date of birth, marital status, nationality or photo")

    words = len(s["text"].split())
    if words < SHORT_CV:
        add("warn", "length", f"about {words} words, which is very short for a CV: add real detail about the work, "
            f"from the code or the user (never padding)")
    elif pages is None:
        est = words / WORDS_PER_PAGE
        add("warn" if est > 2.1 else "pass", "length", f"about {words} words, roughly {est:.1f} page(s)" + (": aim for two pages at most" if est > 2.1 else ""))


# macOS PDFKit is what Preview, Spotlight and copy-paste from a PDF use
PDFKIT = ("ObjC.import('PDFKit'); function run(argv) { var d = $.PDFDocument.alloc.initWithURL("
          "$.NSURL.fileURLWithPath(argv[0])); if (d.isNil()) return ''; var s = d.string; return s.isNil() ? '' : s.js; }")


def other_parsers(path):
    """{name: text} from the other PDF readers this machine has: macOS PDFKit and poppler's pdftotext."""
    commands = []
    if sys.platform == "darwin" and shutil.which("osascript"):
        commands.append(("macOS PDFKit", ["osascript", "-l", "JavaScript", "-e", PDFKIT, str(path)]))
    if shutil.which("pdftotext"):
        commands.append(("pdftotext", ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"]))
    out = {}
    for name, cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0 and text.strip():
            out[name] = text
    return out


def moved_passages(a, b):
    """Passages of word list a that b has somewhere else (not just missing or spelled differently)."""
    missing, extra = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            missing.append(" ".join(a[i1:i2]))
        if op in ("insert", "replace"):
            extra.append(" ".join(b[j1:j2]))
    return [m for m in missing if any(f" {m} " in f" {e} " for e in extra)]


def pdf_checks(doc, add, source=None, max_pages=2, extra_parsers=True):
    text, raw = doc.text(), doc.text(raw=True)
    words = re.findall(r"\w+", text)
    expected = len(re.findall(r"\w+", structure_from_markdown(source)["text"])) if source else None
    if len(words) < (expected / 2 if expected is not None else 50):
        undecodable = BAD_CHARS["a replacement character"].search(text) or any(not f.has_tounicode and f.type0 for f in doc.fonts)
        why = ("its fonts have no Unicode map, so the text can't be decoded; export it again with standard fonts"
               if undecodable else "the PDF is probably an image or a scan, which an ATS can't read")
        add("fail", "text", f"only {len(words)} words of real text: {why}")
        return
    add("pass", "text", f"{len(words)} words of selectable text")

    issues, fail = [], False
    lines_text, lines_raw = text.splitlines(), raw.splitlines()
    if raw != text:
        if len(lines_text) == len(lines_raw):
            diffs = [(r, t) for r, t in zip(lines_raw, lines_text) if r != t]
            by_eye = all(HARD_SCRIPTS.search(r + t) for r, t in diffs)
            fail = fail or not by_eye
            issues.append(f"{len(diffs)} line(s) read differently in parsers that ignore ActualText, e.g. {diffs[0][0][:50]!r}"
                          + (BY_EYE if by_eye else ""))
        else:
            fail = True
            extra = len(lines_raw) - len(lines_text)
            issues.append(f"spaces in some fonts map to line breaks, so many parsers see {extra} extra line breaks "
                          f"(e.g. a name or phrase split in two)")
    for what, pattern in BAD_CHARS.items():
        hits = [l for l in lines_raw if pattern.search(l)]
        if hits:
            by_eye = all(HARD_SCRIPTS.search(l) for l in hits)
            fail = fail or not by_eye
            issues.append(f"{what} on {len(hits)} line(s), e.g. {hits[0][:50]!r}" + (BY_EYE if by_eye else ""))
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
    checked = ["with and without ActualText", "in drawing order"]
    for name, other in (other_parsers(doc.path).items() if extra_parsers else ()):
        checked.append(f"in {name}")
        elsewhere = moved_passages(tokens(text), tokens(other))
        if elsewhere:
            issues.append(f"{len(elsewhere)} passage(s) read in a different order in {name}, e.g. {elsewhere[0][:40]!r}")
    add("fail" if fail else "warn" if issues else "pass", "characters", "; ".join(issues) or
        f"reads the same {', '.join(checked[:-1])} and {checked[-1]}; no ligatures, no words split across lines")

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
    bad = [l["uri"] for l in doc.links if not web_link(l["uri"])]
    if bad:
        fail = True
        issues.append(f"links that won't open for a recruiter (a local file or address, or a script): {', '.join(bad[:3])}")
    if source:
        want = md_links(source)
        local = [f"{label} ({url})" for label, url in want if not web_link(url)]
        missing = [f"{label} ({url})" for label, url in want if web_link(url) and url_key(url) not in have]
        if local:
            fail = True
            issues.append(f"links in the source a recruiter can't open: {'; '.join(dict.fromkeys(local))}; "
                          f"link a public https:// address or drop the link")
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
        issues.append(f"{images} image(s) or icon(s): any text in them is invisible to an ATS (and jobs in the UK, US, "
                      f"Ireland, Canada and Australia expect no photo)")
    columned = [l for l in doc.lines if any(x < doc.pages[l.page - 1].width * 0.6 for x in l.gaps)]
    if len(columned) > 5 and len(columned) > 0.15 * len(doc.lines):
        fail = True
        issues.append("text sits side by side in columns: many ATS read across both columns and mix them up")
    junk = [l.text for l in doc.lines if re.search(r"file://|^page \d+( of \d+)?$|^\d+\s*/\s*\d+$|\b\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}", l.text, re.I)]
    if junk:
        fail = True
        issues.append(f"browser or page header/footer text: {junk[0][:50]!r}")
    long_lines = [l for l in doc.lines if len(l.text) > 20]
    small = [l for l in long_lines if l.size < 8]
    if len(small) > len(long_lines) / 2:
        fail = True
        issues.append(f"most text is smaller than 8pt ({len(small)} of {len(long_lines)} lines), hard to read: a word or "
                      f"link too wide for the line makes a browser shrink the page; use [label](url) for long links")
    elif small:
        issues.append(f"{len(small)} line(s) in text smaller than 8pt")
    add("fail" if fail else "warn" if issues else "pass", "layout",
        "; ".join(issues) or "single column, no images, no header or footer text")

    if source:
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
        elif missing and all(HARD_SCRIPTS.search(m) for m in missing):
            add("warn", "fidelity", f"{len(missing)} passage(s) couldn't be compared with the source, e.g. {missing[0][:60]!r}" + BY_EYE)
        elif missing:
            missing.sort(key=lambda m: bool(HARD_SCRIPTS.search(m)))   # lead with one the user can fix
            split_link = re.search(r"https?://|www\.|\w\.\w+/", missing[0])
            add("fail", "fidelity", f"{len(missing)} passage(s) of the source missing or changed in the PDF, e.g. {missing[0][:60]!r}"
                + (f" (PDF has {extra[0][:40]!r})" if extra else "")
                + ("; a long address splits across lines, so link it as [label](url) instead" if split_link else ""))
        elif extra:
            add("warn", "fidelity", f"text in the PDF that isn't in the source, e.g. {extra[0][:60]!r}")
        else:
            add("pass", "fidelity", f"all {len(src)} words of the source are in the PDF, in order")

        bold_src = [strip_md(b) for line in source.splitlines() if not line.startswith("#")
                    for b in re.findall(r"\*\*(.+?)\*\*", line)]
        bold_pdf = Counter(w for line in doc.lines for w in tokens(" ".join(line.bold_runs())))
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


def analyse(path, keywords=None, source=None, max_pages=2, original=None, extra_parsers=True):
    path = Path(path)
    results = []

    def add(status, check, detail):
        results.append({"status": status, "check": check, "detail": detail})

    src_md = Path(source).read_text(encoding="utf-8-sig") if source else None
    if path.suffix.lower() == ".pdf":
        try:
            doc = pdf_text.Document(path)
        except pdf_text.TooComplex:
            raise
        except Exception as e:   # a malformed file: one line from main, not a traceback
            raise Unreadable(f"{path.name} isn't a readable PDF ({type(e).__name__}: {e}). Export it again.") from e
        if doc.encrypted:
            add("fail", "text", pdf_text.ENCRYPTED)
            return {"file": str(path), "score": 0, "fails": 1, "warnings": 0, "keyword_coverage": None,
                    "results": results}
        s = structure_from_markdown(src_md) if src_md else structure_from_pdf(doc)
        first = doc.lines[0].text.strip() if doc.lines else ""
        if src_md and fold(first) != fold(s["name"]) and HARD_SCRIPTS.search(first + s["name"]):
            add("warn", "reading order", f"the PDF's first line reads {first[:40]!r}, which couldn't be compared with your name" + BY_EYE)
        elif src_md and fold(first) != fold(s["name"]):
            add("fail", "reading order", f"the PDF's first line reads {first[:40]!r}, but an ATS takes the first line as your name")
        elif not src_md and s["name"] and fold(first) != fold(s["name"]):
            add("warn", "reading order", f"the PDF's first line reads {first[:40]!r}, not your name, and an ATS takes the "
                f"first line as your name")
        content_checks(s, add, pages=len(doc.pages))
        pdf_checks(doc, add, src_md, max_pages, extra_parsers)
        text = doc.text()
    else:
        md = path.read_text(encoding="utf-8-sig")
        s = structure_from_markdown(md)
        content_checks(s, add)
        local = [f"{label} ({url})" for label, url in md_links(md) if not web_link(url)]
        if local:
            add("fail", "links", f"links a recruiter can't open (a local file or address, or a script): "
                f"{'; '.join(dict.fromkeys(local))}; link a public https:// address or drop the link")
        text = s["text"]

    new_md = src_md if src_md is not None else (None if path.suffix.lower() == ".pdf" else md)
    if original and Path(original).exists() and new_md is not None:
        status, detail = links_kept(original, new_md)
        add(status, "links kept", detail)

    coverage = None
    keywords = [k for k in keywords or [] if keyword_pattern(k)]   # "C++" stays, "---" or "★" can't be matched
    if keywords:
        text = text.replace(s["name"], " ", 1) if s["name"] else text   # "Sam Go" doesn't know Go
        haystack = norm(text)
        present = [k for k in keywords if keyword_found(k, haystack, text, s["skills_text"])]
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
    p.add_argument("--keywords", help="comma-separated keywords from the job description (--keywords-file is safer)")
    p.add_argument("--keywords-file", metavar="FILE", help='keywords from the job description, one per line or '
                   'comma-separated; "-" reads them from standard input')
    p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--original", help="the user's original CV file, to check no link was lost")
    p.add_argument("--no-extra-parsers", action="store_true", help="don't also read the PDF with macOS PDFKit or pdftotext")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    listed = None if args.keywords_file == "-" else args.keywords_file
    for name, value in (("CV", args.cv), ("--source", args.source), ("--keywords-file", listed)):
        if value and not Path(value).is_file():
            sys.exit(f"not found: {value}" + ("" if name == "CV" else f" (the {name} file)"))
    keywords = args.keywords or ""
    if args.keywords_file:   # read as bytes, so a console's code page can't garble them
        raw = sys.stdin.buffer.read() if args.keywords_file == "-" else Path(listed).read_bytes()
        try:
            keywords += "\n" + raw.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            sys.exit(f"can't read the keywords as UTF-8 ({e}); save them as UTF-8 and try again")
    keywords = [re.sub(r"^[-*\u2022]\s+", "", k.strip()) for k in re.split(r"[,\n]", keywords)]   # "- Python" too
    keywords = list(dict.fromkeys(k for k in keywords if k))
    try:
        report = analyse(args.cv, keywords, args.source, args.max_pages, args.original, not args.no_extra_parsers)
    except UnicodeDecodeError as e:
        sys.exit(f"can't read the Markdown as UTF-8 ({e}); save it as UTF-8 and try again")
    except pdf_text.TooComplex as e:
        sys.exit(f"This PDF is too complex to read safely: {e}. Export it again.")
    except Unreadable as e:
        sys.exit(str(e))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        marks = {"pass": "✓", "warn": "⚠", "fail": "✗"}
        print(f"ATS readiness: {report['score']}/100 ({report['fails']} to fix, {report['warnings']} to consider)")
        print("  (how well software reads the CV, plus common content issues; not how a recruiter will judge it)")
        for r in report["results"]:
            print(f"  {marks[r['status']]} {r['check']}: {r['detail']}")
    sys.exit(1 if report["fails"] else 0)


if __name__ == "__main__":
    main()
