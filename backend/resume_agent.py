"""
Resume Match agent: compares a job description with my resume profile.

It is rule-based, so it needs no AI provider, API key or internet connection,
and it always gives the same answer for the same input. Steps:

1. Find the skills a job description asks for, using a fixed skill dictionary.
2. Find the skills my resume shows, using the same dictionary.
3. Compare them: matched skills, missing skills and a match score.
4. Write a tailored summary by picking the resume highlights that best fit the
   job. It only reuses sentences I wrote, so it never invents experience.
"""

import re

# Each skill has a display name and the regular expressions that detect it.
# Word boundaries (\b) stop "java" matching inside "javascript", for example.
SKILLS = {
    "Python": [r"\bpython\b"],
    "SQL": [r"\bsql\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b"],
    "Java": [r"\bjava\b"],
    "C++": [r"\bc\+\+"],
    "C#": [r"\bc#"],
    "C": [r"\bc (?:programming|language)\b", r"\bc/c\+\+"],
    "HTML": [r"\bhtml5?\b"],
    "CSS": [r"\bcss3?\b"],
    "React": [r"\breact(?:\.?js)?\b"],
    "Angular": [r"\bangular\b"],
    "Node.js": [r"\bnode(?:\.?js)?\b"],
    "FastAPI": [r"\bfastapi\b"],
    "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"],
    "REST APIs": [r"\brest(?:ful)?(?: ?apis?)?\b", r"\bapi development\b"],
    "Microservices": [r"\bmicro-?services?\b"],
    "SQLAlchemy": [r"\bsqlalchemy\b"],
    "SQLite": [r"\bsqlite\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
    "MySQL": [r"\bmysql\b"],
    "MongoDB": [r"\bmongo(?:db)?\b"],
    "Git": [r"\bgit\b"],
    "GitHub": [r"\bgithub\b"],
    "GitLab": [r"\bgitlab\b"],
    "CI/CD": [r"\bci ?/ ?cd\b", r"\bcontinuous (?:integration|delivery|deployment)\b", r"\bpipelines?\b"],
    "Docker": [r"\bdocker\b", r"\bcontaineri[sz]"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Linux": [r"\blinux\b", r"\bunix\b"],
    "Testing": [r"\bpytest\b", r"\bunit[- ]?test", r"\btesting\b", r"\btest cases?\b"],
    "Debugging": [r"\bdebug"],
    "Data structures and algorithms": [r"\bdata structures?\b", r"\balgorithms?\b"],
    "OOP": [r"\bobject[- ]oriented\b", r"\boop\b"],
    "Pandas": [r"\bpandas\b"],
    "NumPy": [r"\bnumpy\b"],
    "Machine learning": [r"\bmachine learning\b", r"\bml\b"],
    "AI / LLMs": [r"\bai\b", r"\bartificial intelligence\b", r"\bllms?\b", r"\bgen ?ai\b"],
    "Automation": [r"\bautomat(?:e|ed|es|ing|ion)\b"],
    "Workflow automation": [r"\bworkflows?\b"],
    "Camunda": [r"\bcamunda\b"],
    "BPMN": [r"\bbpmn\b"],
    "LIMS": [r"\blims\b", r"\blaboratory information management\b"],
    "ELN": [r"\beln\b", r"\belectronic lab(?:oratory)? notebooks?\b"],
    "LabVantage": [r"\blabvantage\b"],
    "Life sciences": [r"\blife sciences?\b", r"\bpharma(?:ceutical)?s?\b", r"\bbiotech", r"\blaborator(?:y|ies)\b"],
    "Master data management": [r"\bmaster data\b"],
    "Data validation": [r"\bvalidat(?:e|ed|ing|ion)\b"],
    "Excel": [r"\bexcel\b"],
    "Agile": [r"\bagile\b", r"\bscrum\b"],
    "Jira": [r"\bjira\b"],
    "Client communication": [
        r"\bcommunication\b", r"\bclients?\b", r"\bcustomers?\b",
        r"\bstakeholders?\b", r"\bpresentations?\b", r"\bdemonstrations?\b",
    ],
    "Problem solving": [r"\bproblem[- ]solving\b"],
}

# Compile every pattern once when the module loads, not on every request.
COMPILED_SKILLS = {
    name: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for name, patterns in SKILLS.items()
}

YEARS_PATTERN = re.compile(r"(\d+)\s*(?:\+|-\s*\d+)?\s*(?:\+\s*)?years?", re.IGNORECASE)
TITLE_PATTERN = re.compile(r"^\s*(?:job title|title|position|role)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)

# Plain-English skill names are lowercased inside a sentence; product names keep their capitals.
GENERAL_SKILLS = {
    "Testing", "Debugging", "Data structures and algorithms", "Machine learning",
    "Automation", "Workflow automation", "Life sciences", "Master data management",
    "Data validation", "Client communication", "Problem solving",
}

SUMMARY_HIGHLIGHT_COUNT = 3
SUMMARY_SKILL_COUNT = 4


def find_skills(text: str) -> list[str]:
    """Return the skills mentioned in the text, in dictionary order."""
    return [
        name
        for name, patterns in COMPILED_SKILLS.items()
        if any(pattern.search(text) for pattern in patterns)
    ]


def find_years_required(job_description: str) -> int | None:
    """Return the smallest 'N years' figure in the job description, if any."""
    years = [int(match) for match in YEARS_PATTERN.findall(job_description)]
    years = [value for value in years if 0 < value <= 30]
    return min(years) if years else None


def find_job_title(job_description: str) -> str | None:
    match = TITLE_PATTERN.search(job_description)
    return match.group(1).strip() if match else None


def split_lines(text: str) -> list[str]:
    return [line.strip(" -•\t") for line in text.splitlines() if line.strip(" -•\t")]


def pick_highlights(highlights: list[str], wanted_skills: set[str]) -> list[str]:
    """
    Score each highlight by the job skills it mentions, keep the
    best few, and return them in their original order so the summary reads naturally.
    """
    scored = []
    for position, sentence in enumerate(highlights):
        shared = set(find_skills(sentence)) & wanted_skills
        # Technical skills count fully; general ones like "client communication" count half,
        # so a highlight is chosen for the tools it shows, not just for mentioning clients.
        score = sum(0.5 if skill in GENERAL_SKILLS else 1 for skill in shared)
        scored.append((score, position, sentence))

    # Highest score first; on a tie, the highlight written earlier wins.
    best = sorted(scored, key=lambda item: (-item[0], item[1]))[:SUMMARY_HIGHLIGHT_COUNT]
    return [sentence for _, _, sentence in sorted(best, key=lambda item: item[1])]


def build_summary(intro: str, matched: list[str], highlights: list[str]) -> str:
    intro = intro.strip().rstrip(".")
    if matched:
        skills = [
            skill.lower() if skill in GENERAL_SKILLS else skill
            for skill in matched[:SUMMARY_SKILL_COUNT]
        ]
        skill_text = skills[0] if len(skills) == 1 else ", ".join(skills[:-1]) + " and " + skills[-1]
        opening = f"{intro}, with hands-on experience in {skill_text}."
    else:
        opening = f"{intro}."

    sentences = [opening] + [s if s.endswith(".") else s + "." for s in highlights]
    return " ".join(sentences)


def analyze(job_description: str, profile: dict) -> dict:
    """Compare a job description with the resume profile and suggest a summary."""
    job_skills = find_skills(job_description)
    resume_text = "\n".join([profile["intro"], profile["skills"], profile["highlights"]])
    resume_skills = set(find_skills(resume_text))

    matched = [skill for skill in job_skills if skill in resume_skills]
    missing = [skill for skill in job_skills if skill not in resume_skills]
    score = round(len(matched) / len(job_skills) * 100) if job_skills else 0

    highlights = pick_highlights(split_lines(profile["highlights"]), set(job_skills))

    return {
        "job_title": find_job_title(job_description),
        "years_required": find_years_required(job_description),
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "tailored_summary": build_summary(profile["intro"], matched, highlights),
    }
