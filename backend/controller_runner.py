from backend.interview_controller import (
    QuestionType,
    InterviewState,
    decide_next_action,
    move_to_next_priority,
    record_turn,
)
from backend.agents import (
    ask_interviewer,
    evaluate_answer,
)
from backend.logger import setup_run_logger

async def run_interview(
    websocket,
    llm_client,
    state: InterviewState,
    faiss_results: list[list[str]],
    logger = None
):
    logger.info("Interview started")
    logger.info(f"Job role: {state.job_role}")
    logger.info(f"JD priorities: {state.jd_priorities}")
    interview_difficulty = state.config["interview"].get("difficulty", "medium")
    logger.info(f"Interview difficulty: {interview_difficulty}")

    while state.current_priority_index < len(state.jd_priorities):

        # ---- Enter new JD priority ----
        if state.questions_asked_in_priority == 0:
            current_priority = state.jd_priorities[state.current_priority_index]
            state.resume_evidence = faiss_results[state.current_priority_index]

            logger.info(f"Entering priority: {current_priority}")
            logger.info(f"all evidence: {state.resume_evidence}")
            logger.info(f"FAISS evidence : {state.resume_evidence[0]}")

            await websocket.send_text(
                f"SYSTEM_INFO:Now evaluating {current_priority}"
            )

        # ---- Decide next action ----
        action = decide_next_action(state= state, logger= logger)
        logger.info(
            f"[run_interview] Decided action: {action.value} "
            f"(question {state.questions_asked_in_priority + 1}/{state.config['interview'].get('questions_per_topic')} for this priority)"
        )

        # ---- Ask interviewer (LLM call) ----
        question = await ask_interviewer(
            llm_client=llm_client,
            job_role=state.job_role,
            jd_priority=current_priority,
            action=action.value,
            resume_evidence=state.resume_evidence[0],
            history=state.history if action == QuestionType.CLARIFICATION or action == QuestionType.DEPTH else None,
            covered_topics= state.covered_topics.get(current_priority, set()),
            interview_difficulty=interview_difficulty,
            logger = logger
        )

        logger.info(f"[Interviewer] {question}")
        await websocket.send_text(f"Interviewer:{question}")

        # ---- Candidate answers ----
        await websocket.send_text("SYSTEM_TURN:USER")
        answer = await websocket.receive_text()
        logger.info(f"[Candidate] {answer}")

        # ---- Evaluate answer (LLM call) ----
        evaluator_output = await evaluate_answer(
            llm_client=llm_client,
            job_role=state.job_role,
            jd_priority=current_priority,
            question=question,
            answer=answer,
            logger = logger
        )
        
        priority = state.jd_priorities[state.current_priority_index]

        if priority not in state.covered_topics:
            state.covered_topics[priority] = set()

        state.covered_topics[priority].update(evaluator_output["strengths"])

        logger.info(
            f"[Evaluator] satisfaction={evaluator_output['satisfaction']} "
            f"confidence={evaluator_output['confidence']}"
        )

        # ---- Record state ----
        record_turn(state, action, evaluator_output, question = question, answer = answer)

        # ---- Priority transition ----
        should_move_priority = (
            state.questions_asked_in_priority >= state.config["interview"].get("questions_per_topic", 3)
            or (
                state.questions_asked_in_priority >= state.config["interview"].get("questions_per_topic", 3) / 2
                and state.avg_satisfaction_curr_priority >= 0.8
            )
        )
        if  should_move_priority:
            logger.info(
                f"Priority '{current_priority}' exhausted "
                f"after {state.questions_asked_in_priority} questions"
            )
            move_to_next_priority(state)

    logger.info("Interview finished")
    await websocket.send_text("SYSTEM_END:")
    



