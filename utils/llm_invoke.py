import asyncio
import os
import requests
from dotenv import load_dotenv

from utils.cosmos_connection import get_last_messages_from_cosmos
from utils.log_utils import debug_print

load_dotenv()

endpoint = os.getenv("ENDPOINT_URL")
deployment = os.getenv("DEPLOYMENT_NAME")
api_version = os.getenv("API_VERSION")
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_KEY")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
Embedding_Endpoint = os.getenv("EMBEDDING_ENDPOINT")
index_name = os.getenv("INDEX_NAME")

from openai import AzureOpenAI


async def warm_up_search_index():
    try:
        debug_print("Starting search index warmup...")
        warmup_response = await call_llm_async_with_retry("What is this document about?", "warmup-session", max_retries=1)
        debug_print(f"Warmup response: {warmup_response}")
        return True
    except Exception as e:
        debug_print(f"Warmup failed: {str(e)}")
        return False


def query_azure_search(query: str, top_k: int = 5):
    headers = {
        "Content-Type": "application/json",
        "api-key": search_key
    }
    url = f"{search_endpoint}/indexes/{index_name}/docs/search?api-version=2023-07-01-preview"
    body = {
        "search": query,
        "queryType": "semantic",
        "semanticConfiguration": "pr1semantic",
        "top": top_k,
        "captions": "extractive",
        "answers": "extractive",
        "queryLanguage": "en-us",
        "speller": "lexicon"
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    response_json = response.json()

    results = response_json.get("value", [])
    debug_print("Raw search results:", results)

    # Sort by @search.score instead of reranker
    sorted_results = sorted(results, key=lambda x: x.get("@search.rerankerScore", 0), reverse=True)
    return sorted_results[:top_k]


def format_chunks_for_prompt(chunks):
    formatted = []
    for i, chunk in enumerate(chunks):
        content = chunk.get("content", chunk.get("text", ""))
        score = chunk.get("@search.score", 0)
        rerank = chunk.get("@search.rerankerScore", 0)
        image_url = chunk.get("metadata_storage_path", "")

        # Add image URL if it looks like an image
        if image_url.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
            content += f"\n[Image reference: {image_url}]"

        formatted.append(f"Source {i+1} (score={score:.4f}, reranker={rerank:.4f}):\n{content}")
    return "\n\n".join(formatted)



async def call_llm_async_with_retry(user_input: str, session_id: str, max_retries: int = 3, delay: int = 2):
    debug_print(f"User Query: {user_input}")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version=api_version,
    )

    prompt_header = """You are a helpful and knowledgeable document assistant chatbot. Your primary role is to help users find information from their documents using an integrated search system.

            CORE BEHAVIOR:
            - Always try to provide a helpful response, even if the information is partial
            - Be conversational and friendly in your tone
            - When you have relevant information, present it clearly and confidently
            - Maintain conversation continuity by referencing previous exchanges when relevant
            - Only give the information present in the document,it is really important to NEVER EVER give answers based on your assumptions or outside the documents.
            - If there are any image links (e.g. Azure Blob Storage) from XML files, you must include them in your answer.
            - Position the image links exactly where they are referred to in the XML document. For example, if a paragraph references "Figure 1", include the image URL at that point in the answer.
            
            RESPONSE GUIDELINES:
            1. ALWAYS attempt to answer based on available document content
            2. If you find relevant information, provide a comprehensive response with specific details
            3. If information is partial, say "Based on the available information..." and provide what you can
            4. Ask clarifying questions when the user's intent is unclear
            5. Provide context and explain technical terms when necessary
            6. Providing links is mandatory if present — especially for images embedded in XML. Example: "As shown in Figure 1: [image URL]"

            CONVERSATION FLOW:
            - Acknowledge the user's question
            - Search through available documents
            - Provide the most relevant information found
            - Provide links if available
            - Offer additional help or related information when appropriate
            - Reference previous conversation context when it adds value to the current response

            IMPORTANT: You are strictly forbidden from answering using your own knowledge or anything outside the retrieved documents.
            Remember: You are designed to be maximally helpful. Even when perfect information isn't available, guide the user toward useful insights or suggest ways to refine their search."""

    cosmos_messages = get_last_messages_from_cosmos(session_id, limit=5)

    # Get top chunks from Azure Search
    top_chunks = query_azure_search(user_input+str("?"), top_k=5)
    formatted_context = format_chunks_for_prompt(top_chunks)

    full_prompt = f"{prompt_header}{formatted_context}\n\nQUESTION: {user_input+str("?")}"

    chat_prompt = []
    if cosmos_messages:
        for msg in cosmos_messages:
            chat_prompt.append({"role": msg["role"], "content": msg["content"]})

    chat_prompt.append({"role": "user", "content": full_prompt})
    debug_print("Final Prompt Sent to LLM", full_prompt)

    last_response = None
    last_error = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                await asyncio.sleep(delay)

            loop = asyncio.get_event_loop()
            completion = await loop.run_in_executor(None, lambda: client.chat.completions.create(
                model=deployment,
                messages=chat_prompt,
                max_tokens=1000,
                temperature=0,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stream=False,
                extra_body={
                    "data_sources": [{
                        "type": "azure_search",
                        "parameters": {
                            "filter": None,
                            "endpoint": f"{search_endpoint}",
                            "index_name": f"{index_name}",
                            "semantic_configuration": "pr1semantic",
                            "authentication": {
                                "type": "api_key",
                                "key": f"{search_key}"
                            },
                            "embedding_dependency": {
                                "type": "endpoint",
                                "endpoint": Embedding_Endpoint,
                                "authentication": {
                                    "type": "api_key",
                                    "key": subscription_key
                                }
                            },
                            "query_type": "semantic",   # Use simple query for better performance
                            "in_scope": True,
                            "strictness": 1,
                            "top_n_documents": 15
                        }
                    }]
                }
 
            ))

            choice = completion.choices[0]
            response_content = choice.message.content
            debug_print("LLM Response Content", response_content)

            return {
                "response": response_content,
                "top_chunks": [{
                    "content": chunk.get("content", chunk.get("text", "")),
                    "search_score": round(chunk.get("@search.score", 0), 4),
                    "reranker_score": round(chunk.get("@search.rerankerScore", 0), 4),
                    "source": chunk.get("metadata_storage_path", "")
                } for chunk in top_chunks[:2]]
            }

        except Exception as e:
            last_error = e
            if attempt >= max_retries - 1:
                raise e

    if last_response:
        return {
            "response": last_response,
            "top_chunks": []
        }
    elif last_error:
        raise last_error

    return None
