import sqlite3
import json
from collections import Counter, defaultdict
from statistics import mean
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio
from autogen_core.models import SystemMessage
from .database import save_report
from datetime import datetime
load_dotenv()

embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

embedding_model = SentenceTransformer(embedding_model_name, device="cpu")

CONFIDENCE_WEIGHT = {
    "low": 0.5,
    "medium": 1.0,
    "high": 1.5
}

def cluster_phrases(phrases, distance_threshold=0.55):
    """
    Groups semantically similar phrases together.
    Returns representative phrase for each cluster.
    """

    if len(phrases) <= 1:
        return [{"phrase": p, "count": 1} for p in phrases]

    embeddings = embedding_model.encode(phrases, normalize_embeddings=True)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold
    )

    labels = clustering.fit_predict(embeddings)

    clusters = {}

    for label, phrase in zip(labels, phrases):
        clusters.setdefault(label, []).append(phrase)

    # pick most common phrase per cluster
    cluster_summary = []

    for phrases in clusters.values():
        representative = max(set(phrases), key=phrases.count)
        cluster_summary.append({
            "phrase": representative,
            "count": len(phrases)
        })

    # sort clusters by importance
    cluster_summary.sort(key=lambda x: x["count"], reverse=True)

    return cluster_summary

def generate_report(session_id):

    conn = sqlite3.connect("data/interviews.db")
    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT satisfaction, confidence, strengths, weaknesses, jd_priority
        FROM interview_turns
        WHERE session_id=?
        """,
        (session_id,)
    ).fetchall()

    scores = []
    topic_strengths = defaultdict(list)
    topic_weaknesses = defaultdict(list)
    topic_scores = defaultdict(list)

    for satisfaction, confidence, st, wk, topic in rows:

        weight = CONFIDENCE_WEIGHT.get(confidence, 1)

        weighted_score = satisfaction * weight
        scores.append(weighted_score)

        strengths = json.loads(st)
        weaknesses = json.loads(wk)

        topic_strengths[topic].extend(strengths)
        topic_weaknesses[topic].extend(weaknesses)
        topic_scores[topic].append(weighted_score)

    overall_score = mean(scores)/1.5  # normalize to [0,1]
    # print(f"strengths before clustering: {strength_list}\n\n")
    # print(f"weaknesses before clustering: {weakness_list}\n\n")
    final_strengths = []
    final_weaknesses = []

    for topic in topic_strengths:

        clustered_s = cluster_phrases(topic_strengths[topic])
        clustered_w = cluster_phrases(topic_weaknesses[topic])

        final_strengths.extend([c["phrase"] for c in clustered_s[:2]])
        final_weaknesses.extend([c["phrase"] for c in clustered_w[:2]])

    top_strengths = final_strengths[:6]
    top_weaknesses = final_weaknesses[:6]    
        # --- Topic Scores ---
    topic_avg = {
        topic: round(mean(vals) / 1.5, 2)
        for topic, vals in topic_scores.items()
    }

    report = {
        "overall_score": overall_score,
        "topic_scores": topic_avg,
        "strengths": top_strengths,
        "weaknesses": top_weaknesses
    }

    return report

async def generate_human_report(llm_client, session_id, job_role):

    report_data = generate_report(session_id)

    prompt = f"""
        Write a concise interview evaluation report for a {job_role} candidate.

        Use the data below of a conducted interview.

        {json.dumps(report_data)}

        Format the report with these sections:
        Interview Summary
        Key Strengths
        Areas for Improvement
        Final Evaluation

        Base the report strictly on the strengths, weaknesses, and topic scores. 
    """
    print("Prompt for Human Report Generation:\n", prompt)
    response = await llm_client.create(
        messages=[
        SystemMessage(content=prompt)
    ]
    )
    report = response.content.replace('*', '')
    save_report({
    "session_id": session_id,
    "overall_score": report_data["overall_score"],
    "strengths": report_data["strengths"],
    "weaknesses": report_data["weaknesses"],
    "topic_performance": report_data["topic_scores"],
    "llm_report": report,
    "created_at": datetime.now().isoformat()
    })
    
    return report, report_data

# async def main():

#     load_dotenv()
#     GROQ_API_KEY = os.getenv("GROQ_API_KEY")

#     model_client = OpenAIChatCompletionClient(
#         model="llama-3.1-8b-instant",
#         api_key=GROQ_API_KEY,
#         base_url="https://api.groq.com/openai/v1",
#         model_info={
#             "family": "llama",
#             "context_length": 8192,
#             "vision": False,
#             "function_calling": True,
#             "json_output": True,
#             "supports_tools": True,
#             "structured_output": False,
#         },
#     )

#     jd_role = "Data Scientist / GenAI Engineer"
    
#     report_data = generate_report("c0107f4f-1b4b-49b3-b526-60273c2b3874")

#     final_report = await generate_human_report(
#         report_data=report_data,
#         job_role=jd_role,
#         llm_client=model_client
#     )
#     print("\n\nStructured Report Data:\n", json.dumps(report_data, indent=2))
#     print("\nFinal Human-Readable Report:\n", final_report)


# if __name__ == "__main__":
#     asyncio.run(main())