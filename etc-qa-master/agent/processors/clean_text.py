import re

from agent.state import AgentState
from utils.config_center import get_business_config


def clean_text(state: AgentState) -> dict:
    question = state.question or state.raw_question
    answer = state.answer or state.raw_answer

    question = _defensive_clean(question)

    if answer:
        answer = _defensive_clean(answer)

    return {
        "question": question,
        "answer": answer,
        "current_step": "clean_text",
    }


def _defensive_clean(text: str) -> str:
    clean_rules = get_business_config("clean_rules", [])
    for rule in clean_rules:
        text = re.sub(rule, "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([。！？])\1+", r"\1", text)
    text = re.sub(r"[，]{2,}", "，", text)
    text = re.sub(r"(\d)[，、](\d)", r"\1.\2", text)
    text = text.strip(" ，。！？、")
    return text
