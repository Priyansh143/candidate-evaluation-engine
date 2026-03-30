# InterviewSim AI

An end-to-end, AI-powered multi-agent interview simulation platform that guides a candidate through a configurable interview flow, generates questions dynamically using an LLM, retrieves relevant evidence from the candidate profile/resume and job description context, evaluates answers in real time, and produces a post-interview report with transcript history.


## Demo



## Key Features

* Upto 100 free interviews per day using free Groq API key.
* Mulit-agent system with lightning fast interviews and evaluations ( ~1 sec / response).
* Configurable Interview and Interviewer itself!
* Interactive AI interview chat flow
* Resume/profile and job-description-driven questioning
* Dynamic & unpredictable questioning.
* Interview evaluation, topic wise scoring and report generation.
* Interview Transcript viewing and interview history with evaluations.
* Modern cyber aesthetic UI/UX design.
* Dockerized setup for reproducible execution


## Tech Stack

* **Frontend**: HTML, CSS, JavaScript 
* **Backend**: Python, FastAPI 
* **LLM Integration**: Groq API (inference), Autogen (agent initialization)
* **Retrieval**: FAISS
* **Storage**: SQLite
* **Containerization**: Docker, Docker Compose


## Installation

### Prerequisites

- Git
- Python 3.10+ (for local run)
- Docker Desktop (for Docker run)

### Clone the Repository

```bash
git clone <your-repo-url>
cd InterviewEvaluationSys
````

## Run the Application

You can run the project in two ways.

### Option 1 — Run with Python

```bash
python run.py
```

This will automatically:

* create a virtual environment if it does not exist
* install the required dependencies
* start the FastAPI server

Open the application in your browser:

```bash
http://localhost:8000
```

---

### Option 2 — Run with Docker
<details>
<summary> Click to expand </summary>
Build the Docker image:

```bash
docker build -t interview-ai .
```

Start the application using Docker Compose:

```bash
docker compose up
```

Open the application in your browser:

```bash
http://localhost:8000
```

### Stop the Application

```bash
docker compose stop
```

To remove the container:

```bash
docker compose down
```

The interview data stored in the Docker volume will remain unless the volume is removed manually.

</details>

## Screenshots
<details>
<summary> Click to expand </summary>

```md

### Home Screen
![Home Screen](Docs/screens/main-screen.png)

### Interview in Progress
![Interview Screen](Docs/screens/chat-screen.png)

### Evaluation Report
![Evaluation Report](docs/screens/evaluation-1.png)
![Evaluation Report](docs/screens/evaluation-2.png)

### Transcript Modal
![Transcript Modal](Docs/screenshots/transcript-modal.png)

### Profile Screen
![Profile Screen](Docs/screens/profile-screen.png)

### Past Interviews
![Past Interviews](Docs/screens/past-interviews.png)

### Config Screen
![Config Screen](Docs/screens/config-screen.png)

```
</details>

## Architecture

<details>
<summary> Click to expand </summary>
The system is organized around five main components:

* **User**: Starts the interview, answers questions, reviews results, and opens the transcript.
* **Frontend**: Handles UI state, settings, interview chat, loading screens, report display, and transcript modal.
* **Backend**: Orchestrates session setup, state management, retrieval, question generation, answer evaluation, and persistence.
* **LLM**: Generates interview questions and evaluation summaries.
* **Database**: Stores session data, interview turns, evaluation output, and history.

![Architecture Diagram](Docs/diagrams/architectureDiagram.png)
Evaluation Engine is part of backend, separately shown for better understanding.

</details>


## Sequence Diagram

<details>
<summary> Click to expand </summary>


![End-to-End AI Interview Session Sequence Diagram](Docs/diagrams/sequenceDiagram.png)

> This diagram shows the complete interview lifecycle, from session setup to transcript review.

</details>

## Project Structure

<details>
<summary> Click to expand </summary>


```text
.
├── backend/
├── frontend/
├── docs/
├── .env
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
├── .gitignore
├── .dockerignore
├── config.yaml
└── README.md
```
</details>


## API Endpoints
<details>
<summary> Click to expand </summary>

Update this section to match your real routes.

```text
POST /setup
POST /startInterview
POST /send_text
GET  /evaluation/{sessionId}
GET  /transcript/{sessionId}
```

Responsibilities:

* `POST /setup` — initialize interview settings and session data
* `POST /startInterview` — begin the interview workflow
* `POST /send_text` — submit a user answer
* `GET /evaluation/{sessionId}` — fetch the final report
* `GET /transcript/{sessionId}` — fetch interview transcript data
</details>

## Future Improvements

* Deployed Web-Application
* Voice enabled interviews using TTS-STT models.
* More Interviewer States
* More types of interviews (Eg- Technical, aptitude, cultural fit, etc) 
* Camera enabled interview with timer.
* Expanded admin or history dashboard
* User's overall skill tracking and analysis
* Exportable PDF report

## Known Limitations

* The project depends on external LLM responses from groq.
* Evaluation quality may vary based on model output.
* The retrieval quality depends on the resume/profile data provided.


## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.


## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.

