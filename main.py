"""
Enterprise AI Employee — HCL Capital
FastAPI backend serving the employee directory, the handbook assistant,
and the static frontend. No external API key required: handbook Q&A uses
local keyword + fuzzy section matching over the handbook text.
"""
import csv
import logging
import os
import re
import time
from collections import Counter
from difflib import SequenceMatcher
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Paths & app setup
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMPLOYEES_CSV = os.path.join(ROOT, "data", "employees.csv")
HANDBOOK_TXT = os.path.join(ROOT, "handbook", "HCL_Capital_Employee_Handbook.txt")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("hcl-ai-employee")

app = FastAPI(
    title="Enterprise AI Employee — HCL Capital",
    description="Employee directory and handbook Q&A assistant for HCL Capital.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STARTED_AT = time.time()


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class Question(BaseModel):
    question: str = Field(..., min_length=1, description="A natural-language employee question.")


class Employee(BaseModel):
    employee_id: str
    name: str
    department: str
    role: str
    location: str
    email: str
    joining_date: str


class AnswerMatch(BaseModel):
    title: str
    confidence: float


class Answer(BaseModel):
    answer: str
    source: str
    confidence: float
    related: list[AnswerMatch] = []


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def load_employees() -> list[dict]:
    if not os.path.exists(EMPLOYEES_CSV):
        log.warning("Employee file not found at %s", EMPLOYEES_CSV)
        return []
    with open(EMPLOYEES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    log.info("Loaded %d employee records", len(rows))
    return rows


def load_handbook() -> str:
    if not os.path.exists(HANDBOOK_TXT):
        log.warning("Handbook text not found at %s", HANDBOOK_TXT)
        return ""
    with open(HANDBOOK_TXT, encoding="utf-8") as f:
        text = f.read()
    log.info("Loaded handbook text (%d characters)", len(text))
    return text


def split_sections(text: str) -> list[dict]:
    """Split the handbook into {title, body, raw} sections on '## ' headers."""
    chunks = re.split(r"\n(?=## )", text)
    result = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith("## "):
            continue
        lines = chunk.splitlines()
        title = lines[0].replace("## ", "").strip()
        body = "\n".join(lines[1:]).strip()
        result.append({"title": title, "body": body, "raw": chunk})
    return result


employees: list[dict] = load_employees()
handbook: str = load_handbook()
sections: list[dict] = split_sections(handbook)

STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "did", "how", "what", "when",
    "where", "why", "can", "i", "to", "of", "for", "in", "on", "my", "me",
    "and", "or", "it", "this", "that", "please", "about",
}


def tokenize(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if w not in STOPWORDS}


# --------------------------------------------------------------------------
# Handbook Q&A matching
# --------------------------------------------------------------------------
def score_section(q_words: set, question: str, section: dict) -> float:
    """Blend keyword overlap with fuzzy title similarity for a robust score."""
    if not q_words:
        return 0.0

    body_words = tokenize(section["body"])
    title_words = tokenize(section["title"])

    overlap = len(q_words & body_words) / len(q_words)
    title_overlap = len(q_words & title_words) / len(q_words)
    fuzzy = SequenceMatcher(None, question.lower(), section["title"].lower()).ratio()

    return round(min(1.0, overlap * 0.6 + title_overlap * 0.9 + fuzzy * 0.25), 4)


def answer_question(question: str) -> Answer:
    q_words = tokenize(question)
    scored = sorted(
        ((score_section(q_words, question, s), s) for s in sections),
        key=lambda x: x[0],
        reverse=True,
    )
    scored = [(score, s) for score, s in scored if score > 0]

    if not scored:
        return Answer(
            answer=(
                "I couldn't find a matching section in the employee handbook. "
                "Try asking about leave, working hours, attendance, benefits, "
                "IT support, payroll, or the code of conduct."
            ),
            source="Employee Handbook",
            confidence=0.0,
            related=[],
        )

    best_score, best = scored[0]
    related = [
        AnswerMatch(title=s["title"], confidence=round(score, 2))
        for score, s in scored[1:4]
        if score > 0.15
    ]

    return Answer(
        answer=f"{best['title']}\n\n{best['body']}",
        source=f"Employee Handbook — {best['title']}",
        confidence=round(min(best_score, 1.0), 2),
        related=related,
    )


# --------------------------------------------------------------------------
# Routes — system
# --------------------------------------------------------------------------
@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "employees": len(employees),
        "handbook_sections": len(sections),
        "uptime_seconds": round(time.time() - STARTED_AT, 1),
    }


@app.get("/api/stats", tags=["System"])
def stats():
    departments = Counter(e["department"] for e in employees)
    return {
        "total_employees": len(employees),
        "departments": dict(departments),
        "handbook_sections": len(sections),
    }


# --------------------------------------------------------------------------
# Routes — employees
# --------------------------------------------------------------------------
@app.get("/api/employees", response_model=list[Employee], tags=["Employees"])
def get_employees(
    search: Optional[str] = Query(None, description="Free-text search across all fields."),
    department: Optional[str] = Query(None, description="Filter by exact department name."),
):
    results = employees
    if department:
        results = [e for e in results if e["department"].lower() == department.lower()]
    if search:
        q = search.lower()
        results = [e for e in results if any(q in str(v).lower() for v in e.values())]
    return results


@app.get("/api/departments", tags=["Employees"])
def get_departments():
    counts = Counter(e["department"] for e in employees)
    return [{"name": name, "count": count} for name, count in sorted(counts.items())]


@app.get("/api/employees/{employee_id}", response_model=Employee, tags=["Employees"])
def get_employee(employee_id: str):
    for e in employees:
        if e["employee_id"].lower() == employee_id.lower():
            return e
    raise HTTPException(status_code=404, detail=f"No employee found with id '{employee_id}'")


# --------------------------------------------------------------------------
# Routes — handbook assistant
# --------------------------------------------------------------------------
@app.post("/api/ask", response_model=Answer, tags=["Assistant"])
def ask(q: Question):
    if not q.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    return answer_question(q.question)


@app.get("/api/handbook", tags=["Assistant"])
def handbook_text():
    return {"content": handbook, "sections": [s["title"] for s in sections]}


@app.get("/api/handbook/{section_title}", tags=["Assistant"])
def handbook_section(section_title: str):
    for s in sections:
        if s["title"].lower() == section_title.lower():
            return s
    raise HTTPException(status_code=404, detail=f"No handbook section titled '{section_title}'")


# --------------------------------------------------------------------------
# Static frontend
# --------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.on_event("startup")
def on_startup():
    log.info(
        "Enterprise AI Employee ready — %d employees, %d handbook sections",
        len(employees), len(sections),
    )
