from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import httpx
import logging

# Import models, services, and config from our other files
from .models import ChatRequest, BatchQueryRequest, ProcessedResponse
from .services import (
    extract_text_from_pdf,
    chunk_document,
    smart_chunk_for_query,
    extract_policy_details,
    calculate_premium,
    call_policy_api_json,
    call_policy_api_stream
)
from .config import POLICY_API_BASE_URL

logger = logging.getLogger(__name__)

# We create two routers:
# 1. root_router: for endpoints like / and /health
# 2. api_router: for all endpoints starting with /api
root_router = APIRouter()
api_router = APIRouter(prefix="/api")

# ==================== Root API Routes ====================

@root_router.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Insurance Policy Processor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "batch": "/api/batch-query",
            "upload": "/api/upload-policy",
            "premium": "/api/calculate-premium"
        }
    }

@root_router.get("/health")
async def health_check():
    """
    Health check endpoint - also checks downstream Policy API
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{POLICY_API_BASE_URL}/health")
            policy_api_status = response.json()
    except Exception as e:
        policy_api_status = {"status": "unavailable", "error": str(e)}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "policy_api": policy_api_status,
        "middleware_version": "1.0.0"
    }

# ==================== Main API Routes ====================

@api_router.post("/upload-policy")
async def upload_policy(
    file: UploadFile = File(...),
    query: Optional[str] = Form(None)
):
    """
    Upload policy document (PDF or TXT) and optionally ask a question
    This processes the document and forwards to Policy API
    """
    start_time = datetime.now()
    
    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported"
        )
    
    file_content = await file.read()
    
    if file.content_type == "application/pdf":
        policy_text = extract_text_from_pdf(file_content)
    else:
        policy_text = file_content.decode('utf-8')
    
    if not policy_text.strip():
        raise HTTPException(status_code=400, detail="Extracted text is empty")
    
    # Validate minimum length
    if len(policy_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Policy text must be at least 10 characters long"
        )
    
    chunks = chunk_document(policy_text)
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    response_data = {
        "message": "Policy document processed successfully",
        "filename": file.filename,
        "total_length": len(policy_text),
        "chunks_created": len(chunks),
        "processing_time_ms": round(processing_time, 2),
        "policy_text": policy_text  # Return for frontend
    }
    
    if query:
        relevant_text = smart_chunk_for_query(policy_text, query)
        payload = {
            "policy_text": relevant_text,
            "query": query,
            "stream": False,
            "temperature": 0.7
        }
        api_response = await call_policy_api_json("/chat", payload)
        response_data["query_response"] = api_response
    
    return response_data

@api_router.post("/chat", response_model=ProcessedResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - NON-STREAMING for Query Text Mode
    Used when user provides policy_text + query directly
    """
    start_time = datetime.now()
    
    # Validation - For Query Text mode, we ALWAYS need policy_text
    if not request.policy_text:
        raise HTTPException(
            status_code=400,
            detail="policy_text is required for Query Text mode"
        )
    
    # Validate policy_text length
    if len(request.policy_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Policy text must be at least 10 characters long"
        )
    
    # Process with smart chunking
    processed_text = smart_chunk_for_query(request.policy_text, request.query)
    chunks_count = len(chunk_document(request.policy_text))
    
    # Build payload for downstream API
    payload = {
        "policy_text": processed_text,
        "query": request.query,
        "stream": False,
        "temperature": request.temperature
    }
    
    if request.query_type:
        payload["query_type"] = request.query_type
    
    # Call API (non-streaming)
    api_response = await call_policy_api_json("/chat", payload)
    
    # Calculate premium if requested
    premium_calc = None
    if request.calculate_premium:
        policy_details = extract_policy_details(request.policy_text)
        premium_calc = calculate_premium(policy_details)
    
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    return ProcessedResponse(
        query=api_response["query"],
        response=api_response["response"],
        conversation_id=api_response.get("conversation_id"),
        query_type=api_response.get("query_type"),
        processing_time_ms=round(processing_time, 2),
        cached=api_response.get("cached", False),
        premium_calculation=premium_calc,
        chunks_processed=chunks_count
    )

@api_router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming version of chat endpoint - for Document Mode
    First message: requires policy_text
    Follow-up messages: requires conversation_id
    """
    # Validation BEFORE starting stream
    if not request.conversation_id and not request.policy_text:
        raise HTTPException(
            status_code=400,
            detail="Either policy_text (new conversation) or conversation_id (follow-up) is required"
        )
    
    # ONLY validate policy_text length if it's provided AND this is a new conversation
    if request.policy_text and not request.conversation_id:
        if len(request.policy_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Policy text must be at least 10 characters long for new conversations"
            )
    
    processed_text = None
    if request.policy_text and not request.conversation_id:
        processed_text = smart_chunk_for_query(request.policy_text, request.query)
    
    # Build payload
    payload = {
        "query": request.query,
        "stream": True,
        "temperature": request.temperature
    }
    
    if request.conversation_id:
        # Follow-up question - use conversation_id
        payload["conversation_id"] = request.conversation_id
    else:
        # First question - use policy_text
        payload["policy_text"] = processed_text or request.policy_text
    
    if request.query_type:
        payload["query_type"] = request.query_type
    
    # ONLY validate processed text if it's a new conversation
    if "policy_text" in payload and not request.conversation_id:
        if len(payload["policy_text"].strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Processed policy text is too short (minimum 10 characters required)"
            )
    
    async def stream_generator():
        async for chunk in call_policy_api_stream("/chat", payload):
            yield chunk
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )

@api_router.post("/batch-query")
async def batch_query(request: BatchQueryRequest):
    """
    Process multiple queries at once against a single policy
    """
    start_time = datetime.now()
    
    if request.query_types and len(request.query_types) != len(request.queries):
        raise HTTPException(
            status_code=400,
            detail="query_types length must match queries length"
        )
    
    results = []
    for idx, query in enumerate(request.queries):
        relevant_text = smart_chunk_for_query(request.policy_text, query)
        
        payload = {
            "policy_text": relevant_text,
            "queries": [query],
            "use_cache": request.use_cache
        }
        
        if request.query_types:
            payload["query_types"] = [request.query_types[idx]]
        
        api_response = await call_policy_api_json("/batch-query", payload)
        
        if api_response.get("results"):
            results.append(api_response["results"][0])
    
    total_processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    return {
        "results": results,
        "total_processing_time_ms": round(total_processing_time, 2),
        "queries_processed": len(results)
    }

@api_router.post("/calculate-premium")
async def calculate_premium_endpoint(policy_text: str = Form(...)):
    """
    Standalone premium calculation endpoint
    """
    if not policy_text.strip():
        raise HTTPException(status_code=400, detail="Policy text is required")
    
    policy_details = extract_policy_details(policy_text)
    premium = calculate_premium(policy_details)
    
    return {
        "premium_calculation": premium,
        "extracted_details": policy_details
    }

@api_router.get("/query-types")
async def get_query_types():
    """
    Forward query types from Policy API
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{POLICY_API_BASE_URL}/query-types")
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch query types: {str(e)}"
        )
