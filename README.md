# 🩺 MediGuide AI

AI-powered medical symptom assessment and patient guidance assistant, built with **LangChain + Streamlit + OpenAI**.

> **⚠️ Medical disclaimer:** MediGuide AI is an educational prototype. It is **not** a doctor, **not** a diagnosis tool, and **not** an emergency service. It never gives a confirmed diagnosis. Always consult a qualified healthcare professional, and call your local emergency number in an emergency.

---

## Features

- Collects age, gender, symptoms (multiselect + free text), duration, severity, conditions, medications, notes and answer language
- Sends the data to an OpenAI model through a LangChain `LLMChain`
- Receives **structured JSON** and parses it safely (bad JSON never crashes the app)
- Shows a results dashboard: summary, general info, possible conditions (education only), urgency level (colour coded), next steps, questions for the doctor, warning signs
- **Streams** a plain-language guidance note live with `st.write_stream`
- **Caching:** in-memory and SQLite, switchable from the sidebar
- Disclaimers in the sidebar, the main area and the results
- Extra rule-based safety net: dangerous symptoms (e.g. chest pain + shortness of breath) can never be rated below HIGH/EMERGENCY, even if the model says otherwise

## Project structure

```
medical_ai_assistant/
├── app.py               # Streamlit UI (run this)
├── requirements.txt
├── .env.example         # copy to .env and add your key
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py        # settings + form options
│   ├── prompts.py       # PromptTemplate, ChatPromptTemplate, JSON schema
│   ├── chains.py        # ChatOpenAI, LLMChain, streaming, message demo
│   ├── cache_manager.py # in-memory + SQLite caching
│   └── utils.py         # safe JSON parsing + helpers
├── tests/
│   └── test_utils.py    # offline unit tests
└── docs/
    └── Medical_AI_Assignment.pdf
```

## Setup

1. **Python 3.10+** is required.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```
3. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Get an API key from <https://platform.openai.com> (API keys section).
5. Copy the example env file and add your key:
   ```bash
   cp .env.example .env            # Windows: copy .env.example .env
   ```
   Then edit `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
   `.env` is listed in `.gitignore` - **never commit it**.

## Run

```bash
streamlit run app.py
```

Run the offline tests (no API key needed):

```bash
python -m unittest discover -s tests -v
```

## How the LangChain concepts are used

| Concept | Where | What it does |
|---|---|---|
| `ChatOpenAI` | `src/chains.py` → `build_llm` | Connects to the OpenAI chat model |
| `PromptTemplate` | `src/prompts.py` → `PATIENT_PROMPT_TEMPLATE` | Reusable single-string template for patient data |
| `ChatPromptTemplate` | `src/prompts.py` → `ASSESSMENT_CHAT_TEMPLATE`, `NARRATIVE_CHAT_TEMPLATE` | System (safety rules) + Human (patient data) messages |
| `SystemMessage` / `HumanMessage` / `AIMessage` | `src/chains.py` → `raw_message_demo` | Builds a multi-turn conversation by hand |
| Structured JSON | `src/prompts.py` + `src/utils.py` | Schema in the prompt; fences stripped; `try/except` around `json.loads` |
| `LLMChain` | `src/chains.py` → `build_assessment_chain` | Reusable prompt + model pipeline |
| Streaming | `src/chains.py` → `stream_narrative` + `st.write_stream` | Typing effect using `llm.stream()` |
| Caching | `src/cache_manager.py` | `set_llm_cache(...)` with in-memory or SQLite cache |

**Data flow:** form input → build prompt inputs → select cache → build LLM + LLMChain → run chain → parse JSON → stream narrative → render dashboard.

## Caching: InMemoryCache vs SQLiteCache

Register a cache once with `set_llm_cache(...)`. LangChain then checks it automatically before every model call. If the same prompt and model settings were used before, the saved answer is returned instantly and **no API call is made**, which saves time and money.

| | InMemoryCache | SQLiteCache |
|---|---|---|
| Stored in | RAM (memory) | A file on disk (`mediguide_cache.db`) |
| Speed | Fastest | Fast, slightly slower |
| Survives restart? | No | Yes |
| Best for | One session | Reusing answers across sessions |

**Try it:** choose a cache in the sidebar, submit the same form twice, and compare the **Response time** metric. The second run should be much faster and give an identical result. (Cache keys include the model name and temperature, so changing them causes a new API call.)

## Test scenarios

| # | Input | Expected behaviour |
|---|---|---|
| 1 | Age 25, runny nose + sore throat, 1-3 days, severity 2 | Urgency LOW; calm monitoring advice |
| 2 | Age 40, fever + cough, 4-7 days, severity 6 | Urgency MEDIUM/HIGH; advises seeing a professional |
| 3 | Chest pain + shortness of breath | Urgency HIGH/EMERGENCY; urges immediate help |
| 4 | Same form twice (cache on) | Second run faster; identical result |
| 5 | Empty symptoms | Warning shown; API is **not** called |
| 6 | Answer language = Urdu | Guidance text is returned in Urdu |

## Notes

- The JSON `urgency_level` and all keys stay in English so the UI can colour them; all other text follows the chosen language.
- The model is run in OpenAI **JSON mode** for the assessment, and a parser still cleans fences/extra text as a second safety layer.
- Ideas for bonus marks: PDF report download, session history, urgency analytics chart, Docker.
