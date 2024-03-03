from typing import List, Optional
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.beta.threads.run import RequiredAction, LastError
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


app = FastAPI()
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # or the origin of your ReactJS app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(
    api_key=api_key,
)
assistant_id = assistant_id
run_finished_states = ["completed", "failed", "cancelled", "expired", "requires_action"]


# Existing Pydantic models
class RunStatus(BaseModel):
    run_id: str
    thread_id: str
    status: str
    required_action: Optional[RequiredAction]
    last_error: Optional[LastError]


class ThreadMessage(BaseModel):
    content: str
    role: str
    hidden: bool
    id: str
    created_at: int


class Thread(BaseModel):
    messages: List[ThreadMessage]


class CreateMessage(BaseModel):
    content: str


# New Pydantic model for file upload
class FileUpload(BaseModel):
    files: List[UploadFile]


@app.get("/")
async def read_root():
    return {"message": "Welcome to the ChatPly"}


# New endpoint for viewing thread history
@app.get("/api/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    # Implement logic to retrieve the history of the specified thread
    # You may use OpenAI API or a database to fetch historical messages
    # Return the history as a response
    return JSONResponse(content={"message": "Thread history retrieved successfully"})


# New endpoint for uploading files
@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    # Process the uploaded files (e.g., save to disk, store in a database)
    # You may customize this logic based on your specific requirements
    # For simplicity, this example just returns a success message
    return {"message": "Files uploaded successfully"}


# Existing endpoints
@app.post("/api/new")
async def post_new():
    thread = await client.beta.threads.create()
    await client.beta.threads.messages.create(
        thread_id=thread.id,
        content="Greet the user and tell it about yourself and ask it what it is looking for.",
        role="user",
        metadata={"type": "hidden"},
    )
    run = await client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant_id
    )

    return RunStatus(
        run_id=run.id,
        thread_id=thread.id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error,
    )


@app.get("/api/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    run = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error,
    )


@app.post("/api/threads/{thread_id}/runs/{run_id}/tool")
async def post_tool(thread_id: str, run_id: str, tool_outputs: List[ToolOutput]):
    run = await client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id, thread_id=thread_id, tool_outputs=tool_outputs
    )
    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error,
    )


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    messages = await client.beta.threads.messages.list(thread_id=thread_id)

    result = [
        ThreadMessage(
            content=message.content[0].text.value if message.content else "",
            role=message.role,
            hidden="type" in message.metadata and message.metadata["type"] == "hidden",
            id=message.id,
            created_at=message.created_at,
        )
        for message in messages.data
    ]

    return Thread(
        messages=result,
    )


@app.post("/api/threads/{thread_id}")
async def post_thread(thread_id: str, message: CreateMessage):
    await client.beta.threads.messages.create(
        thread_id=thread_id, content=message.content, role="user"
    )

    run = await client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )

    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
