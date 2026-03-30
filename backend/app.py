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
import logging

PROFILE_PATH = "data/profile.json"
CONFIG_PATH = "config.yaml"
session_store = {}
model_client = None
use_profile = False
app = FastAPI()

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f) 

app.mount("/static", StaticFiles(directory="frontend/static"), name = "static")
templates = Jinja2Templates(directory="frontend/templates")


# utils
def log_and_raise(logger, stage, e):
    logger.exception(f"[ERROR] Failure during {stage}: {str(e)}")
    raise

def delete_resume(session_id: str):
    resume_path = f"data/uploads/{session_id}.pdf"
    try:
        if os.path.exists(resume_path):
            os.remove(resume_path)
    except OSError as e:
        print(f"Failed to delete resume: {e}")

# websocket handler
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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "api_key": CONFIG.get("api", {}).get("groq_api_key", "")
        })

@app.get("/config")
def get_config():
    return CONFIG 

@app.post("/setup")
async def setup_interview(
    role: str = Form(...),
    jd: str = Form(...),
    resume: Optional[UploadFile] = File(None),
    config: str = Form(...)
):
    global model_client  
    CONFIG = json.loads(config)
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
    session_id = str(uuid.uuid4())
    resume_path = None
    if (resume):
        os.makedirs("data/uploads", exist_ok=True)
        resume_path = f"data/uploads/{session_id}.pdf"

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
        session = session_store.get(session_id)
        logger = setup_run_logger()
        
        if not session:
            await websocket.close()
            return
        
        job_role = session["role"]
        job_desc = session["jd"]
        resume_path = session["resume_path"]
        config = session["config"]
        
        
        if not config["logging"]["enabled"]:
            logger.disabled = True
        else:
            level = getattr(logging, config["logging"]["level"].upper(), logging.INFO)
            logger.setLevel(level)
        
        logger.info(f"WebSocket connection established for session_id: {session_id}")
        logger.info(f"session store: {session_store}")

        # Build FAISS using uploaded resume
        try:
            faiss_service = ResumeFAISS(resume_pdf = resume_path, logger=logger)
        except Exception as e:
            log_and_raise(logger, "Build FAISS", e)
            
        try: 
            # Extract JD priorities
            jd_priorities, topic_objects = await extract_jd_priorities_llm(
                jd_role=job_role,
                jd_text=job_desc,
                max_topics=config["interview"]["max_topics"],
                llm_call=model_client,
                logger=logger
            )
        except Exception as e:
            log_and_raise(logger, "extract_jd_priorities", e)

        # Search resume evidence
        try:
            faiss_results = faiss_service.search(topic_objects, top_k=3,resume_path=resume_path, logger=logger)
        except Exception as e:
            log_and_raise(logger, "FAISS Search", e)
        logger.info(f"config used in app.py: {config}")
        logger.info(f"all evidence: {faiss_results}")
        # Initialize interview state
        state = InterviewState(
            session_id=session_id,
            job_role=job_role,
            jd_priorities=jd_priorities,
            config = config
        )

        # Start interview controller
        try:
            await run_interview(
                websocket=websocket,
                state=state,
                llm_client=model_client,
                faiss_results=faiss_results,
                logger=logger
            )
        except Exception as e:
            log_and_raise(logger, "run_interview", e)

    except WebSocketDisconnect:
        delete_resume(session_id)
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
    conn = sqlite3.connect("data/interviews.db")
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT llm_report FROM interview_reports WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    report = row[0] if row else None
    report_data = generate_report(session_id)
    return {
    "report": report,
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

# ensure file exists
def init_profile():
    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "w") as f:
            json.dump({
                "experience": [],
                "projects": [],
                "skills": [],
                "achievements": [],
                "research": []
            }, f, indent=2)


@app.post("/profile")
async def save_profile(profile: str = Form(...)):
    init_profile()

    data = json.loads(profile)

    with open(PROFILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return {"message": "Profile saved"}

@app.get("/profile")
async def get_profile():
    init_profile()

    try:
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        return {"profile": data}
    except:
        return {"profile": None}
    
@app.post("/api_key")
async def save_api_key(api_key: str = Form(...)):

    # Load existing config
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        config = {}

    # Ensure api section exists
    if "api" not in config:
        config["api"] = {}

    # Update API key
    config["api"]["groq_api_key"] = api_key

    # Write back to YAML
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f)

    return {"status": "success"}