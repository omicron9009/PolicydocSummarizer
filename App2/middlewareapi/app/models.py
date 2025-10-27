from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# ==================== Pydantic Models ====================

class ChatRequest(BaseModel):
    policy_text: Optional[str] = None
    query: str
    conversation_id: Optional[str] = None
    query_type: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = 0.7
    calculate_premium: bool = False

class BatchQueryRequest(BaseModel):
    policy_text: str
    queries: List[str]
    query_types: Optional[List[str]] = None
    use_cache: bool = True

class PremiumCalculation(BaseModel):
    base_premium: float
    age_factor: float
    coverage_factor: float
    total_premium: float
    breakdown: Dict[str, Any]

class ProcessedResponse(BaseModel):
    query: str
    response: str
    conversation_id: Optional[str] = None
    query_type: Optional[str] = None
    processing_time_ms: float
    cached: bool
    premium_calculation: Optional[PremiumCalculation] = None
    chunks_processed: Optional[int] = None

class TestData(BaseModel):
    key: str
    value: Any
