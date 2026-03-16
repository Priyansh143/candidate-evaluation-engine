from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class QuestionType(str, Enum):
    THEORY = "THEORY"
    APPLIED = "APPLIED"
    CLARIFICATION = "CLARIFICATION"
    
@dataclass
class InterviewState:
    session_id: int
    job_role: str

    jd_priorities: List[str]
    current_priority_index: int = 0

    questions_asked_in_priority: int = 0
    max_questions_per_priority: int = 3

    last_question_type: Optional[QuestionType] = None
    last_satisfaction: Optional[float] = None
    last_confidence: Optional[str] = None

    resume_evidence: List[str] = field(default_factory=list)

    history: List[Dict] = field(default_factory=list)
    
def decide_next_action(state: InterviewState) -> QuestionType:
    # First question of a priority
    if state.questions_asked_in_priority == 0:
        return (
            QuestionType.APPLIED
            if state.resume_evidence
            else QuestionType.THEORY
        )

    # If max questions reached, caller must move priority
    if state.questions_asked_in_priority >= state.max_questions_per_priority:
        raise RuntimeError("Priority exhausted")

    # Decide based on evaluator feedback
    if state.last_satisfaction is None:
        return QuestionType.THEORY

    if state.last_satisfaction >= 0.75:
        return QuestionType.APPLIED

    if 0.45 <= state.last_satisfaction < 0.75:
        return QuestionType.CLARIFICATION

    return QuestionType.THEORY

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
    evaluator_output: Dict
):
    record = {
        "session_id": state.session_id,
        "priority_index": state.current_priority_index,
        "jd_priority": state.jd_priorities[state.current_priority_index],
        "question_number": state.questions_asked_in_priority + 1,
        "question_type": question_type.value,
        "satisfaction": evaluator_output["satisfaction"],
        "confidence": evaluator_output["confidence"],
        "strengths": evaluator_output.get("strengths", []),
        "weaknesses": evaluator_output.get("weaknesses", []),
        "timestamp": datetime.utcnow().isoformat()
    }

    state.history.append(record)

    # Update state
    state.last_question_type = question_type
    state.last_satisfaction = evaluator_output["satisfaction"]
    state.last_confidence = evaluator_output["confidence"]
    state.questions_asked_in_priority += 1
    
