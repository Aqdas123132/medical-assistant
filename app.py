"""
app.py - Streamlit user interface for MediGuide AI.

Run with:   streamlit run app.py

Pages (after login):
  New assessment | My history | Analytics | Admin (admin account only)

Data flow of an assessment:
  form input -> build prompt inputs -> select cache -> build LLM + LLMChain
  -> run chain -> parse JSON -> save to history -> stream narrative
  -> render dashboard -> follow-up chat
"""

import time
from collections import Counter

import pandas as pd
import streamlit as st

from src import auth, database, report, theme
from src.cache_manager import clear_memory_cache, configure_cache
from src.chains import (
    USING_LLMCHAIN,
    build_assessment_chain,
    build_llm,
    raw_message_demo,
    run_assessment,
    stream_followup,
    stream_narrative,
)
from src.config import (
    CACHE_MODES,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DISCLAIMER_LONG,
    DISCLAIMER_SHORT,
    DURATION_OPTIONS,
    GENDER_OPTIONS,
    LANGUAGE_OPTIONS,
    MODEL_OPTIONS,
    SYMPTOM_OPTIONS,
    URGENCY_COLORS,
    URGENCY_LEVELS,
    URGENCY_MESSAGES,
)
from src.utils import (
    apply_safety_floor,
    assessment_to_inputs,
    build_chain_inputs,
    build_symptom_list,
    normalize_result,
    safe_parse_json,
    validate_age,
)

st.set_page_config(page_title="MediGuide AI", page_icon="🩺", layout="wide")

PAGE_NEW = "New assessment"
PAGE_HISTORY = "My history"
PAGE_ANALYTICS = "Analytics"
PAGE_ADMIN = "Admin"


@st.cache_resource
def _prepare_database():
    """Create the database tables once per server start."""
    database.init_db()
    return True


# ==========================================================================
# Small shared helpers
# ==========================================================================
def render_urgency_message(level: str):
    """The coloured Streamlit box that explains what the urgency level means."""
    message = URGENCY_MESSAGES.get(level, "")
    if level == "LOW":
        st.success(message)
    elif level == "EMERGENCY":
        st.error(message)
    else:
        st.warning(message)


def urgency_chart(counts: dict):
    """Bar chart of urgency levels, each bar in its own urgency colour."""
    data = pd.DataFrame(
        {"level": URGENCY_LEVELS, "count": [counts.get(lv, 0) for lv in URGENCY_LEVELS]}
    )
    try:
        import altair as alt

        chart = (
            alt.Chart(data)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("level:N", sort=URGENCY_LEVELS, title="Urgency level"),
                y=alt.Y("count:Q", title="Assessments", axis=alt.Axis(tickMinStep=1)),
                color=alt.Color(
                    "level:N",
                    scale=alt.Scale(
                        domain=URGENCY_LEVELS, range=[URGENCY_COLORS[lv] for lv in URGENCY_LEVELS]
                    ),
                    legend=None,
                ),
            )
        )
        st.altair_chart(chart)
    except Exception:  # fall back to a plain chart if altair is unavailable
        st.bar_chart(data.set_index("level"))


# ==========================================================================
# Login / sign-up page (shown when nobody is logged in)
# ==========================================================================
def render_login_sidebar():
    with st.sidebar:
        st.markdown(f'<div class="mg-char" style="text-align:center">{theme.character_svg(90)}</div>',
                    unsafe_allow_html=True)
        st.title("MediGuide AI")
        st.caption("AI-powered symptom guidance assistant (educational prototype)")
        st.write("Log in to get safe, structured, preliminary guidance and to keep your history.")
        theme.sidebar_disclaimer()  # Disclaimer: sidebar


def handle_login(username: str, password: str):
    user, error = auth.login(username, password)
    if error:
        st.error(error)
        return
    st.session_state.pop("result", None)
    st.session_state["user"] = user
    st.session_state["welcome"] = True
    st.rerun()


