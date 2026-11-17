from analyzer import analyze_resume_full
from file_reader import extract_resume_text

def main():

    print("=== Résumé Analyzer ===")
    file_path = input("Enter the path to the résumé (PDF or DOCX): ").strip()
    job_desc = input("\nPaste the job description:\n\n")

    # Extract text
    try:
        resume_text = extract_resume_text(file_path)
    except Exception as e:
        print(f"\n❌ Error reading file: {e}")
        return

    # Analyze
    print("\nAnalyzing résumé...\n")
    report = analyze_resume_full(resume_text, job_desc)

    # === Display results ===
    print("\n=======================")
    print("📌 Résumé Analysis Report")
    print("=======================\n")

    print(f"Detected Language: {report['language']}")
    print(f"Overall Score: {report['overall_score']} / 100\n")

    print("🟢 Strengths:")
    for s in report["strengths"]:
        print(f"  - {s}")
    if not report["strengths"]:
        print("  None.")

    print("\n🟠 Improvements:")
    for s in report["improvements"]:
        print(f"  - {s}")
    if not report["improvements"]:
        print("  None.")

    print("\n📋 Missing Essential Sections:")
    if report["missing_critical_sections"]:
        for s in report["missing_critical_sections"]:
            print(f"  - {s}")
    else:
        print("  None")

    print("\n📎 Optional Sections Suggested:")
    if report["suggested_optional_sections"]:
        for s in report["suggested_optional_sections"]:
            print(f"  - {s}")
    else:
        print("  None")

    print("\n🔑 Keywords & Relevance:")
    for w, score, tag in report["keywords"]:
        label = "Strong Match" if tag == "strong" else "Weak Match"
        print(f"  - {w}: {round(score*100)}% → {label}")

    print("\n💡 Suggestions:")
    for s in report["suggestions"]:
        print(f"  - {s}")
    if not report["suggestions"]:
        print("  None.")

    print("\n🤖 ATS Filter Simulation:")
    print(f"ATS Score: {report['ats_score']} / 100")
    print(f"Verdict: {report['ats_verdict']}")
    for r in report["ats_reasons"]:
        print(f"  - {r}")

    print("\n=== Done. ===")

if __name__ == "__main__":
    main()
