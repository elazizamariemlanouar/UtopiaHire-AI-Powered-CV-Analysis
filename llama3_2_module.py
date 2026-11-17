import subprocess
import json
import re

LOG_FILE = "interview_log.json"  # fichier où la conversation sera sauvegarée

def parse_llama_json(response_text):
    """Essaie d’extraire le bloc JSON du modèle même si des caractères sont autour"""
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not match:
        return None
    json_str = match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def call_llama(language, job_role, company_name, interests, context, last_answer):
    prompt = f"""
You are a professional interviewer.
The interview will be held in {language}.
The role is: {job_role} at {company_name}.
The candidate's interests are: {interests}.
Here is the conversation so far: {context}.
The last answer from the candidate: {last_answer}.
the duration of the interview will be 10 minutes.
Analyze the answer for relevance and the quality of the language.
ask some questions related to the entreprise and then some technical questions and then behavioral skills 
Then generate the next interview question.
Respond with JSON ONLY. Do not include any explanations or extra text.

Return JSON ONLY with:
{{
    "analysis": {{
        "summary": "...",
        "strengths": "...",
        "weaknesses": "..."
    }},
    "new_question": "..."
}}
"""
    result = subprocess.run(
        ["ollama", "run", "llama3.2", prompt],  # pour Ollama 0.12.5
        capture_output=True,
        text=True
    )

    response_text = result.stdout.strip()

    data = parse_llama_json(response_text)
    if data is None:
        print("\n[⚠️] Le modèle n’a pas renvoyé de JSON valide. Voici la sortie brute :")
        print(response_text)
        return None

    # Ajouter des valeurs par défaut si elles manquent
    analysis = data.get("analysis", {})
    analysis.setdefault("summary", "")
    analysis.setdefault("strengths", "")
    analysis.setdefault("weaknesses", "")
  
    data["analysis"] = analysis

    return data

def save_log(history):
    """Sauvegarde l'historique dans un fichier JSON"""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def interview_session():
    print("=== 🎤 Entretien simulé avec LLaMA 3.2 ===\n")
    language = input("Which language you will choose? ")
    job_role = input("➡️  Poste visé : ")
    company_name = input("🏢 Entreprise : ")
    interests = input("💡 Centres d'intérêt du candidat : ")

    context = {}  # historique conversation sous forme dictionnaire {question: réponse}
    last_answer = ""
    history = []  # pour sauvegarder chaque tour de la conversation

    print("\n🧠 L’interview commence !\n")

    while True:
        response = call_llama(language, job_role, company_name, interests, context, last_answer)
        if response is None:
            # Si le JSON est invalide, continuer quand même
            last_answer = input("\n🧍‍♀️ Vous : ")
            continue

        analysis = response["analysis"]
        new_question = response["new_question"]

        print("\n🤖 Interviewer :", new_question)
     
        print(f"Résumé : {analysis['summary']}")

        # enregistrement du tour dans l'historique
        history.append({
            "question": new_question,
            "answer": last_answer,
            "analysis": analysis
        })

        # sauvegarde immédiate à chaque tour
        save_log(history)

        # réponse du candidat
        last_answer = input("\n🧍‍♀️ Vous : ")
        if last_answer.lower() in ["exit", "quit", "stop"]:
            print("\n🛑 Entretien terminé.")
            break

        # mise à jour du contexte
        context[new_question] = last_answer

if __name__ == "__main__":
    interview_session()