def render_login_page():
    render_login_sidebar()
    theme.hero(
        "MediGuide AI",
        "Your safe, friendly symptom guidance assistant",
        [
            "Hi! I'm Dr. Medi",
            "Log in to see your saved guidance history.",
            "I'm an AI helper, not a real doctor.",
        ],
    )
    st.warning(DISCLAIMER_LONG)  # Disclaimer: main area

    left, right = st.columns([1, 1])
    with left:
        st.markdown(theme.info_card("", "Structured AI guidance",
                    "Urgency level, possible conditions, next steps and warning signs."),
                    unsafe_allow_html=True)
        st.markdown(theme.info_card("", "Private accounts",
                    "Passwords are stored hashed. Only you can open your own history."),
                    unsafe_allow_html=True)
        st.markdown(theme.info_card("", "Saved history and chat",
                    "Revisit past assessments, ask follow-up questions, download reports."),
                    unsafe_allow_html=True)
        st.markdown(theme.info_card("", "Safety first",
                    "Never a diagnosis. Emergency symptoms always get urgent advice."),
                    unsafe_allow_html=True)

    with right:
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                login_clicked = st.form_submit_button("Log in", type="primary")
            if login_clicked:
                handle_login(username, password)

        with tab_signup:
            with st.form("signup_form"):
                full_name = st.text_input("Full name")
                new_username = st.text_input(
                    "Choose a username", help="3-30 characters: letters, numbers, underscore"
                )
                email = st.text_input("Email")
                new_password = st.text_input(
                    "Password", type="password", help="At least 8 characters, with a letter and a number"
                )
                confirm = st.text_input("Confirm password", type="password")
                consent = st.checkbox(
                    "I understand MediGuide AI is educational (not medical advice) and that my "
                    "assessments are saved in my account history."
                )
                signup_clicked = st.form_submit_button("Create account", type="primary")
            if signup_clicked:
                if not consent:
                    st.warning("Please tick the box to continue.")
                else:
                    user, errors = auth.register(new_username, full_name, email, new_password, confirm)
                    if errors:
                        for message in errors:
                            st.error(message)
                    else:
                        st.success("Account created! Logging you in...")
                        handle_login(new_username, new_password)


# ==========================================================================
# Sidebar (after login)
# ==========================================================================
def render_sidebar(user: dict):
    """Draw the sidebar. Returns (page, model_name, temperature, cache_mode, default_language)."""
    with st.sidebar:
        st.markdown(f'<div class="mg-char" style="text-align:center">{theme.character_svg(90)}</div>',
                    unsafe_allow_html=True)
        st.title("MediGuide AI")
        st.caption("AI-powered symptom guidance assistant (educational prototype)")
        st.write(f"**{user['full_name']}**" + ("  ·  admin" if user["role"] == "admin" else ""))

        pages = [PAGE_NEW, PAGE_HISTORY, PAGE_ANALYTICS]
        if user["role"] == "admin":
            pages.append(PAGE_ADMIN)
        page = st.radio("Menu", pages, key="page", label_visibility="collapsed")

        theme.sidebar_disclaimer()  # Disclaimer: sidebar

        st.divider()
        st.subheader("Model configuration")
        default_index = MODEL_OPTIONS.index(DEFAULT_MODEL) if DEFAULT_MODEL in MODEL_OPTIONS else 0
        model_name = st.selectbox("OpenAI model", MODEL_OPTIONS, index=default_index)
        temperature = st.slider("Temperature (creativity)", 0.0, 1.0, DEFAULT_TEMPERATURE, 0.1)
        st.caption(
            "Chain type: LLMChain"
            if USING_LLMCHAIN
            else "Chain type: prompt | llm (LCEL fallback for this Python version)"
        )

        cache_mode = st.selectbox(
            "Caching",
            CACHE_MODES,
            index=1,
            help=(
                "In-memory: stored in RAM, lost on restart.\n\n"
                "SQLite: stored in a .db file, survives restart."
            ),
        )
        st.caption(configure_cache(cache_mode))
        if cache_mode == "In-memory" and st.button("Clear in-memory cache"):
            clear_memory_cache()
            st.toast("In-memory cache cleared.")

        st.divider()
        default_language = st.selectbox("Default answer language", LANGUAGE_OPTIONS)

        st.divider()
        if st.button("Log out"):
            auth.logout(user)
            for key in ("user", "result", "page"):
                st.session_state.pop(key, None)
            st.rerun()

    return page, model_name, temperature, cache_mode, default_language


