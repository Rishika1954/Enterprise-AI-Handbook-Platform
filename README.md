# Enterprise AI Employee - HCL Capital Branded Demo

A polished, ready-to-run Employee Handbook assistant with:
- FastAPI backend with logging, CORS, fuzzy handbook matching, and typed
  response models (see `/docs` for interactive API docs)
- Redesigned HTML/CSS/JavaScript frontend — navy/brass enterprise theme,
  department analytics, filterable employee directory, and a chat assistant
  with match-confidence scores and related-topic suggestions
- Employee directory with department filter chips and live search
- Handbook search / Q&A with confidence scoring and related sections
- PDF employee handbook
- No API key required

## What's new in this version
- **Backend:** `/api/stats`, `/api/departments`, employee search/filter query
  params, per-section handbook lookup, structured logging, CORS enabled,
  and a smarter answer-matching algorithm (keyword + fuzzy title match with
  a confidence score and related-topic suggestions).
- **Frontend:** a distinct enterprise visual identity (deep navy, brass gold,
  teal accent, serif/sans type pairing) instead of the previous generic
  purple-gradient look; a dashboard with department breakdown bars; color-
  coded employee cards; a chat assistant that shows match confidence and
  lets you tap into related handbook sections; and a browsable handbook
  page with a clickable table of contents instead of a raw text dump.

## Run on Mac

1. Open Terminal.
2. Go into this folder:
   cd Enterprise-AI-Employee-HCL-Branded

3. Create environment:
   python3 -m venv venv
   source venv/bin/activate

4. Install:
   pip install -r requirements.txt

5. Start:
   cd backend
   uvicorn main:app --reload --port 8020

6. Open:
   http://127.0.0.1:8020

If port 8020 is busy:
   lsof -ti :8020 | xargs kill -9
Then start the server again.

The application uses the handbook PDF as the source document. The backend extracts the handbook text at startup and performs simple relevant-section matching, so it works without an external AI API.
