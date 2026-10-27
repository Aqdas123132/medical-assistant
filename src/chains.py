"""
chains.py - Builds the ChatOpenAI model, the LLMChain, and streaming helpers.
"""

import warnings

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY
from src.prompts import (
    ASSESSMENT_CHAT_TEMPLATE,
    DEMO_FOLLOW_UP,
    FOLLOWUP_SYSTEM_TEXT,
    NARRATIVE_CHAT_TEMPLATE,
    PATIENT_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
)

# LLMChain still works but newer LangChain versions mark it as "deprecated".
# The assignment asks for LLMChain, so we hide the warning to keep logs clean.
warnings.filterwarnings("ignore", message=".*LLMChain.*")

# On very new Python versions (3.14+), LangChain 0.3's LLMChain cannot even be
# imported (a typing problem inside the library, not in this project).
# So we TRY to import it, and if that fails we use the modern equivalent:
# "prompt | llm | parser" (LCEL), which does the same job.
try:
    from langchain.chains import LLMChain
except Exception:  # pragma: no cover - depends on installed version
    try:
        from langchain.chains.llm import LLMChain
    except Exception:
        LLMChain = None

USING_LLMCHAIN = LLMChain is not None


# --------------------------------------------------------------------------
# 1) ChatOpenAI
# --------------------------------------------------------------------------
def build_llm(model_name: str, temperature: float = 0.2, json_mode: bool = False):
    """
    Create the OpenAI chat model.

    json_mode=True asks OpenAI to guarantee syntactically valid JSON.
    We use it for the assessment chain, but NOT for the streamed narrative.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your-key"):
        raise ValueError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    extra = {}
    if json_mode:
        extra["model_kwargs"] = {"response_format": {"type": "json_object"}}

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=OPENAI_API_KEY,
        timeout=60,
        max_retries=2,
        **extra,
    )


# --------------------------------------------------------------------------
# 2) LLMChain - the reusable assessment pipeline
# --------------------------------------------------------------------------
def build_assessment_chain(llm):
    """prompt (ChatPromptTemplate) + model = one reusable chain."""
    if USING_LLMCHAIN:
        return LLMChain(llm=llm, prompt=ASSESSMENT_CHAT_TEMPLATE)
    # Fallback (same idea, modern syntax): prompt -> model -> plain text
    return ASSESSMENT_CHAT_TEMPLATE | llm | StrOutputParser()


def run_assessment(chain, inputs: dict) -> str:
    """Run the chain and return the raw text produced by the model."""
    result = chain.invoke(inputs)
    # LLMChain returns {"text": "..."}; the fallback chain returns a string.
    return result["text"] if isinstance(result, dict) else result


# --------------------------------------------------------------------------
# 3) Streaming - yields the narrative piece by piece
# --------------------------------------------------------------------------
def stream_narrative(llm, inputs: dict):
    """
    Generator: yields small chunks of text as the model writes them.
    st.write_stream() prints each chunk so the user sees a typing effect.
    """
    messages = NARRATIVE_CHAT_TEMPLATE.format_messages(**inputs)
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content


# --------------------------------------------------------------------------
# 3b) Follow-up chat - streams an answer using the saved conversation
# --------------------------------------------------------------------------
def stream_followup(llm, inputs: dict, urgency: str, summary: str, history: list, question: str):
    """
    Generator for the follow-up chat.

    history: earlier messages as dicts {"role": "user"|"assistant", "content": ...}
    The messages sent to the model look like:
        SystemMessage (rules + patient data) -> Human -> AI -> Human -> AI ... -> Human(question)
    """
    system_text = FOLLOWUP_SYSTEM_TEXT.format(
        language=inputs.get("language", "English"),
        patient_data=PATIENT_PROMPT_TEMPLATE.format(**inputs),
        urgency=urgency or "unknown",
        summary=summary or "not available",
    )
    messages = [SystemMessage(content=system_text)]
    for item in history[-10:]:  # keep only the last 10 messages to save tokens
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    messages.append(HumanMessage(content=question))

    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content


# --------------------------------------------------------------------------
# 4) Raw System / Human / AI message demo
# --------------------------------------------------------------------------
def raw_message_demo(llm, inputs: dict) -> list:
    """
    Shows how the three message types form a conversation.

      SystemMessage : sets the role and safety rules
      HumanMessage  : the patient's data / questions
      AIMessage     : the model's earlier reply, kept as conversation memory

    Returns a list of (role, text) pairs for display.
    """
    patient_text = PATIENT_PROMPT_TEMPLATE.format(**inputs)

    # Turn 1: system rules + patient data.
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content="Give a 2-sentence general overview (no diagnosis).\n\n"
            + patient_text
        ),
    ]
    first_reply = llm.invoke(messages)  # returns an AIMessage

    # Turn 2: add the AI reply to the history, then ask a follow-up.
    messages.append(AIMessage(content=first_reply.content))
    messages.append(HumanMessage(content=DEMO_FOLLOW_UP))
    second_reply = llm.invoke(messages)
    messages.append(AIMessage(content=second_reply.content))

    labels = {SystemMessage: "System", HumanMessage: "Human", AIMessage: "AI"}
    return [(labels[type(m)], m.content) for m in messages]