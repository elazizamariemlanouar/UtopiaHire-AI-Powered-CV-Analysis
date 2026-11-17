# llama_service.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import subprocess
import json
import re

app = FastAPI(title="LLaMA Interview Simulator")

LOG_FILE = "interview_log.json"  # conversation log

# === Helper functions ===
def parse_llama_json(response_text):
    """Extract JSON block from LLaMA output"""
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
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
The duration of the interview will be 10 minutes.
Analyze the answer for relevance and quality of the language.
Ask some questions related to the company, then technical questions, then behavioral skills.
Generate the next interview question.
Respond with JSON ONLY. Do not include explanations or extra text.

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
        ["ollama", "run", "llama3.2", prompt],
        capture_output=True,
        text=True
    )

    response_text = result.stdout.strip()
    data = parse_llama_json(response_text)
    if data is None:
        return None, response_text

    analysis = data.get("analysis", {})
    analysis.setdefault("summary", "")
    analysis.setdefault("strengths", "")
    analysis.setdefault("weaknesses", "")
    data["analysis"] = analysis

    return data, None

def save_log(history):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# === Server-side state ===
history = []  # conversation history

# === Ask for the static variables once at server start ===
print("=== LLaMA Interview Server Setup ===")
language = input("Choose interview language: ")
job_role = input("Job role: ")
company_name = input("Company name: ")
interests = input("Candidate interests: ")
print("\nServer ready! Waiting for POST requests...\n")

# === FastAPI endpoints ===
@app.get("/")
def read_root():
    return {"message": "Virtual Interview Simulator Backend is running!"}

@app.post("/receive_transcription")
async def receive_transcription(request: Request):
    global history
    data = await request.json()

    # The JSON sent by the speech-transcription service is the candidate's last answer
    last_answer = data

    # Context is the growing conversation
    context = history.copy()

    # Call LLaMA
    response, raw_output = call_llama(
        language, job_role, company_name, interests, context, last_answer
    )

    if response is None:
        raise HTTPException(
            status_code=500,
            detail=f"LLaMA did not return valid JSON. Output:\n{raw_output}"
        )

    # Append to server-side history
    history.append({
        "question": response["new_question"],
        "answer": last_answer,
        "analysis": response["analysis"]
    })
    save_log(history)

    # Return next question + analysis
    return {
        "new_question": response["new_question"],
        "analysis": response["analysis"]
    }
