# 🤖 Azure AI Chatbot API

A FastAPI-based chatbot API that integrates Azure OpenAI, Azure Cognitive Search (with semantic reranker), and Cosmos DB for storing chat history and feedback. Built for scalable AI-assisted conversations with full traceability and performance logging.

---

## 🚀 Features

- ⚡ FastAPI backend with async support
- 🔍 Semantic search via Azure Cognitive Search
- 🧠 LLM response generation via Azure OpenAI
- 💾 Chat history and feedback stored in Azure Cosmos DB
- 🧪 CORS-enabled for frontend integration
- 🕒 Tracks response time and top search chunk scores

---

## 🛠️ Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure Cognitive Search](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search)
- [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction)
- [Python 3.10+](https://www.python.org/)
- [Uvicorn](https://www.uvicorn.org/)

---

## 🧩 Directory Structure

.
├── main.py # FastAPI app
├── utils/
│ └── llm_invoke.py # Azure OpenAI + Cognitive Search logic
├── .env # Environment variables
├── requirements.txt # Python dependencies
└── README.md # Project documentation

yaml
Copy
Edit

---

## ⚙️ Environment Variables (`.env`)

Create a `.env` file in the root directory with the following keys:

```env
COSMOS_CONNECTION_STRING=your_cosmos_connection_string
COSMOS_DB_NAME=chatdb
COSMOS_CONTAINER_NAME=chatcontainer

ALLOWED_ORIGINS=http://localhost:3000,https://yourfrontend.com
📦 Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
🏃 Run the Server
bash
Copy
Edit
uvicorn main:app --reload
By default, the app runs at: http://localhost:8000

📬 API Endpoints
POST /chat
Send a message and receive a chatbot response (powered by Azure OpenAI + Cognitive Search).

Request Body:

json
Copy
Edit
{
  "message": "Hello, what is Azure Cognitive Search?",
  "session_id": "abc123",
  "user_id": "user42",
  "user_roles": ["admin"]
}
Response:

json
Copy
Edit
{
  "response": "Azure Cognitive Search is a cloud search service...",
  "session_id": "abc123",
  "elapsed_time": 1.234,
  "first_chunk": {
    "search_score": 4.56,
    "reranker_score": 1.23
  },
  "second_chunk": {
    "search_score": 3.99,
    "reranker_score": 0.97
  }
}
POST /update-feedback
Attach user feedback to a previous assistant message.

Request Body:

json
Copy
Edit
{
  "id": "message-uuid",
  "feedback": "positive",
  "sessionId": "abc123"
}
GET /session/new
Returns a new UUID-based session ID.

Response:

json
Copy
Edit
{ "session_id": "uuid-generated" }
GET /
Health check endpoint.

🧪 Sample .env for Testing
env
Copy
Edit
COSMOS_CONNECTION_STRING=AccountEndpoint=https://...;AccountKey=...
COSMOS_DB_NAME=chatdb
COSMOS_CONTAINER_NAME=chatcontainer
ALLOWED_ORIGINS=*
📝 Notes
All chat messages (user and assistant) are stored in Cosmos DB.

The assistant response includes top-2 reranked search chunks (with scores).

Feedback (positive / negative) can be posted later using the message ID.

🔐 Security
CORS is configured via .env.

You can add bearer token auth or other middleware as needed.