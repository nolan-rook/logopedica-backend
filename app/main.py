import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from orquesta_sdk import Orquesta, OrquestaClientOptions
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize Orquesta client
def init_orquesta_client():
    api_key = os.getenv("ORQUESTA_API_KEY")
    options = OrquestaClientOptions(api_key=api_key, environment="production")
    return Orquesta(options)

client = init_orquesta_client()

# Load questions from sheet
def load_questions_from_sheet(sheet_path):
    questions = []
    workbook = load_workbook(sheet_path)
    sheet = workbook.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        question = row[2]
        if question:
            questions.append(question)
    return questions

questions = load_questions_from_sheet('data/vragenlijst.xlsx')

# POST endpoint to process a question
@app.post("/question/")
async def question(request: Request):
    data = await request.json()
    question_index = data.get("question_index")
    previous_question = data.get("previous_question")
    previous_answer = data.get("previous_answer")

    if question_index is None or question_index < 1 or question_index > len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index")

    question = questions[question_index - 1]

    previous_context = ""
    if previous_question and previous_answer:
        previous_context = f"Vraag: {previous_question}\nAntwoord: {previous_answer}"

    deployment = client.deployments.invoke(
        key="logopedica-vragenlijsten",
        context={
            "environments": [],
            "klacht": ["mondgewoonten"]
        },
        inputs={
            "question": question,
            "previous": previous_context
        }
    )
    rephrased_question = deployment.choices[0].message.content

    return {"rephrased_question": rephrased_question}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
