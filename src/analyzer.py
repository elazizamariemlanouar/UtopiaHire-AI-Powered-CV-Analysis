import re
import textstat
from langdetect import detect
import spacy
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util

# === Load all models once (production-friendly) ===
nlp_en = spacy.load("en_core_web_sm")
nlp_fr = spacy.load("fr_core_news_sm")

embed_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
kw_model = KeyBERT("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# ===============================
# LANGUAGE & READABILITY HELPERS
# ===============================
def detect_lang(txt):
    try:
        return detect(txt)
    except:
        return "en"

def readability_score(text, lang):
    if lang.startswith("en"):
        try:
            # Flesch can go below 0 or above 100: clamp it to a 0-100 scale
            return max(0, min(100, textstat.flesch_reading_ease(text)))
        except:
            pass
    # fallback for french
    sents = re.split(r"[.!?]\s+", text.strip())
    words = text.split()
    asl = len(words) / max(1, len(sents))
    return max(0, min(100, 100 - (asl - 12) * 4))

# ===============================
# SECTION PROCESSING
# ===============================

SECTION_HEADERS = {
    "personal_info": [r"personal information", r"contact", r"details", r"coordonnées"],
    "summary": [r"summary", r"objective", r"profile", r"résumé", r"profil"],
    "experience": [r"experience", r"employment", r"career", r"expérience", r"stages", r"travail"],
    "education": [r"education", r"academic", r"degree", r"diplôme", r"formation"],
    "projects": [r"projects", r"portfolio", r"projets", r"projets réalisés"],
    "skills": [r"skills", r"competencies", r"abilities", r"compétences"],
    "certifications": [r"certifications", r"licenses", r"certificat"],
    "achievements": [r"achievements", r"awards", r"honors", r"réalisations"],
    "languages": [r"languages", r"langues"],
    "interests": [r"interests", r"hobbies", r"centres d’intérêt"],
    "volunteering": [r"volunteering", r"community", r"vie associative"],
    "references": [r"references", r"referees"],
}


def split_sections(text):
    text_lower = text.lower()
    sections = {}
    current = "other"
    buffer = []

    for line in text_lower.split("\n"):
        matched = False
        for key, patterns in SECTION_HEADERS.items():
            if any(re.search(p, line, re.IGNORECASE) for p in patterns):
                if buffer:
                    sections[current] = "\n".join(buffer).strip()
                    buffer = []
                current = key
                matched = True
                break
        if not matched:
            buffer.append(line)

    if buffer:
        sections[current] = "\n".join(buffer).strip()
    return sections


def check_missing_sections(sections):
    critical = ["personal_info", "summary", "experience", "education", "skills"]
    optional = ["projects", "certifications", "achievements", "languages", "interests", "volunteering", "references"]

    missing_critical = [s for s in critical if s not in sections or not sections[s].strip()]
    missing_optional = [s for s in optional if s not in sections or not sections[s].strip()]

    return {
        "missing_critical": missing_critical,
        "suggested_optional": missing_optional
    }

# ===============================
# SECTION SCORING
# ===============================
def evaluate_section(name, content, job_desc, embed_model, nlp):
    score = 0
    details = {"strengths": [], "improvements": []}

    if not content or not content.strip():
        return 0, details

    if name == "personal_info":
        if "@" in content: score += 3
        if re.search(r"\d{4,}", content): score += 3
        if "linkedin" in content or "github" in content: score += 2
        if score >= 5:
            details["strengths"].append("Contains full contact information.")
        else:
            details["improvements"].append("Add email or LinkedIn link.")

    elif name == "summary":
        if len(content.split()) > 40: score += 5
        if any(w in content for w in ["experience", "skills", "motivated"]): score += 5
        if score >= 8:
            details["strengths"].append("Good professional summary.")
        else:
            details["improvements"].append("Add more detail about goals and expertise.")

    elif name == "experience":
        doc = nlp(content)
        verbs = [t for t in doc if t.pos_ == "VERB"]
        score += min(len(verbs) // 3, 10)

        if len(verbs) > 5:
            details["strengths"].append("Uses action verbs effectively.")
        else:
            details["improvements"].append("Add more action verbs to describe achievements.")

    elif name == "education":
        if "university" in content or "degree" in content:
            score += 5
        details["strengths"].append("Education listed.")

    elif name == "skills":
        resume_emb = embed_model.encode(content, convert_to_tensor=True)
        job_emb = embed_model.encode(job_desc, convert_to_tensor=True)
        sim = float(util.cos_sim(resume_emb, job_emb))
        score += int(sim * 10)
        details["strengths"].append(f"Skills relevant to job ({round(sim * 100, 1)}% match).")

    else:
        score += 5

    return min(score, 10), details

def compute_overall_score(section_scores):
    weights = {
        "personal_info": 5,
        "summary": 10,
        "experience": 30,
        "education": 15,
        "projects": 15,
        "skills": 25,
    }

    # each section is scored out of 10 -> overall score out of 100
    total = sum(section_scores.get(s, 0) * w for s, w in weights.items())
    return round(total / sum(weights.values()) * 10, 1)

# ===============================
# KEYWORD MATCHING
# ===============================
def extract_keywords_with_relevance(resume_text, job_text):
    resume_keywords = kw_model.extract_keywords(resume_text, top_n=10)
    job_keywords = kw_model.extract_keywords(job_text, top_n=10)
    job_kw_set = [w for w, _ in job_keywords]

    annotated = []
    for word, _ in resume_keywords:
        kw_emb = embed_model.encode(word, convert_to_tensor=True)
        job_embs = embed_model.encode(job_kw_set, convert_to_tensor=True)
        sims = util.cos_sim(kw_emb, job_embs).cpu().numpy()[0]
        max_sim = sims.max()
        tag = "strong" if max_sim > 0.6 else "weak"
        annotated.append((word, float(max_sim), tag))

    return annotated

# ===============================
# SUGGEST IMPROVEMENTS
# ===============================
def suggest_improvements(missing_keywords):
    suggestions = []
    for kw in missing_keywords:
        if "python" in kw or "sql" in kw:
            suggestions.append("Consider certifications like Google Data Analytics or Python for Everybody.")
        elif "marketing" in kw:
            suggestions.append("Take courses on SEO, Digital Strategy, or Meta Ads.")
        elif "leadership" in kw or "communication" in kw:
            suggestions.append("Improve leadership or public speaking skills.")
    if not suggestions:
        suggestions.append("Add more measurable achievements in your experiences.")
    return suggestions

# ===============================
# ATS FILTER SIMULATION
# ===============================
def ats_filter_score(report):
    score = 100
    reasons = []

    # missing critical sections
    missing_critical = report.get("missing_critical_sections", [])
    if missing_critical:
        penalty = 10 * len(missing_critical)
        score -= penalty
        reasons.append(f"Missing essential sections: {', '.join(missing_critical)} (-{penalty})")

    # keyword coverage
    keywords = report.get("keywords", [])
    strong_kw = len([k for k in keywords if k[2] == "strong"])
    total_kw = len(keywords)
    if total_kw > 0 and strong_kw / total_kw < 0.5:
        score -= 20
        reasons.append("Less than 50% of strong job-related keywords. (-20)")

    # structure issues
    if report["overall_score"] < 60:
        score -= 10
        reasons.append("Weak structure or content. (-10)")

    # final verdict
    if score >= 80:
        verdict = "Likely to pass ATS filters."
    elif score >= 60:
        verdict = "May pass ATS filters depending on employer."
    else:
        verdict = "High risk of rejection by ATS."

    return {
        "ats_score": score,
        "ats_verdict": verdict,
        "ats_reasons": reasons
    }

# ===============================
# MAIN ANALYZER
# ===============================
def analyze_resume_full(resume_text, job_desc):
    lang = detect_lang(resume_text)
    nlp = nlp_fr if lang.startswith("fr") else nlp_en

    sections = split_sections(resume_text)
    missing_info = check_missing_sections(sections)

    report = {
        "language": lang,
        "sections": {},
        "strengths": [],
        "improvements": [],
        "suggestions": [],
    }

    # section scoring
    for name, content in sections.items():
        score, fb = evaluate_section(name, content, job_desc, embed_model, nlp)
        report["sections"][name] = {"score": score, **fb}
        report["strengths"] += fb["strengths"]
        report["improvements"] += fb["improvements"]

    section_scores = {k: v["score"] for k, v in report["sections"].items()}
    report["overall_score"] = compute_overall_score(section_scores)

    report["missing_critical_sections"] = missing_info["missing_critical"]
    report["suggested_optional_sections"] = missing_info["suggested_optional"]

    # keyword relevance
    report["keywords"] = extract_keywords_with_relevance(resume_text, job_desc)
    weak_keywords = [k for k, _, tag in report["keywords"] if tag == "weak"]
    report["suggestions"] += suggest_improvements(weak_keywords)

    # ATS
    ats = ats_filter_score(report)
    report.update(ats)

    return report
