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

def load_questions_from_sheet(sheet_path):
    questions_with_options = []
    workbook = load_workbook(sheet_path)
    sheet = workbook.active
    for row in sheet.iter_rows(min_row=3, values_only=True):
        question_index = row[0]  # Question index including subletters
        question = row[1]
        quick_reply_options = row[2].split(',') if row[2] else []
        condition = row[3] if len(row) > 3 else None
        if question:
            questions_with_options.append((question_index, question, quick_reply_options, condition))
    return questions_with_options

@app.post("/question/")
async def question(request: Request):
    data = await request.json()
    question_index = data.get("question_index")
    previous_question = data.get("previous_question")
    previous_answer = data.get("previous_answer")

    if question_index is None or question_index < 1:
        raise HTTPException(status_code=400, detail="Invalid question index")

    while question_index <= len(questions_with_options):
        q_index, question, quick_reply_options, condition = questions_with_options[question_index - 1]

        if condition:
            if not is_condition_met(condition, previous_answer, quick_reply_options):
                question_index += 1
                continue
        break

    if question_index > len(questions_with_options):
        raise HTTPException(status_code=400, detail="No suitable question found")

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

    return {"rephrased_question": rephrased_question, "quick_reply_options": quick_reply_options}

def is_condition_met(condition, previous_answer, quick_reply_options):
    # Logic to check if the condition for a subquestion is met
    # Assuming condition format is "7a" and it's triggered if the first option of question 7 is chosen
    main_question_index = int(condition[:-1]) - 1
    if main_question_index < 0 or main_question_index >= len(questions_with_options):
        return False

    _, _, options, _ = questions_with_options[main_question_index]
    return options and previous_answer == options[0]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