# ==========================================================================
# Page 1: New assessment
# ==========================================================================
def render_form(default_language: str):
    """Draw the patient form. Returns (submitted, raw_values_dict)."""
    st.header("Tell us about your symptoms")
    with st.form("patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            age_text = st.text_input("Age", placeholder="e.g. 25")
        with col2:
            gender = st.selectbox("Gender", GENDER_OPTIONS)

        selected = st.multiselect("Symptoms (choose one or more)", SYMPTOM_OPTIONS)
        free_text = st.text_input(
            "Other symptoms (optional, separate with commas)",
            placeholder="e.g. ear pain, watery eyes",
        )

        col3, col4 = st.columns(2)
        with col3:
            duration = st.selectbox("How long have you had them?", DURATION_OPTIONS)
        with col4:
            language = st.selectbox(
                "Answer language",
                LANGUAGE_OPTIONS,
                index=LANGUAGE_OPTIONS.index(default_language),
            )

        severity = st.slider("Severity (1 = very mild, 10 = very severe)", 1, 10, 3)

        conditions = st.text_area("Existing medical conditions (optional)", placeholder="e.g. asthma, diabetes")
        medications = st.text_area("Current medications (optional)", placeholder="e.g. metformin")
        notes = st.text_area("Additional notes (optional)")

        submitted = st.form_submit_button("Get guidance", type="primary")

    values = {
        "age_text": age_text,
        "gender": gender,
        "selected": selected,
        "free_text": free_text,
        "duration": duration,
        "language": language,
        "severity": severity,
        "conditions": conditions,
        "medications": medications,
        "notes": notes,
    }
    return submitted, values


def process_submission(values: dict, user: dict, model_name: str, temperature: float, cache_mode: str):
    """
    Validate input, call the LLMChain, parse the JSON, save it to the user's
    history and keep the result in st.session_state so it survives re-runs.
    """
    # --- Validation: no API call if the input is incomplete (test scenario 5)
    symptoms = build_symptom_list(values["selected"], values["free_text"])
    if not symptoms:
        st.warning("Please select or type at least one symptom. No request was sent.")
        return
    age, age_error = validate_age(values["age_text"])
    if age_error:
        st.warning(age_error)
        return

    inputs = build_chain_inputs(
        age,
        values["gender"],
        symptoms,
        values["duration"],
        values["severity"],
        values["conditions"],
        values["medications"],
        values["notes"],
        values["language"],
    )

    # --- Build the model + chain and run the assessment
    try:
        llm_json = build_llm(model_name, temperature, json_mode=True)
        chain = build_assessment_chain(llm_json)
        start = time.perf_counter()
        with st.spinner("Dr. Medi is analysing your symptoms..."):
            raw_text = run_assessment(chain, inputs)
        elapsed = time.perf_counter() - start
    except ValueError as err:  # e.g. missing API key
        st.error(str(err))
        return
    except Exception as err:  # network errors, bad key, rate limits, ...
        st.error(f"Could not get a response from the model: {err}")
        return

    # --- Parse the JSON safely
    data, parse_error = safe_parse_json(raw_text)
    parsed, safety_note = None, None
    if data is not None:
        parsed = normalize_result(data)
        parsed["urgency_level"], safety_note = apply_safety_floor(parsed["urgency_level"], symptoms)

    # --- Save to the user's history (only when the result is usable)
    assessment_id, assessment = None, None
    if parsed is not None:
        try:
            assessment_id = database.save_assessment(user["id"], inputs, parsed, model_name)
            assessment = database.get_assessment(assessment_id, user["id"])
        except Exception as err:
            st.warning(f"The result could not be saved to your history: {err}")

    st.session_state["result"] = {
        "parsed": parsed,
        "parse_error": parse_error,
        "raw_text": raw_text,
        "inputs": inputs,
        "elapsed": elapsed,
        "cache_mode": cache_mode,
        "safety_note": safety_note,
        "narrative": None,  # filled in by streaming
        "model_name": model_name,
        "temperature": temperature,
        "assessment_id": assessment_id,
        "assessment": assessment,
    }


def render_results(a: dict, elapsed=None, cache_mode=None, safety_note=None):
    """
    Draw the structured results dashboard from an assessment dict
    (works for a fresh result and for one opened from the history).
    """
    st.divider()
    st.header("Your guidance")
    st.info(DISCLAIMER_LONG)  # Disclaimer: results

    parsed = a.get("parsed")
    if not parsed:
        st.error("This assessment has no readable result.")
        return

    level = parsed.get("urgency_level") or a.get("urgency") or "MEDIUM"
    color = URGENCY_COLORS.get(level, URGENCY_COLORS["MEDIUM"])
    st.markdown(theme.urgency_banner(level, color), unsafe_allow_html=True)
    render_urgency_message(level)
    if safety_note:
        st.warning(safety_note)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Urgency", level)
    m2.metric("Severity reported", f"{a.get('severity')}/10")
    m3.metric("Possible conditions", len(parsed.get("possible_conditions", [])))
    if elapsed is not None:
        m4.metric("Response time", f"{elapsed:.2f} s", help=f"Cache: {cache_mode}")
    else:
        m4.metric("Saved on", str(a.get("created_at", ""))[:10])

    tab_summary, tab_conditions, tab_steps, tab_questions, tab_warn = st.tabs(
        [
            "Summary",
            "Possible conditions",
            "Next steps",
            "Questions for your doctor",
            "Warning signs",
        ]
    )

    with tab_summary:
        st.subheader("Patient symptom summary")
        st.write(f"**Age:** {a.get('age')}  |  **Gender:** {a.get('gender')}  |  **Duration:** {a.get('duration')}")
        st.write(f"**Symptoms:** {a.get('symptoms')}")
        st.subheader("General information")
        st.write(parsed.get("summary") or "No summary was returned.")

    with tab_conditions:
        st.caption("For education only - this is NOT a diagnosis.")
        conditions = parsed.get("possible_conditions", [])
        if conditions:
            for item in conditions:
                with st.expander(item.get("name", "Condition")):
                    st.write(item.get("reason") or "No explanation given.")
        else:
            st.write("No conditions were listed.")

    with tab_steps:
        for step in parsed.get("recommended_next_steps") or ["See a healthcare professional."]:
            st.success(step)

    with tab_questions:
        for q in parsed.get("questions_for_doctor") or ["No questions were suggested."]:
            st.info(q)

    with tab_warn:
        st.caption("Seek urgent medical help if any of these happen.")
        for sign in parsed.get("warning_signs") or ["No warning signs were listed."]:
            st.error(sign)


def render_narrative(res: dict):
    """Stream the friendly narrative live (or show the saved one)."""
    st.subheader("Guidance in plain words")

    if res["narrative"] is not None:
        st.write(res["narrative"])
        return

    try:
        llm_text = build_llm(res["model_name"], res["temperature"], json_mode=False)
        # st.write_stream shows chunks as they arrive and returns the full text.
        text = st.write_stream(stream_narrative(llm_text, res["inputs"]))
        res["narrative"] = text
        if res.get("assessment_id") and res.get("assessment"):
            database.update_narrative(res["assessment_id"], text)
            res["assessment"]["narrative"] = text
    except Exception as err:
        res["narrative"] = ""
        st.warning(f"The plain-words guidance could not be generated: {err}")


def render_downloads(a: dict, user: dict):
    """Buttons to download the guidance as a text file and (if possible) a PDF."""
    st.subheader("Download your report")
    col_txt, col_pdf = st.columns(2)
    with col_txt:
        st.download_button(
            "Download report (.txt)",
            data=report.build_report_text(a, user).encode("utf-8"),
            file_name=f"mediguide_report_{a['id']}.txt",
            mime="text/plain",
            key=f"dl_txt_{a['id']}",
        )
    with col_pdf:
        if report.pdf_supported(a, user):
            st.download_button(
                "Download report (.pdf)",
                data=report.build_pdf(a, user),
                file_name=f"mediguide_report_{a['id']}.pdf",
                mime="application/pdf",
                key=f"dl_pdf_{a['id']}",
            )
        else:
            st.caption("PDF works for Latin-script languages (and needs `reportlab`). Use the .txt report.")


def render_chat(a: dict, model_name: str, temperature: float):
    """Follow-up chat about one assessment. Messages are saved in the database."""
    st.subheader("Ask a follow-up question")
    history = database.get_chat_messages(a["id"])
    for message in history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask something about your guidance...", key=f"chat_input_{a['id']}")
    if not question:
        return

    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        try:
            llm = build_llm(model_name, temperature)
            parsed = a.get("parsed") or {}
            answer = st.write_stream(
                stream_followup(
                    llm,
                    assessment_to_inputs(a),
                    parsed.get("urgency_level"),
                    parsed.get("summary"),
                    history,
                    question,
                )
            )
        except Exception as err:
            st.error(f"Could not get an answer: {err}")
            return
    database.add_chat_message(a["id"], "user", question)
    database.add_chat_message(a["id"], "assistant", answer)


def render_message_demo(res: dict, model_name: str, temperature: float):
    """Optional demo of raw System / Human / AI messages."""
    with st.expander("Demo: raw System / Human / AI messages"):
        st.caption(
            "Shows how SystemMessage, HumanMessage and AIMessage build a conversation. "
            "Uses the symptoms from your last submitted form."
        )
        if st.button("Run message demo"):
            try:
                llm = build_llm(model_name, temperature)
                with st.spinner("Running demo..."):
                    pairs = raw_message_demo(llm, res["inputs"])
                for role, text in pairs:
                    st.markdown(f"**{role}:**")
                    st.write(text)
            except Exception as err:
                st.error(f"Demo failed: {err}")


def page_new_assessment(user, model_name, temperature, cache_mode, default_language):
    theme.hero(
        theme.greeting(user["full_name"]),
        "Describe your symptoms and get safe, structured guidance.",
        [
            "Tell me what you're feeling",
            "I'll suggest an urgency level and next steps.",
            "Remember: I'm not a doctor. Please see one if worried.",
        ],
        size=125,
    )
    st.warning(DISCLAIMER_LONG)  # Disclaimer: main area

    submitted, values = render_form(default_language)
    if submitted:
        st.session_state.pop("result", None)  # forget the previous result
        process_submission(values, user, model_name, temperature, cache_mode)

    res = st.session_state.get("result")
    if not res:
        return

    if res["assessment"] is not None:
        render_results(res["assessment"], res["elapsed"], res["cache_mode"], res["safety_note"])
    else:
        st.divider()
        st.error(
            "Sorry, the structured result could not be read. "
            f"Details: {res['parse_error']} Please try again."
        )
        with st.expander("Show raw model output (for debugging)"):
            st.code(res["raw_text"] or "(empty)")

    render_narrative(res)

    if res.get("assessment"):
        render_downloads(res["assessment"], user)
        render_chat(res["assessment"], model_name, temperature)
    render_message_demo(res, model_name, temperature)


# ==========================================================================
# Page 2: My history
# ==========================================================================
def page_history(user, model_name, temperature):
    st.header("My history")
    items = database.list_assessments(user["id"])
    if not items:
        st.info("You have no saved assessments yet. Create one on the 'New assessment' page.")
        return

    table = pd.DataFrame(
        [
            {
                "ID": a["id"],
                "Date": str(a["created_at"]).replace("T", " "),
                "Symptoms": a["symptoms"],
                "Severity": a["severity"],
                "Urgency": a["urgency"],
            }
            for a in items
        ]
    )
    st.dataframe(table, hide_index=True)

    labels = {
        a["id"]: f"#{a['id']} · {str(a['created_at']).replace('T', ' ')} · {a['urgency'] or 'n/a'} · "
        f"{(a['symptoms'] or '')[:40]}"
        for a in items
    }
    chosen = st.selectbox("Open an assessment", list(labels), format_func=lambda i: labels[i])
    a = database.get_assessment(chosen, user["id"])
    if a is None:
        st.error("That assessment could not be found.")
        return

    render_results(a)
    if a.get("narrative"):
        st.subheader("Guidance in plain words")
        st.write(a["narrative"])
    render_downloads(a, user)

    with st.expander("Delete this assessment"):
        confirm = st.checkbox("Yes, delete it permanently (and its chat)", key=f"confirm_del_{a['id']}")
        if st.button("Delete", key=f"del_{a['id']}"):
            if confirm:
                database.delete_assessment(a["id"], user["id"])
                st.toast("Assessment deleted.")
                st.rerun()
            else:
                st.warning("Please tick the confirmation box first.")

    render_chat(a, model_name, temperature)


# ==========================================================================
# Page 3: Analytics (the logged-in user's own data)
# ==========================================================================
def page_analytics(user):
    st.header("My analytics")
    items = database.list_assessments(user["id"])
    if not items:
        st.info("Analytics will appear after your first assessment.")
        return

    counts = database.urgency_counts(user["id"])
    severities = [a["severity"] for a in items if a["severity"] is not None]
    average = sum(severities) / len(severities) if severities else 0
    most_common = max(counts, key=counts.get) if counts else "-"

    c1, c2, c3 = st.columns(3)
    c1.markdown(theme.stat_card("", len(items), "Assessments"), unsafe_allow_html=True)
    c2.markdown(theme.stat_card("", f"{average:.1f}", "Average severity"), unsafe_allow_html=True)
    c3.markdown(theme.stat_card("", most_common, "Most common urgency"), unsafe_allow_html=True)

    st.subheader("Urgency distribution")
    urgency_chart(counts)

    st.subheader("Most reported symptoms")
    symptom_counter = Counter()
    for a in items:
        for symptom in (a["symptoms"] or "").split(","):
            if symptom.strip():
                symptom_counter[symptom.strip().title()] += 1
    if symptom_counter:
        top = pd.DataFrame(symptom_counter.most_common(8), columns=["Symptom", "Times"])
        st.bar_chart(top.set_index("Symptom"))

    st.subheader("Severity over time")
    trend = pd.DataFrame(
        {"Severity": [a["severity"] for a in reversed(items)]},
        index=[str(a["created_at"]).replace("T", " ") for a in reversed(items)],
    )
    st.line_chart(trend)
    st.caption("Educational statistics only - not medical advice.")


# ==========================================================================
# Page 4: Admin (only for the admin account)
# ==========================================================================
def page_admin(user):
    st.header("Admin panel")
    if user["role"] != "admin":
        st.error("You do not have permission to view this page.")
        return

    st.caption(
        "Shows accounts and login records. For privacy, users' medical details are "
        "NOT shown here - only counts."
    )
    totals = database.totals()
    c1, c2, c3 = st.columns(3)
    c1.markdown(theme.stat_card("", totals["users"], "Registered users"), unsafe_allow_html=True)
    c2.markdown(theme.stat_card("", totals["logins"], "Total logins"), unsafe_allow_html=True)
    c3.markdown(theme.stat_card("", totals["assessments"], "Assessments made"), unsafe_allow_html=True)

    tab_users, tab_events, tab_stats = st.tabs(["Users", "Login records", "Urgency overview"])

    with tab_users:
        users = pd.DataFrame(database.list_users())
        if users.empty:
            st.info("No users yet.")
        else:
            users = users.rename(
                columns={
                    "username": "Username",
                    "full_name": "Full name",
                    "email": "Email",
                    "role": "Role",
                    "created_at": "Signed up",
                    "last_login": "Last login",
                    "login_count": "Logins",
                    "assessments": "Assessments",
                }
            ).drop(columns=["id"])
            st.dataframe(users, hide_index=True)
            st.download_button(
                "Download users (.csv)",
                data=users.to_csv(index=False).encode("utf-8"),
                file_name="mediguide_users.csv",
                mime="text/csv",
            )

    with tab_events:
        events = pd.DataFrame(database.recent_events(200))
        if events.empty:
            st.info("No login records yet.")
        else:
            events = events.rename(columns={"username": "Username", "event": "Event", "created_at": "Time"})
            st.dataframe(events, hide_index=True)
            st.caption("Events: signup, login, failed (wrong password), locked, logout.")

    with tab_stats:
        urgency_chart(database.urgency_counts(None))


# ==========================================================================
# Main
# ==========================================================================
def main():
    _prepare_database()
    theme.apply_theme()
    theme.disclaimer_ticker()  # moving disclaimer bar (every page)

    user = st.session_state.get("user")
    if not user:
        render_login_page()
        return

    page, model_name, temperature, cache_mode, default_language = render_sidebar(user)

    if st.session_state.pop("welcome", False):
        st.toast(f"Welcome, {user['full_name']}!")

    if page == PAGE_HISTORY:
        page_history(user, model_name, temperature)
    elif page == PAGE_ANALYTICS:
        page_analytics(user)
    elif page == PAGE_ADMIN:
        page_admin(user)
    else:
        page_new_assessment(user, model_name, temperature, cache_mode, default_language)

    st.divider()
    st.caption(
        "MediGuide AI is an educational project and not a medical device. "
        "Always consult a qualified healthcare professional."
    )


main()