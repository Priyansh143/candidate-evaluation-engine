from typing import List
import re
from autogen_core.models import SystemMessage
import ast
import asyncio

async def extract_jd_priorities_llm(jd_text: str, jd_role: str, llm_call, logger = None) -> List[str]:
    """
    Uses an LLM to extract ordered JD priorities.
    `llm_call` should be a function that takes (system_prompt, user_prompt)
    and returns raw text.
    """

    user_prompt = f"""
        Extract the main interview topics for the given job role and job description.
        job role: {jd_role}
        Job Description:
        {jd_text}

        Return a Python list of dictionaries.

        Each dictionary must contain:
        - topic: the main interview topic
        - keywords: 4–5 related related terms/subtopics that might appear in a resume

        Rules:
        - 3 to 6 topics
        - topic must be 2–4 words
        - keywords must be concise resume terms
        - NO explanations
        - NO trailing text, only the list
        Example:
        [
        {{
        "topic": "model deployment",
        "keywords": ["deployed","model serving","fastapi","docker","production pipeline"]
        }},
        {{
        "topic": "feature engineering",
        "keywords": ["feature engineering","feature selection","feature extraction","data preprocessing","feature transformation"]
        }}
        ]
    """
    response = await llm_call.create(
        messages=[
            SystemMessage(content=user_prompt)
        ]
    )
    print("LLM response for JD priority extraction:\n", response.content)
    logger.info("\n INSIDE JD PRIORITY EXTRACTION FUNCTION \n")
    logger.info(f"LLM response for JD priority extraction: {response.content}")
    logger.info("LLM response received for JD priority extraction.")
    
    raw_output = response.content.strip()

    # Extract list block from LLM output
    match = re.search(r"\[.*\]", raw_output, re.S)
    if not match:
        raise ValueError("Could not parse topics list")

    list_str = match.group(0)

    # safer than eval
    topic_objects = ast.literal_eval(list_str)
    logger.info(f"Parsed JD priorities: {topic_objects}\n")

    # limit topics
    if len(topic_objects) > 6:
        topic_objects  = topic_objects[:6]
    # simple topic list for existing pipeline
    topics = [item["topic"] for item in topic_objects]
    logger.info(f"Extracted JD priorities: {topics}\n")
    return topics, topic_objects

def extract_jd_priorities_stub(
    job_role: str,
    job_description: str
) -> List[str]:
    return [
        "machine learning fundamentals",
        "model deployment",
        "data preprocessing",
        "model evaluation",
        "sql analytics"
    ]
    
