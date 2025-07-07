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
ENDPOINT_URL=Your URL
DEPLOYMENT_NAME=Your deployment
API_VERSION=Your api version
SEARCH_ENDPOINT=Endpoint
AZURE_OPENAI_API_KEY=Your azure open-ai key
SEARCH_KEY=Your search key
EMBEDDING_ENDPOINT=Embedding model endpoint
INDEX_NAME=Your index name