from dotenv import load_dotenv
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from autogen_ext.models.openai import OpenAIChatCompletionClient
from backend.controller_runner import run_interview
from backend.interview_controller import InterviewState
from backend.interview_setup import extract_jd_priorities_llm
from backend.faiss_index import ResumeFAISS  
import uuid
from fastapi import UploadFile, File, Form
import shutil
from backend.logger import setup_run_logger
from backend.analysis import generate_human_report, generate_report
import sqlite3
import yaml
import json

with open("backend/config.yaml") as f:
    CONFIG = yaml.safe_load(f)
    
session_store = {}

load_dotenv()
model_client = OpenAIChatCompletionClient(model = CONFIG["models"]["llm_model"],
                                          api_key=CONFIG["api"]["groq_api_key"],
                                          base_url="https://api.groq.com/openai/v1",
                                          model_info={
                                                "family": "llama",
                                                "context_length": 8192,
                                                "vision": False,
                                                "function_calling": True,
                                                "json_output": True,
                                                "supports_tools": True,
                                                "structured_output": False,
                                            })

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/static"), name = "static")
templates = Jinja2Templates(directory="frontend/templates")

class WebSocketInputHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        
    async def get_input(self, prompt:str, cancellation_token: Optional[object]= None) -> str:
        try:
            await self.websocket.send_text("SYSTEM_TURN:USER")
            data = await self.websocket.receive_text()
            return data
        except WebSocketDisconnect:
            print("WebSocket disconnected during input wait.")
            return "TERMINATE"
        

# #FAISS service initialization 
# faiss_service = ResumeFAISS("resume_a.pdf")

# routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Render the index.html template
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/setup")
async def setup_interview(
    role: str = Form(...),
    jd: str = Form(...),
    resume: UploadFile = File(...),
    config: str = Form(...)
):
    CONFIG = json.loads(config)
    os.makedirs("uploads", exist_ok=True)
    session_id = str(uuid.uuid4())

    resume_path = f"uploads/{session_id}.pdf"

    with open(resume_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    session_store[session_id] = {
        "role": role,
        "jd": jd,
        "resume_path": resume_path,
        "config": CONFIG
    }

    return {"session_id": session_id}

@app.websocket("/ws/interview/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):

    await websocket.accept()

    try:
        logger = setup_run_logger()
        logger.info(f"WebSocket connection established for session_id: {session_id}")

        session = session_store.get(session_id)
        logger.info(f"session store: {session_store}")

        if not session:
            await websocket.close()
            return

        job_role = session["role"]
        job_desc = session["jd"]
        resume_path = session["resume_path"]
        config = session["config"]

        # Build FAISS using uploaded resume
        faiss_service = ResumeFAISS(resume_pdf = resume_path, logger=logger)

        # Extract JD priorities
        jd_priorities, topic_objects = await extract_jd_priorities_llm(
            jd_role=job_role,
            jd_text=job_desc,
            llm_call=model_client,
            logger=logger
        )

        # Search resume evidence
        faiss_results = faiss_service.search(topic_objects, top_k=3, logger=logger)
        logger.info(f"config used in app.py: {config}")
        # Initialize interview state
        state = InterviewState(
            session_id=session_id,
            job_role=job_role,
            jd_priorities=jd_priorities,
            config = config
        )

        # Start interview controller
        await run_interview(
            websocket=websocket,
            state=state,
            llm_client=model_client,
            faiss_results=faiss_results,
            logger=logger
        )

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error: {e}")
        

@app.get("/evaluation/{session_id}")
async def get_evaluation(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        job_role = "Junior Data Scientist"
    else:
        job_role = session["role"]
    report, report_data = await generate_human_report(model_client, session_id, job_role=job_role)
    print(f"Generated report {type(report)}: {report}")
    return {
    "report": report,
    "report_data": report_data
    }
    
@app.get("/evaluation-nollm/{session_id}")
def get_evaluation_nollm(session_id: str):
    report_data = generate_report(session_id)
    return {
    "report": "",
    "report_data": report_data
    }
    
@app.get("/interviews")
async def get_interviews():

    conn = sqlite3.connect("data/interviews.db")
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT 
            session_id,
            job_role,
            MAX(timestamp) as date,
            AVG(
                satisfaction *
                CASE confidence
                    WHEN 'low' THEN 0.5
                    WHEN 'medium' THEN 1.0
                    WHEN 'high' THEN 1.5
                    ELSE 1.0
                END
            ) / 1.5 as overall_score
        FROM interview_turns
        GROUP BY session_id
        ORDER BY MAX(timestamp) DESC
    """).fetchall()

    interviews = [
        {
            "session_id": r[0],
            "job_role": r[1],
            "date": r[2],
            "overall_score": round(r[3], 2)
        }
        for r in rows
    ]

    return interviews

@app.get("/transcript/{session_id}")
def get_transcript(session_id: str):

    conn = sqlite3.connect("data/interviews.db")
    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT question, answer
        FROM interview_turns
        WHERE session_id=?
        ORDER BY question_number
        """,
        (session_id,)
    ).fetchall()

    transcript = []

    for q, a in rows:

        transcript.append({
            "role": "interviewer",
            "content": q
        })

        transcript.append({
            "role": "candidate",
            "content": a
        })

    return {"transcript": transcript}