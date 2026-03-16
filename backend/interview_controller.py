from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import random 
from backend.database import save_turn


class QuestionType(str, Enum):
    THEORY = "THEORY"
    APPLIED = "APPLIED"
    CLARIFICATION = "CLARIFICATION"
    DEPTH = "DEPTH"
    
@dataclass
class InterviewState:
    session_id: int
    job_role: str
    jd_priorities: List[str]
    config: dict 

    current_priority_index: int = 0
    questions_asked_in_priority: int = 0
    last_question_type: Optional[QuestionType] = None
    last_satisfaction: Optional[float] = None
    last_confidence: Optional[str] = None
    avg_satisfaction_curr_priority: float = 0.0
    covered_topics: Dict[str, set] = field(default_factory=dict)
    resume_evidence: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    

def sample_action(policy):

    actions = list(policy.keys())
    weights = list(policy.values())

    return random.choices(actions, weights=weights, k=1)[0]

def get_score_band(score, thresholds):

    if score is None:
        return "start"

    if score < thresholds["weak"]:
        return "weak"

    if score < thresholds["medium"]:
        return "medium"

    return "strong"

def filter_used_actions(policy, used_actions):

    filtered = {
        action: prob
        for action, prob in policy.items()
        if action.upper() not in used_actions
    }

    return filtered if filtered else policy

def decide_next_action(state: InterviewState, logger) -> QuestionType:
    
    logger.info(f"\n[decide_next_action] DECIDING NEXT ACTION\n")

    cfg = state.config["interview"]

    thresholds = cfg["thresholds"]
    policies = cfg["policy"]

    current_priority = state.jd_priorities[state.current_priority_index]

    used_actions = {
        h["question_type"]
        for h in state.history
        if h["jd_priority"] == current_priority
    }
    logger.info(f"Current JD priority: {current_priority}")
    logger.info(f"Used actions in this priority: {used_actions}")

    band = get_score_band(state.last_satisfaction, thresholds)
    logger.info(f"Last satisfaction score: {state.last_satisfaction}")
    logger.info(f"Score band: {band}")

    policy = policies[band]
    logger.info(f"Base policy: {policy}")

    policy = filter_used_actions(policy, used_actions)
    logger.info(f"Filtered policy: {policy}")

    action = sample_action(policy)
    logger.info(f"Sampled action: {action}")

    return QuestionType[action.upper()] 


def move_to_next_priority(state: InterviewState):
    state.current_priority_index += 1
    state.questions_asked_in_priority = 0
    state.last_question_type = None
    state.last_satisfaction = None
    state.last_confidence = None
    state.resume_evidence = []
    
def record_turn(
    state: InterviewState,
    question_type: QuestionType,
    evaluator_output: Dict,
    question,
    answer
):
    record = {
        "session_id": state.session_id,
        "job_role": state.job_role,
        "priority_index": state.current_priority_index,
        "jd_priority": state.jd_priorities[state.current_priority_index],
        "question_number": state.questions_asked_in_priority + 1,
        "question_type": question_type.value,
        "satisfaction": evaluator_output["satisfaction"],
        "confidence": evaluator_output["confidence"],
        "strengths": evaluator_output.get("strengths", []),
        "weaknesses": evaluator_output.get("weaknesses", []),
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer": answer
    }
    state.history.append(record)
    save_turn(record)

    # Update state
    state.last_question_type = question_type
    state.last_satisfaction = evaluator_output["satisfaction"]
    state.last_confidence = evaluator_output["confidence"]
    state.questions_asked_in_priority += 1
    state.avg_satisfaction_curr_priority = (
        (state.avg_satisfaction_curr_priority * (state.questions_asked_in_priority - 1))
        + evaluator_output["satisfaction"]
    ) / state.questions_asked_in_priority
    
