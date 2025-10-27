import httpx
import json
import re
import PyPDF2
import logging
from io import BytesIO
from typing import List, Dict, Any, AsyncGenerator
from fastapi import HTTPException

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

# Import models and config from our other files
from .models import PremiumCalculation
from .config import POLICY_API_BASE_URL, CHUNK_SIZE, CHUNK_OVERLAP

# Configure logging
logger = logging.getLogger(__name__)

# ==================== Helper Functions ====================

def extract_text_from_pdf(pdf_file: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")

def chunk_document(text: str) -> List[str]:
    """
    Split document into chunks using LangChain's RecursiveCharacterTextSplitter
    Optimized for insurance policies
    """
    try:
        doc = Document(page_content=text)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        chunks = text_splitter.split_documents([doc])
        chunk_texts = [chunk.page_content for chunk in chunks]
        logger.info(f"Document split into {len(chunk_texts)} chunks")
        return chunk_texts
    except Exception as e:
        logger.error(f"Chunking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document chunking failed: {str(e)}")

def smart_chunk_for_query(text: str, query: str) -> str:
    """
    Intelligent chunking: If document is large, chunk it and select relevant chunks
    based on query keywords. Otherwise, return full text.
    """
    if len(text) < CHUNK_SIZE:
        return text
    
    chunks = chunk_document(text)
    query_keywords = set(re.findall(r'\b[a-zA-Z]{4,}\b', query.lower()))
    
    chunk_scores = []
    for idx, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        score = sum(1 for keyword in query_keywords if keyword in chunk_lower)
        chunk_scores.append((score, idx, chunk))
    
    chunk_scores.sort(reverse=True, key=lambda x: x[0])
    
    if chunk_scores and chunk_scores[0][0] > 0:
        relevant_chunks = [chunk for score, idx, chunk in chunk_scores[:5] if score > 0]
    else:
        relevant_chunks = chunks[:3]  # Default to first 3 chunks
    
    combined_text = "\n\n".join(relevant_chunks)
    logger.info(f"Smart chunking: Selected {len(relevant_chunks)} chunks from {len(chunks)} total")
    return combined_text

def extract_policy_details(policy_text: str) -> Dict[str, Any]:
    """
    Extract key details from policy text using regex patterns
    Used for premium calculation
    """
    details = {
        "sum_insured": None,
        "age": None,
        "coverage_type": None,
        "co_payment": None,
        "deductible": None,
        "policy_term": None
    }
    
    sum_patterns = [
        r'sum insured[:\s]+(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|crore|crores)?',
        r'coverage amount[:\s]+(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'insured amount[:\s]+(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    ]
    for pattern in sum_patterns:
        match = re.search(pattern, policy_text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            details["sum_insured"] = float(amount_str)
            break
    
    age_patterns = [
        r'age[:\s]+(\d+)\s*years?',
        r'(\d+)\s*years?\s+old',
        r'policyholder age[:\s]+(\d+)'
    ]
    for pattern in age_patterns:
        match = re.search(pattern, policy_text, re.IGNORECASE)
        if match:
            details["age"] = int(match.group(1))
            break
    
    if re.search(r'critical illness', policy_text, re.IGNORECASE):
        details["coverage_type"] = "critical_illness"
    elif re.search(r'family floater', policy_text, re.IGNORECASE):
        details["coverage_type"] = "family_floater"
    elif re.search(r'individual', policy_text, re.IGNORECASE):
        details["coverage_type"] = "individual"
    
    copay_match = re.search(r'co-?payment[:\s]+(\d+)%', policy_text, re.IGNORECASE)
    if copay_match:
        details["co_payment"] = int(copay_match.group(1))
    
    deductible_match = re.search(r'deductible[:\s]+(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*)', policy_text, re.IGNORECASE)
    if deductible_match:
        details["deductible"] = float(deductible_match.group(1).replace(',', ''))
    
    term_match = re.search(r'policy term[:\s]+(\d+)\s*years?', policy_text, re.IGNORECASE)
    if term_match:
        details["policy_term"] = int(term_match.group(1))
    
    return details

def calculate_premium(policy_details: Dict[str, Any]) -> PremiumCalculation:
    """
    Calculate insurance premium based on extracted policy details
    This is a simplified calculation - adjust based on actual requirements
    """
    base_premium = 5000.0
    
    age = policy_details.get("age") or 30
    
    # Age factor (increases with age)
    if age < 25:
        age_factor = 0.8
    elif age < 35:
        age_factor = 1.0
    elif age < 45:
        age_factor = 1.3
    elif age < 55:
        age_factor = 1.7
    else:
        age_factor = 2.2
    
    sum_insured = policy_details.get("sum_insured") or 500000
    coverage_factor = 1.0 + (sum_insured / 1000000) * 0.5
    
    copay_discount = 1.0
    if policy_details.get("co_payment"):
        copay_discount = 0.9
    
    deductible_discount = 1.0
    if policy_details.get("deductible"):
        deductible_discount = 0.95
    
    coverage_type_factor = 1.0
    if policy_details.get("coverage_type") == "critical_illness":
        coverage_type_factor = 1.4
    elif policy_details.get("coverage_type") == "family_floater":
        coverage_type_factor = 1.6
    
    total_premium = (
        base_premium * age_factor * coverage_factor * coverage_type_factor *
        copay_discount * deductible_discount
    )
    
    breakdown = {
        "base_premium": round(base_premium, 2),
        "age_multiplier": age_factor,
        "coverage_multiplier": round(coverage_factor, 2),
        "coverage_type_multiplier": coverage_type_factor,
        "copay_discount": copay_discount,
        "deductible_discount": deductible_discount,
        "policy_details": policy_details
    }
    
    return PremiumCalculation(
        base_premium=round(base_premium, 2),
        age_factor=age_factor,
        coverage_factor=round(coverage_factor, 2),
        total_premium=round(total_premium, 2),
        breakdown=breakdown
    )

# ==================== API Call Functions ====================

async def call_policy_api_json(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the Policy Summarizer API and expect a JSON response.
    This is a regular async function.
    """
    url = f"{POLICY_API_BASE_URL}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Conversation not found or expired")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif response.status_code == 503:
                raise HTTPException(status_code=503, detail="Model not loaded")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Policy API error: {response.text}"
                )
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Policy API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to Policy API: {str(e)}")

async def call_policy_api_stream(endpoint: str, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Call the Policy Summarizer API and stream the response.
    This is an async generator (uses 'yield').
    """
    url = f"{POLICY_API_BASE_URL}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream('POST', url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_detail = error_text.decode()
                    
                    # Log the error instead of raising HTTPException during stream
                    logger.error(f"Policy API error ({response.status_code}): {error_detail}")
                    
                    # Yield error as SSE format so frontend can handle it
                    yield f"data: {json.dumps({'error': error_detail, 'status_code': response.status_code})}\n\n"
                    return
                
                # Stream successful response
                async for chunk in response.aiter_text():
                    yield chunk
                    
    except httpx.TimeoutException:
        logger.error("Policy API timeout")
        yield f"data: {json.dumps({'error': 'Policy API timeout', 'status_code': 504})}\n\n"
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Policy API: {str(e)}")
        yield f"data: {json.dumps({'error': f'Failed to connect to Policy API: {str(e)}', 'status_code': 503})}\n\n"
