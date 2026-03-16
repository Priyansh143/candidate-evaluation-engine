# agents.py

from typing import List, Optional, Dict
import json
import re
from autogen_core.models import SystemMessage

# -------------------------------
# Interviewer
# -------------------------------

async def ask_interviewer(
    llm_client,
    job_role: str,
    jd_priority: str,
    action: str,
    resume_evidence: List[str],
    history: Optional[List[Dict]] = None,
    covered_topics: Optional[set] = None,
    interview_difficulty: str = "medium",
    logger=None,
) -> str:
    """
    Generate ONE interview question based on current state.
    """

    if logger:
        logger.info(
            f"[ask_interviewer] role={job_role} | "
            f"priority={jd_priority} | action={action} | "
            f"history_used={bool(history)} | "
            f"evidence_count={len(resume_evidence)}"
            f"covered_topics={covered_topics}"
            f"action={action}"
        )

    # ---- Optional short history (last turn only) ----
    history_block = ""
    if history:
        recent = history[-1:]
        history_block = "\n".join(
            f"Q: {h.get('question','')}\nA: {h.get('answer','')}"
            for h in recent
        )
    logger.info(f"history- {history_block}")

    if action in {"CLARIFICATION", "DEPTH", "THEORY"}:
        resume_evidence = ["None"]
        logger.info("No evidence will be used for CLARIFICATION or DEPTH action")

    # ---- Action mapping ----
    action_instruction = {
        "THEORY": "Ask a conceptual question to test the candidate's understanding of fundamentals.",
        "APPLIED": f"Probe candidate's applied experience by asking question using resume evidence for {jd_priority}, or implementation details if no good evidence is available.",
        "CLARIFICATION": "Ask a focused follow-up to clarify an ambiguous or incomplete part of the candidate's last answer.",
        "DEPTH": "Ask a deeper follow-up question that probes the candidate's reasoning — test their understanding of why something works, when it doesn't, or how it would change under different conditions."
    }.get(action, "Ask a relevant interview question.")

    
    logger.info("action mapping- " + action_instruction)
    prompt = f"""
        You are a professional interviewer for the role of {job_role}.
        Current topic being assessed:
        {jd_priority}
        Skills already demonstrated by candidate:
        {covered_topics or "None yet"}
        Relevant resume evidence from candidate:
        {resume_evidence or "Ignore"}
        Last interaction before this:
        {history_block or "None"}
        Task:
        {action_instruction}
        difficulty level: {interview_difficulty}
        Rules:
        - Ask ONE clear question
        - Do NOT ask about skills already demonstrated by the candidate
        - Do NOT explain or give hints
        - Do NOT evaluate the answer
        - Do NOT halucinate candidate's experience, only use the provided resume evidence if it makes sense to you
        - Keep the question under 50 words
        """.strip()

    logger.info("Passed prompt generation")

    if logger:
        logger.debug(
            f"[ask_interviewer] Prompt prepared "
            f"(length={len(prompt)})"
        )

    response = await llm_client.create(
        messages=[
        SystemMessage(content=prompt)
    ]
    )

    question = response.content.strip()

    if logger:
        logger.info(
            f"[ask_interviewer] Question generated "
            f"(length={len(question)})"
        )

    return question


# -------------------------------
# Evaluator
# -------------------------------

async def evaluate_answer(
    llm_client,
    job_role: str,
    jd_priority: str,
    question: str,
    answer: str,
    logger=None,
) -> Dict:
    """
    Evaluate candidate answer and return structured feedback.
    """

    if logger:
        logger.info(
            f"[evaluate_answer] role={job_role} | "
            f"priority={jd_priority} | "
            f"question_len={len(question)} | "
            f"answer_len={len(answer)}"
        )
    example = '{"strengths":["PostgreSQL proficiency","deployment experience"],"weaknesses":["monitoring knowledge", "cloud architecture"],"satisfaction":0.8,"eval_confidence":"high"}'
    prompt = f"""
        You are an interview evaluator for the role of {job_role}.
        Topic being assessed:
        {jd_priority}
        Interview Question:
        {question}
        Candidate Answer:
        {answer}
        Return ONLY valid JSON with the following keys:
        - satisfaction: how satisfactory the answer is for the Interview question asked, float between 0 and 1
        - strengths: list of skill or concept labels that were well demonstrated in the answer, if any, else []
        - weaknesses: list of skill or concept labels that were missing or weak, if any, else []
        - confidence: one of ["low", "medium", "high"] representing how confident you are in your evaluation 

        Example:
        {example}
        """.strip()

    response = await llm_client.create(
        messages=[
        SystemMessage(content=prompt)
    ]
    )

    raw = response.content
    logger.info(
            f"[evaluate_answer] Raw evaluator output "
            f"(length={len(raw)})"
        )

    return parse_evaluator_output(raw, logger)


# -------------------------------
# Evaluator Parsing Utilities
# -------------------------------

def parse_evaluator_output(raw_text: str, logger=None) -> Dict:
    """
    Safely parse evaluator output into structured dict.
    """

    try:
        data = json.loads(raw_text)
        if logger:
            logger.info("[parse_evaluator_output] Parsed JSON directly")
    except json.JSONDecodeError:
        if logger:
            logger.info(
                "[parse_evaluator_output] Direct JSON parse failed, "
                "attempting regex extraction"
            )

        match = re.search(r"\{.*\}", raw_text, re.S)
        if not match:
            if logger:
                logger.info(
                    "[parse_evaluator_output] No JSON block found, "
                    "using default output"
                )
            return default_evaluator_output()

        try:
            data = json.loads(match.group())
            if logger:
                logger.info("[parse_evaluator_output] Parsed JSON via regex")
        except json.JSONDecodeError:
            if logger:
                logger.info(
                    "[parse_evaluator_output] Regex JSON parse failed, "
                    "using default output"
                )
            return default_evaluator_output()

    return normalize_evaluator_output(data, logger)


def normalize_evaluator_output(data: Dict, logger=None) -> Dict:
    # Satisfaction
    try:
        satisfaction = float(data.get("satisfaction", 0.5))
    except (TypeError, ValueError):
        satisfaction = 0.5

    satisfaction = max(0.0, min(1.0, satisfaction))

    # Confidence
    confidence = str(data.get("confidence", "medium")).lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    strengths = data.get("strengths", [])
    weaknesses = data.get("weaknesses", [])

    if not isinstance(strengths, list):
        strengths = []
    if not isinstance(weaknesses, list):
        weaknesses = []

    strengths = [str(s) for s in strengths][:5]
    weaknesses = [str(w) for w in weaknesses][:5]

    if logger:
        logger.info(
            f"[normalize_evaluator_output] satisfaction={satisfaction} | "
            f"confidence={confidence} | "
            f"strengths={strengths} | "
            f"weaknesses={weaknesses}"
        )

    return {
        "satisfaction": satisfaction,
        "confidence": confidence,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def default_evaluator_output() -> Dict:
    return {
        "satisfaction": 0.5,
        "confidence": "medium",
        "strengths": [],
        "weaknesses": [],
    }