from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import datetime
import os
import uvicorn
import time
from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from utils.llm_invoke import call_llm_async_with_retry

load_dotenv()

# Cosmos DB configuration
cosmos_connection_string = os.getenv("COSMOS_CONNECTION_STRING")
database_name = os.getenv("COSMOS_DB_NAME", "chatdb")
container_name = os.getenv("COSMOS_CONTAINER_NAME", "chatcontainer")

# Initialize Cosmos DB client
client = CosmosClient.from_connection_string(cosmos_connection_string)
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

# FastAPI setup
app = FastAPI(
    title="AZURE AI CHATBOT API",
    version="0.0.1",
    description="API for Azure AI Chatbot with Cosmos DB and Azure Cognitive Search",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS setup
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins_list = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# --- Models ---

class ScoreOnly(BaseModel):
    search_score: float
    reranker_score: float

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime.datetime

class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: str
    user_roles: List[str] = []

class ChatResponse(BaseModel):
    response: str
    session_id: str
    elapsed_time: float
    first_chunk: Optional[ScoreOnly]
    second_chunk: Optional[ScoreOnly]

class FeedbackRequest(BaseModel):
    id: str
    feedback: str
    sessionId: str

# --- Utility to save messages ---

def save_message_to_cosmos(session_id, user_id, role, content, user_roles=None, feedback=None, timestamp=None, top_chunks=None):
    message = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "user_roles": user_roles or [],
        "role": role,
        "content": content,
        "timestamp": timestamp or datetime.datetime.utcnow().isoformat(),
        "feedback": feedback,
        "top_chunks": top_chunks or []
    }
    container.create_item(body=message)

# --- Routes ---

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_timestamp = datetime.datetime.utcnow().isoformat()

        # Save user message
        save_message_to_cosmos(
            session_id=request.session_id,
            user_id=request.user_id,
            role="user",
            content=request.message,
            user_roles=request.user_roles,
            feedback=None,
            timestamp=user_timestamp
        )

        start_time = time.time()

        # LLM + Azure Cognitive Search call
        response_data = await call_llm_async_with_retry(request.message, request.session_id)

        response_text = response_data["response"]
        top_chunks = response_data.get("top_chunks", [])

        end_time = time.time()
        elapsed_seconds = round(end_time - start_time, 3)

        assistant_timestamp = datetime.datetime.utcnow().isoformat()

        # Save assistant response with top_chunks to Cosmos
        save_message_to_cosmos(
            session_id=request.session_id,
            user_id=request.user_id,
            role="assistant",
            content=f"{response_text}\n\n_⏱️ Response time: {elapsed_seconds} seconds_",
            user_roles=request.user_roles,
            feedback=None,
            timestamp=assistant_timestamp,
            top_chunks=top_chunks
        )

        # Prepare response chunks (only scores)
        first_chunk_scores = None
        second_chunk_scores = None

        if len(top_chunks) > 0:
            first_chunk_scores = ScoreOnly(
                search_score=top_chunks[0].get("search_score", 0),
                reranker_score=top_chunks[0].get("reranker_score", 0)
            )
        if len(top_chunks) > 1:
            second_chunk_scores = ScoreOnly(
                search_score=top_chunks[1].get("search_score", 0),
                reranker_score=top_chunks[1].get("reranker_score", 0)
            )

        return ChatResponse(
            response=response_text,#+"/nElapsed time in seconds:"+str(elapsed_seconds)+"/nFirst chunk scores:"+str(first_chunk_scores)+"/nSecond chunk scores"+str(second_chunk_scores),
            session_id=request.session_id,
            elapsed_time=elapsed_seconds,
            first_chunk=first_chunk_scores,
            second_chunk=second_chunk_scores
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/update-feedback")
async def update_feedback(feedback_request: FeedbackRequest):
    try:
        message_id = feedback_request.id
        feedback = feedback_request.feedback
        session_id = feedback_request.sessionId

        if not message_id or feedback not in ['positive', 'negative'] or not session_id:
            return JSONResponse(content={"error": "Invalid input"}, status_code=400)

        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": message_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not items:
            return JSONResponse(content={"error": "Message not found in database"}, status_code=404)

        item = items[0]
        item['feedback'] = feedback
        container.replace_item(item=message_id, body=item)

        return {"messageId": message_id, "feedback": feedback}

    except Exception as e:
        return JSONResponse(content={"error": "Failed to update feedback"}, status_code=500)

@app.get("/")
async def root():
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/session/new")
async def create_new_session():
    return {"session_id": str(uuid.uuid4())}

# --- Run locally ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)