import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH_LOCAL = BASE_DIR / ".env"
ENV_PATH_PARENT = BASE_DIR.parent / ".env"

if ENV_PATH_LOCAL.exists():
    load_dotenv(dotenv_path=ENV_PATH_LOCAL)
elif ENV_PATH_PARENT.exists():
    load_dotenv(dotenv_path=ENV_PATH_PARENT)
else:
    load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

model = "openai/gpt-oss-120b"

# Cache resume object globally
cached_resume: "Resume | None" = None


class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = []


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience_years: float | None = None

    skills: list[str] = []
    experiences: list[Experience] = []
    education: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []


resume_schema = Resume.model_json_schema()


class ChatRequest(BaseModel):
    question: str
    history: list[dict] | None = None


def read_pdf(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"Resume file not found at {file_path}")
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def parse_resume(resume_text: str) -> Resume:
    system_prompt = f"""
    You are an expert resume parser.

    Extract information from the resume based on its meaning,
    not only based on exact section headings.

    Different resumes may use different headings.
    For example:
    - Experience
    - Professional Experience
    - Work History
    - Employment
    - Internships

    These may all contain relevant experience.
    Skills may also appear in the skills section, work experience,
    internships or projects.

    Return ONLY valid JSON matching this schema:

    {resume_schema}

    Important rules:
    1. Do not invent information.
    2. If a value is not available, return null.
    3. If a list has no information, return an empty list.
    4. Include internships inside experiences.
    5. Extract skills mentioned across the entire resume.
    """
    user_prompt = f"Parse the following resume:\n\n{resume_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"}
    )
    raw_output = response.choices[0].message.content
    data = json.loads(raw_output)
    return Resume(**data)


def get_or_load_resume() -> Resume:
    global cached_resume
    if cached_resume is not None:
        return cached_resume

    pdf_path = BASE_DIR / "Tanishq_Resume.pdf"
    if not pdf_path.exists():
        pdf_path = BASE_DIR.parent / "Tanishq_Resume.pdf"

    print(f"[INFO] Reading resume from: {pdf_path}")
    resume_text = read_pdf(pdf_path)

    if client is not None and os.getenv("GROQ_API_KEY"):
        print("[INFO] Parsing resume using Groq LLM...")
        cached_resume = parse_resume(resume_text)
        print("[INFO] Resume parsed and cached successfully!")
    else:
        print("[WARNING] GROQ_API_KEY not found. Resume caching fallback initialized.")
        cached_resume = Resume(
            name="Tanishq",
            skills=[],
            experiences=[],
            education=[],
            projects=[],
            certifications=[]
        )
    return cached_resume


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load and cache resume
    try:
        get_or_load_resume()
    except Exception as e:
        print(f"[ERROR] Failed to parse resume at startup: {e}")
    yield


app = FastAPI(title="Tanishq Portfolio AI Assistant API", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ask_candidate(question: str, history: list[dict] | None, resume: Resume) -> str:
    system_prompt = f"""
You are an AI assistant representing Tanishq (the candidate) on his portfolio website.

Below is everything you know about Tanishq:

{resume.model_dump_json(indent=2)}

Rules:
1. Answer only using this resume information.
2. Never hallucinate or assume facts not present in the resume.
3. If information is unavailable, say:
"I don't have enough information to answer that."
4. Be professional, friendly, and concise.
5. Answer as if HR or a recruiter is interviewing the candidate. Speak politely and accurately on Tanishq's behalf.
"""

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for turn in history:
            role = turn.get("role")
            content = turn.get("content")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    return response.choices[0].message.content


@app.get("/")
def home():
    return {
        "status": "healthy",
        "service": "Tanishq Portfolio Ask-Me AI Assistant Backend",
        "resume_cached": cached_resume is not None
    }


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        resume = get_or_load_resume()
        answer = ask_candidate(request.question.strip(), request.history, resume)
        return {"answer": answer}
    except Exception as e:
        print(f"[ERROR] Error processing chat request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
