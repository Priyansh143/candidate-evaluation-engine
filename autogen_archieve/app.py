from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from controller_runner import run_interview
from interview_controller import InterviewState
from interview_setup import extract_jd_priorities_stub
from faiss_index import ResumeFAISS  
import uuid

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
model_client = OpenAIChatCompletionClient(model = "llama-3.1-8b-instant",
                                          api_key=GROQ_API_KEY,
                                          base_url="https://api.groq.com/openai/v1",
                                          model_info={
                                                "family": "llama",
                                                "context_length": 8192,
                                                "vision": False,
                                                "function_calling": True,
                                                "json_output": True,
                                                "supports_tools": True,
                                                "structured_output": False,
                                            },)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name = "static")
templates = Jinja2Templates(directory="templates")

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
        
async def create_interview_team(websocket: WebSocket, job_position: str):

    handler = WebSocketInputHandler(websocket)
    
    system_agent = AssistantAgent(
        name="System",
        model_client=None,  # IMPORTANT: no LLM
        system_message="""
            You are a system controller.
            You only forward instructions.
            You never generate content.
            """
    )

    interviewer = AssistantAgent(
        name="Interviewer",
        model_client=model_client,
        system_message=f"""
            You are an interviewer for a {job_position} role.

            You will receive explicit instructions from the system.
            Follow them exactly.

            Rules:
            - Ask ONLY the question requested
            - Ask ONE question at a time
            - Do NOT explain, evaluate, or give hints
            - Do NOT decide when to stop
            - Do NOT ask follow-up questions unless instructed
            """
    )

    candidate = UserProxyAgent(
        name="Candidate",
        input_func=handler.get_input
    )

    evaluator = AssistantAgent(
        name="Evaluator",
        model_client=model_client,
        system_message=f"""
            You are an interview evaluator for a {job_position} role.

            For EACH candidate answer, return ONLY a JSON object with:
            - satisfaction: float between 0 and 1
            - confidence: one of ["low", "medium", "high"]
            - strengths: list of short strings
            - weaknesses: list of short strings

            Rules:
            - Output ONLY valid JSON
            - Do NOT include explanations
            - Do NOT summarize the interview
            - Do NOT add any text outside JSON
            """
    )

    team = RoundRobinGroupChat(
        participants=[system_agent, interviewer, candidate, evaluator],
        termination_condition=None,   # controller decides termination
        max_turns=100                 # hard safety cap
    )

    return team, system_agent, interviewer, evaluator


#FAISS service initialization 
faiss_service = ResumeFAISS("resume_a.pdf")

# routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Render the index.html template
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/interview")
async def websocket_endpoint(websocket: WebSocket, pos: str = Query("AI Engineer")):
    await websocket.accept()

    try:
        # 1. Create agents (NO logic here)
        team, system_agent, interviewer, evaluator = await create_interview_team(websocket, pos)

        # 2. Extract JD priorities (stub for now)
        jd_priorities = extract_jd_priorities_stub(
            job_role=pos,
            job_description="PLACEHOLDER JD TEXT"
        )

        # 3. Initialize controller state
        state = InterviewState(
            session_id = str(uuid.uuid4()),
            job_role=pos,
            jd_priorities=jd_priorities
        )
        

        # 4. Hand control to controller_runner
        await run_interview(
            websocket=websocket,
            team=team,
            state=state,
            system_agent=system_agent,
            interviewer=interviewer,
            evaluator=evaluator,
            faiss_search= faiss_service.search
        )

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error: {e}")