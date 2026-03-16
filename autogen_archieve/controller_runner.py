from interview_controller import (
    QuestionType,
    InterviewState,
    decide_next_action,
    move_to_next_priority,
    record_turn,
)
from logger import setup_run_logger

async def run_interview(
    websocket,
    team,
    system_agent,
    interviewer,
    evaluator,
    state,
    faiss_search
):
    logger = setup_run_logger(run_id=str(state.session_id))

    logger.info("Interview started")
    logger.info(f"Job role: {state.job_role}")
    logger.info(f"JD priorities: {state.jd_priorities}")

    while state.current_priority_index < len(state.jd_priorities):

        # ---- Enter new priority ----
        if state.questions_asked_in_priority == 0:
            current_priority = state.jd_priorities[state.current_priority_index]
            state.resume_evidence = faiss_search(current_priority)

            logger.info(f"Entering priority: {current_priority}")
            logger.info(f"FAISS evidence count: {len(state.resume_evidence)}")

            await websocket.send_text(
                f"SYSTEM_INFO:Now evaluating {current_priority}"
            )

        # ---- Decide next action ----
        action = decide_next_action(state)
        logger.info(
            f"Decided action: {action.value} "
            f"(question {state.questions_asked_in_priority + 1}/{state.max_questions_per_priority})"
        )

        # ---- Inject instruction to interviewer ----
        instruction = build_interviewer_instruction(state, action)
        await system_agent.send(message=instruction, recipient=interviewer)

        # ---- Interviewer turn ----
        interviewer_msg = await team.step()
        last_question = interviewer_msg.content

        logger.info(f"[Interviewer | {action.value}] {last_question}")

        # Send interviewer question to UI
        await websocket.send_text(f"Interviewer:{last_question}")

        # ---- Candidate turn ----
        candidate_msg = await team.step()
        candidate_answer = candidate_msg.content
        logger.info(f"[Candidate] {candidate_answer}")

        # ---- Inject evaluator instruction ----
        eval_instruction = build_evaluator_instruction(
            state,
            last_question=last_question,
            candidate_answer=candidate_answer
        )

        await system_agent.send(
            message=eval_instruction,
            recipient=evaluator
        )

        # ---- Evaluator turn ----
        evaluator_msg = await team.step()
        raw_eval_text = evaluator_msg.content

        logger.info(f"[Evaluator RAW] {raw_eval_text}")

        evaluator_output = parse_evaluator_output(raw_eval_text)

        logger.info(
            f"[Evaluator PARSED] "
            f"satisfaction={evaluator_output['satisfaction']} "
            f"confidence={evaluator_output['confidence']} "
            f"strengths={evaluator_output['strengths']} "
            f"weaknesses={evaluator_output['weaknesses']}"
        )

        # ---- Record state ----
        record_turn(state, action, evaluator_output)

        # ---- Priority transition ----
        if state.questions_asked_in_priority >= state.max_questions_per_priority:
            logger.info(
                f"Priority '{current_priority}' exhausted "
                f"after {state.questions_asked_in_priority} questions"
            )
            move_to_next_priority(state)

    logger.info("Interview finished")
    logger.info(f"Final state history: {state.history}")

    await websocket.send_text("SYSTEM_END:")
    
def build_interviewer_instruction(state, action):
    current_priority = state.jd_priorities[state.current_priority_index]
    question_number = state.questions_asked_in_priority + 1
    max_questions = state.max_questions_per_priority

    evidence_text = (
        "\n".join(f"- {e}" for e in state.resume_evidence)
        if state.resume_evidence
        else "No relevant resume evidence found."
    )

    action_instruction = {
        QuestionType.THEORY: (
            "Ask a conceptual question to test understanding of fundamentals for the current topic."
        ),
        QuestionType.APPLIED: (
            "Ask about real-world experience or practical implementation related to the current topic."
        ),
        QuestionType.CLARIFICATION: (
            "Ask a follow-up question to clarify or expand on the candidate’s previous answer."
        ),
    }[action]

    instruction = f"""
        You are conducting a job interview.

        Current topic: {current_priority}
        Question {question_number} of {max_questions}

        Task:
        {action_instruction}

        Resume evidence:
        {evidence_text}

        Rules:
        - Ask ONE clear question only
        - Do NOT explain or give hints
        - Do NOT evaluate the answer
        - Keep the question under 50 words
        """

    return instruction.strip()

def build_evaluator_instruction(
    state: InterviewState,
    last_question: str,
    candidate_answer: str
) -> str:
    current_priority = state.jd_priorities[state.current_priority_index]

    return f"""
        You are evaluating a candidate interview answer.

        Context:
        - Job role: {state.job_role}
        - Current topic (JD priority): {current_priority}

        Question asked:
        {last_question}

        Candidate answer:
        {candidate_answer}

        Task:
        Evaluate the answer ONLY for relevance and quality with respect to the topic.

        Return ONLY valid JSON with:
        - satisfaction: float between 0 and 1
        - confidence: one of ["low", "medium", "high"]
        - strengths: list of short strings
        - weaknesses: list of short strings

        Rules:
        - Do NOT explain
        - Do NOT summarize the interview
        - Do NOT include extra text
        """.strip()


def parse_evaluator_output(raw_text: str) -> dict:
    """
    Parse evaluator agent output into a safe structured dict.
    """

    # ---- Try direct JSON ----
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # ---- Fallback: extract JSON block ----
        match = re.search(r"\{.*\}", raw_text, re.S)
        if not match:
            return default_evaluator_output()

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return default_evaluator_output()

    return normalize_evaluator_output(data)

def normalize_evaluator_output(data: dict) -> dict:
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

    # Strengths / Weaknesses
    strengths = data.get("strengths", [])
    weaknesses = data.get("weaknesses", [])

    if not isinstance(strengths, list):
        strengths = ["No clear strengths identified"]
    if not isinstance(weaknesses, list):
        weaknesses = ["No major weaknesses identified"]

    strengths = [str(s) for s in strengths][:5]
    weaknesses = [str(w) for w in weaknesses][:5]

    return {
        "satisfaction": satisfaction,
        "confidence": confidence,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }
    
