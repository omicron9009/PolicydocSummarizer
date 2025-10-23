import streamlit as st
import requests
import hashlib
import time
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import PyPDF2
import mammoth
from io import BytesIO
import json


# ============================================================================
# CONFIGURATION & DATA STRUCTURES
# ============================================================================


API_BASE_URL = "http://localhost:8000"


@dataclass
class Chunk:
    """Efficient chunk representation"""
    id: str
    text: str
    page: int
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict


@dataclass
class DocumentMetadata:
    """Document metadata for validation"""
    filename: str
    file_type: str
    total_pages: int
    total_chars: int
    word_count: int
    hash: str
    upload_time: datetime
    is_valid: bool
    validation_score: float


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================


st.set_page_config(
    page_title="PolicyDocSummarizer",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================================
# SLEEK GREY-BLACK-WHITE CHATBOT UI
# ============================================================================


st.markdown("""
<style>
    /* Import Modern Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ============================================ */
    /* GLOBAL RESET */
    /* ============================================ */
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .stApp {
        background: #f8f9fa;
    }
    
    .block-container {
        padding: 0;
        max-width: 100%;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ============================================ */
    /* CHAT LAYOUT - FULL SCREEN */
    /* ============================================ */
    
    .chat-layout {
        display: flex;
        flex-direction: column;
        height: 100vh;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* ============================================ */
    /* TOP HEADER BAR */
    /* ============================================ */
    
    .top-bar {
        background: white;
        border-bottom: 1px solid #e5e7eb;
        padding: 16px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: sticky;
        top: 0;
        z-index: 100;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    
    .app-title-section {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .app-icon {
        font-size: 24px;
    }
    
    .app-title {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.3px;
    }
    
    .mode-toggle {
        display: flex;
        background: #f3f4f6;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    
    .mode-btn {
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        border: none;
        background: transparent;
        color: #6b7280;
    }
    
    .mode-btn.active {
        background: white;
        color: #111827;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* ============================================ */
    /* CHAT MESSAGES AREA */
    /* ============================================ */
    
    .messages-area {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }
    
    .message-wrapper {
        display: flex;
        gap: 16px;
        animation: fadeIn 0.3s ease-out;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }
    
    .avatar-user {
        background: #111827;
        color: white;
    }
    
    .avatar-assistant {
        background: #e5e7eb;
        color: #374151;
    }
    
    .message-content {
        flex: 1;
        padding-top: 6px;
    }
    
    .message-text {
        color: #111827;
        font-size: 15px;
        line-height: 1.7;
    }
    
    .message-text p {
        margin: 0 0 12px 0;
    }
    
    /* ============================================ */
    /* BOTTOM INPUT AREA */
    /* ============================================ */
    
    .input-area {
        border-top: 1px solid #e5e7eb;
        padding: 16px 24px 24px;
        background: white;
    }
    
    .input-container {
        max-width: 850px;
        margin: 0 auto;
        position: relative;
    }
    
    /* Custom Input Box */
    .custom-input-wrapper {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        padding: 14px 48px 14px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    
    .custom-input-wrapper:focus-within {
        border-color: #111827;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .custom-input-wrapper input {
        flex: 1;
        border: none;
        outline: none;
        font-size: 15px;
        color: #111827;
        background: transparent;
    }
    
    .custom-input-wrapper input::placeholder {
        color: #9ca3af;
    }
    
    .upload-icon-btn {
        color: #6b7280;
        cursor: pointer;
        font-size: 20px;
        transition: all 0.2s;
        padding: 4px;
        border-radius: 4px;
    }
    
    .upload-icon-btn:hover {
        color: #111827;
        background: #f3f4f6;
    }
    
    .send-btn {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        background: #111827;
        color: white;
        border: none;
        border-radius: 8px;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 16px;
    }
    
    .send-btn:hover {
        background: #1f2937;
        transform: translateY(-50%) scale(1.05);
    }
    
    .send-btn:disabled {
        background: #e5e7eb;
        color: #9ca3af;
        cursor: not-allowed;
    }
    
    /* ============================================ */
    /* SUGGESTION CHIPS */
    /* ============================================ */
    
    .suggestions-container {
        max-width: 850px;
        margin: 0 auto 16px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    
    .suggestion-chip {
        background: white;
        border: 1px solid #e5e7eb;
        color: #374151;
        padding: 10px 16px;
        border-radius: 20px;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    
    .suggestion-chip:hover {
        background: #f9fafb;
        border-color: #d1d5db;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        transform: translateY(-1px);
    }
    
    /* ============================================ */
    /* WELCOME SCREEN */
    /* ============================================ */
    
    .welcome-screen {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
        text-align: center;
    }
    
    .welcome-icon {
        font-size: 64px;
        margin-bottom: 24px;
        opacity: 0.8;
    }
    
    .welcome-title {
        font-size: 32px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }
    
    .welcome-subtitle {
        font-size: 16px;
        color: #6b7280;
        margin-bottom: 32px;
        line-height: 1.6;
    }
    
    /* ============================================ */
    /* BATCH MODE */
    /* ============================================ */
    
    .batch-container {
        max-width: 800px;
        margin: 48px auto;
        padding: 0 24px;
    }
    
    .batch-header {
        text-align: center;
        margin-bottom: 32px;
    }
    
    .batch-title {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }
    
    .batch-subtitle {
        font-size: 15px;
        color: #6b7280;
    }
    
    .upload-area {
        background: white;
        border: 2px dashed #d1d5db;
        border-radius: 16px;
        padding: 48px 32px;
        text-align: center;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .upload-area:hover {
        border-color: #9ca3af;
        background: #f9fafb;
    }
    
    .upload-area-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.6;
    }
    
    .upload-area-title {
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 8px;
    }
    
    .upload-area-subtitle {
        font-size: 14px;
        color: #6b7280;
    }
    
    .file-list {
        margin-top: 24px;
    }
    
    .file-item {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s;
    }
    
    .file-item:hover {
        border-color: #d1d5db;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    
    .file-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .file-icon {
        font-size: 24px;
    }
    
    .file-details {
        text-align: left;
    }
    
    .file-name {
        font-size: 14px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 2px;
    }
    
    .file-size {
        font-size: 13px;
        color: #6b7280;
    }
    
    .file-remove {
        color: #ef4444;
        cursor: pointer;
        font-size: 20px;
        padding: 4px;
        border-radius: 4px;
        transition: all 0.2s;
    }
    
    .file-remove:hover {
        background: #fee2e2;
    }
    
    /* ============================================ */
    /* BUTTONS */
    /* ============================================ */
    
    .stButton > button {
        background: #111827;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.2s;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        width: 100%;
    }
    
    .stButton > button:hover {
        background: #1f2937;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Secondary Button */
    button[kind="secondary"] {
        background: white !important;
        color: #111827 !important;
        border: 2px solid #e5e7eb !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    
    button[kind="secondary"]:hover {
        background: #f9fafb !important;
        border-color: #d1d5db !important;
    }
    
    /* ============================================ */
    /* PREMIUM CALCULATOR CARD */
    /* ============================================ */
    
    .calculator-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    .calculator-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .calculator-icon {
        width: 48px;
        height: 48px;
        background: #111827;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
    }
    
    .calculator-title {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
    }
    
    .premium-result {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin-top: 20px;
    }
    
    .premium-label {
        font-size: 12px;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    .premium-amount {
        font-size: 36px;
        font-weight: 800;
        color: #111827;
        margin: 8px 0;
    }
    
    .premium-period {
        font-size: 14px;
        color: #6b7280;
    }
    
    .premium-details {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        margin-top: 16px;
        text-align: left;
        font-size: 14px;
        color: #374151;
        line-height: 1.7;
    }
    
    /* ============================================ */
    /* INPUT FIELDS */
    /* ============================================ */
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        font-size: 15px !important;
        color: #111827 !important;
        background: white !important;
        transition: all 0.2s !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #111827 !important;
        box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.1) !important;
    }
    
    .stTextInput label,
    .stSelectbox label,
    .stNumberInput label,
    .stTextArea label {
        color: #374151 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin-bottom: 6px !important;
    }
    
    /* ============================================ */
    /* FILE UPLOADER */
    /* ============================================ */
    
    [data-testid="stFileUploader"] {
        background: white;
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        padding: 32px;
        transition: all 0.3s;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #9ca3af;
        background: #f9fafb;
    }
    
    [data-testid="stFileUploader"] label {
        color: #111827 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stFileUploader"] small {
        color: #6b7280 !important;
    }
    
    /* ============================================ */
    /* PROGRESS BAR */
    /* ============================================ */
    
    .stProgress > div > div {
        background: #111827;
        height: 6px;
        border-radius: 3px;
    }
    
    /* ============================================ */
    /* SIDEBAR */
    /* ============================================ */
    
    [data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #e5e7eb;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #111827;
        font-weight: 700;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #374151;
    }
    
    /* ============================================ */
    /* ALERTS */
    /* ============================================ */
    
    .stAlert {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px;
        color: #374151;
    }
    
    /* ============================================ */
    /* METRICS */
    /* ============================================ */
    
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
    }
    
    [data-testid="stMetricValue"] {
        color: #111827;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        color: #6b7280;
        font-weight: 600;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* ============================================ */
    /* EXPANDER */
    /* ============================================ */
    
    .streamlit-expanderHeader {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        font-weight: 600;
        color: #111827;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f9fafb;
        border-color: #d1d5db;
    }
    
    /* ============================================ */
    /* TABS */
    /* ============================================ */
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f3f4f6;
        padding: 4px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        color: #6b7280;
    }
    
    .stTabs [aria-selected="true"] {
        background: white;
        color: #111827;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* ============================================ */
    /* SCROLLBAR */
    /* ============================================ */
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f3f4f6;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #9ca3af;
    }
    
    /* ============================================ */
    /* LOADING SPINNER */
    /* ============================================ */
    
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f4f6;
        border-top: 3px solid #111827;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* ============================================ */
    /* STATUS BADGE */
    /* ============================================ */
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 13px;
        font-weight: 600;
    }
    
    .status-success {
        background: #d1fae5;
        color: #065f46;
    }
    
    .status-warning {
        background: #fef3c7;
        color: #92400e;
    }
    
    .status-error {
        background: #fee2e2;
        color: #991b1b;
    }
    
    /* ============================================ */
    /* STATS GRID */
    /* ============================================ */
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin: 20px 0;
    }
    
    .stat-box {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    
    .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 4px;
    }
    
    .stat-label {
        font-size: 12px;
        color: #6b7280;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* ============================================ */
    /* RESPONSIVE */
    /* ============================================ */
    
    @media (max-width: 768px) {
        .top-bar {
            padding: 12px 16px;
        }
        
        .app-title {
            font-size: 16px;
        }
        
        .messages-area {
            padding: 16px;
        }
        
        .input-area {
            padding: 12px 16px 16px;
        }
        
        .stats-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================


def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'messages': [],
        'conversation_id': None,
        'document_chunks': [],
        'doc_metadata': None,
        'processed_text': None,
        'api_health': None,
        'chunk_strategy': 'semantic',
        'chunk_size': 1000,
        'chunk_overlap': 200,
        'validation_passed': False,
        'processing_time': 0,
        'premium_data': None,
        'batch_files': [],
        'mode': 'chat',  # 'chat' or 'batch'
        'show_calculator': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# ============================================================================
# EFFICIENT CHUNKING STRATEGIES
# ============================================================================


class DocumentChunker:
    """Advanced document chunking with multiple strategies"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (1 token ≈ 4 characters)"""
        return len(text) // 4
    
    @staticmethod
    def semantic_chunking(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Chunk]:
        """Semantic chunking: Respects sentence and paragraph boundaries"""
        chunks = []
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = ""
        current_start = 0
        chunk_id = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    id=f"chunk_{chunk_id}",
                    text=current_chunk.strip(),
                    page=0,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    token_count=DocumentChunker.estimate_tokens(current_chunk),
                    metadata={'type': 'semantic', 'paragraph_count': current_chunk.count('\n\n') + 1}
                ))
                
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
                current_start = current_start + len(current_chunk) - len(overlap_text)
                chunk_id += 1
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para
        
        if current_chunk:
            chunks.append(Chunk(
                id=f"chunk_{chunk_id}",
                text=current_chunk.strip(),
                page=0,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                token_count=DocumentChunker.estimate_tokens(current_chunk),
                metadata={'type': 'semantic', 'paragraph_count': current_chunk.count('\n\n') + 1}
            ))
        
        return chunks


# ============================================================================
# DOCUMENT VALIDATION
# ============================================================================


class DocumentValidator:
    """Validate document quality and insurance policy relevance"""
    
    @staticmethod
    def calculate_hash(content: bytes) -> str:
        """Calculate SHA-256 hash for document integrity"""
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def validate_insurance_content(text: str) -> Tuple[bool, float, List[str]]:
        """Validate if document is an insurance policy"""
        insurance_keywords = [
            'policy', 'premium', 'coverage', 'insured', 'insurer',
            'deductible', 'claim', 'benefit', 'exclusion', 'sum assured',
            'policyholder', 'indemnity', 'liability', 'endorsement',
            'rider', 'maturity', 'nominee', 'underwriting'
        ]
        
        text_lower = text.lower()
        found_keywords = [kw for kw in insurance_keywords if kw in text_lower]
        
        confidence = (len(found_keywords) / len(insurance_keywords)) * 100
        is_valid = confidence >= 30
        
        return is_valid, confidence, found_keywords


# ============================================================================
# ENHANCED TEXT EXTRACTION
# ============================================================================


def extract_text_from_pdf(file) -> Tuple[str, int]:
    """Enhanced PDF extraction"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages)
        
        text_parts = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            page_text = re.sub(r'\s+', ' ', page_text)
            text_parts.append(page_text)
        
        full_text = '\n\n'.join(text_parts)
        return full_text.strip(), page_count
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


def extract_text_from_word(file) -> str:
    """Extract text from Word document"""
    try:
        result = mammoth.extract_raw_text(file)
        return result.value
    except Exception as e:
        raise Exception(f"Word extraction failed: {str(e)}")


# ============================================================================
# API FUNCTIONS
# ============================================================================


@st.cache_data(ttl=300)
def check_api_health() -> Dict:
    """Check API health with caching"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "model_loaded": False, "error": str(e)}


def send_chat_query(query: str, chunks: List[Chunk] = None, conversation_id: str = None) -> Dict:
    """Send query with optimized chunking"""
    try:
        if conversation_id:
            payload = {
                "conversation_id": conversation_id,
                "query": query,
                "stream": False
            }
        else:
            policy_text = "\n\n".join([chunk.text for chunk in chunks[:5]]) if chunks else ""
            
            payload = {
                "policy_text": policy_text,
                "query": query,
                "stream": False,
                "temperature": 0.7
            }
        
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def calculate_premium_with_ai(chunks: List[Chunk], age: int, coverage: int, term: int, policy_type: str) -> str:
    """Use AI to calculate premium based on policy document"""
    try:
        policy_text = "\n\n".join([chunk.text for chunk in chunks[:5]]) if chunks else ""
        
        query = f"""Based on this insurance policy document, calculate the estimated premium for:
        - Age: {age} years
        - Coverage Amount: ₹{coverage:,}
        - Policy Term: {term} years
        - Policy Type: {policy_type}
        
        Please provide:
        1. Estimated annual premium in INR
        2. Brief calculation methodology
        3. Key factors
        
        Format: Start with "Premium: ₹X,XXX per year" followed by explanation."""
        
        payload = {
            "policy_text": policy_text,
            "query": query,
            "stream": False,
            "temperature": 0.3
        }
        
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get('response', 'Unable to calculate premium')
    except Exception as e:
        return f"Error: {str(e)}"


def process_document(file):
    """Process uploaded document"""
    start_time = time.time()
    
    try:
        file_content = file.read()
        file_hash = DocumentValidator.calculate_hash(file_content)
        
        file.seek(0)
        
        if file.type == "application/pdf":
            text, page_count = extract_text_from_pdf(file)
            file_type = "pdf"
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_word(file)
            page_count = 1
            file_type = "docx"
        else:
            file.seek(0)
            text = file_content.decode('utf-8')
            page_count = 1
            file_type = "txt"
        
        is_valid, confidence, keywords = DocumentValidator.validate_insurance_content(text)
        
        chunker = DocumentChunker()
        chunks = chunker.semantic_chunking(text, st.session_state.chunk_size, st.session_state.chunk_overlap)
        
        metadata = DocumentMetadata(
            filename=file.name,
            file_type=file_type,
            total_pages=page_count,
            total_chars=len(text),
            word_count=len(text.split()),
            hash=file_hash,
            upload_time=datetime.now(),
            is_valid=is_valid,
            validation_score=confidence
        )
        
        st.session_state.doc_metadata = metadata
        st.session_state.document_chunks = chunks
        st.session_state.processed_text = text
        st.session_state.validation_passed = is_valid
        st.session_state.processing_time = time.time() - start_time
        
        return True, f"✅ Processed **{file.name}** ({metadata.word_count:,} words, {len(chunks)} chunks)"
    
    except Exception as e:
        return False, f"❌ Error processing {file.name}: {str(e)}"


# ============================================================================
# UI COMPONENTS
# ============================================================================


def render_top_bar():
    """Render top navigation bar"""
    st.markdown("""
    <div class="top-bar">
        <div class="app-title-section">
            <div class="app-icon">📋</div>
            <div class="app-title">PolicyDocSummarizer</div>
        </div>
        <div class="mode-toggle" id="mode-toggle">
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mode toggle buttons
    col1, col2, col3 = st.columns([6, 1, 1])
    with col2:
        if st.button("💬 Chat", key="chat_mode", use_container_width=True, 
                    type="primary" if st.session_state.mode == 'chat' else "secondary"):
            st.session_state.mode = 'chat'
            st.rerun()
    with col3:
        if st.button("📦 Batch", key="batch_mode", use_container_width=True,
                    type="primary" if st.session_state.mode == 'batch' else "secondary"):
            st.session_state.mode = 'batch'
            st.rerun()


def render_chat_interface():
    """Render the main chat interface"""
    
    # Messages area
    if not st.session_state.messages and not st.session_state.doc_metadata:
        # Welcome screen
        st.markdown("""
        <div class="welcome-screen">
            <div class="welcome-icon">📋</div>
            <div class="welcome-title">PolicyDocSummarizer</div>
            <div class="welcome-subtitle">
                Upload a policy document or ask questions about insurance policies<br>
                I can analyze, summarize, and answer questions about your documents
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Display messages
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="message-wrapper">
                    <div class="message-avatar avatar-user">👤</div>
                    <div class="message-content">
                        <div class="message-text">{msg["content"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="message-wrapper">
                    <div class="message-avatar avatar-assistant">🤖</div>
                    <div class="message-content">
                        <div class="message-text">{msg["content"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Input area at bottom
    st.markdown('<div style="height: 120px;"></div>', unsafe_allow_html=True)  # Spacer
    
    # Fixed input container
    input_container = st.container()
    with input_container:
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        
        # Suggestions (only show if no messages)
        if not st.session_state.messages:
            st.markdown('<div class="suggestions-container">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            suggestions = [
                "What is sum insured?",
                "List all exclusions",
                "Calculate premium"
            ]
            for col, suggestion in zip([col1, col2, col3], suggestions):
                with col:
                    if st.button(suggestion, key=f"sug_{suggestion}", use_container_width=True):
                        handle_query(suggestion)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        # File upload and text input in same row
        col1, col2 = st.columns([8, 1])
        
        with col1:
            query = st.text_input(
                "Message",
                placeholder="Type a message or upload a document...",
                label_visibility="collapsed",
                key="chat_input"
            )
        
        with col2:
            uploaded_file = st.file_uploader(
                "📎",
                type=['pdf', 'docx', 'txt'],
                label_visibility="collapsed",
                key="file_upload"
            )
        
        if uploaded_file:
            with st.spinner("Processing document..."):
                success, message = process_document(uploaded_file)
                if success:
                    st.success(message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"{message}\n\nI've analyzed your document. You can now ask me questions about it!"
                    })
                    st.rerun()
                else:
                    st.error(message)
        
        if query:
            handle_query(query)
        
        st.markdown('</div></div>', unsafe_allow_html=True)


def render_batch_mode():
    """Render batch processing interface"""
    st.markdown("""
    <div class="batch-container">
        <div class="batch-header">
            <div class="batch-title">Batch Processing</div>
            <div class="batch-subtitle">Upload multiple policy documents for analysis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Upload multiple files",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        key="batch_upload"
    )
    
    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} files uploaded**")
        
        for idx, file in enumerate(uploaded_files):
            file_size = len(file.getvalue()) / 1024  # KB
            st.markdown(f"""
            <div class="file-item">
                <div class="file-info">
                    <div class="file-icon">📄</div>
                    <div class="file-details">
                        <div class="file-name">{file.name}</div>
                        <div class="file-size">{file_size:.1f} KB</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("🚀 Process All Files", use_container_width=True):
            progress_bar = st.progress(0)
            results = []
            
            for idx, file in enumerate(uploaded_files):
                progress_bar.progress((idx + 1) / len(uploaded_files))
                success, message = process_document(file)
                results.append(message)
            
            progress_bar.empty()
            
            for result in results:
                if "✅" in result:
                    st.success(result)
                else:
                    st.error(result)


def render_premium_calculator():
    """Render premium calculator in sidebar"""
    st.markdown("""
    <div class="calculator-card">
        <div class="calculator-header">
            <div class="calculator-icon">💰</div>
            <div class="calculator-title">Premium Calculator</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", 18, 80, 30)
        coverage = st.number_input("Coverage (₹)", 100000, 50000000, 1000000, 100000)
    with col2:
        term = st.number_input("Term (Years)", 5, 40, 20)
        policy_type = st.selectbox("Type", ["Term Life", "Health", "Vehicle"])
    
    if st.button("Calculate", use_container_width=True):
        if st.session_state.document_chunks:
            with st.spinner("Calculating..."):
                result = calculate_premium_with_ai(
                    st.session_state.document_chunks,
                    age, coverage, term, policy_type
                )
                st.session_state.premium_data = result
        else:
            st.warning("Please upload a policy document first")
    
    if st.session_state.premium_data:
        premium_match = re.search(r'₹[\d,]+', st.session_state.premium_data)
        premium_amount = premium_match.group(0) if premium_match else "₹ --"
        
        st.markdown(f"""
        <div class="premium-result">
            <div class="premium-label">Estimated Premium</div>
            <div class="premium-amount">{premium_amount}</div>
            <div class="premium-period">per year</div>
            <div class="premium-details">{st.session_state.premium_data}</div>
        </div>
        """, unsafe_allow_html=True)


def handle_query(query: str):
    """Handle user query"""
    if not query.strip():
        return
    
    st.session_state.messages.append({"role": "user", "content": query})
    
    with st.spinner("Thinking..."):
        result = send_chat_query(
            query=query,
            chunks=st.session_state.document_chunks,
            conversation_id=st.session_state.conversation_id
        )
        
        if 'error' not in result:
            response = result['response']
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.conversation_id = result.get('conversation_id')
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ Error: {result['error']}"
            })
    
    st.rerun()


# ============================================================================
# MAIN APPLICATION
# ============================================================================


def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        if st.button("🔄 Check API", use_container_width=True):
            st.session_state.api_health = check_api_health()
        
        if st.session_state.api_health:
            if st.session_state.api_health.get('model_loaded'):
                st.success("✅ API Ready")
            else:
                st.error("⚠️ API Error")
        
        st.markdown("---")
        
        # Premium Calculator
        if st.session_state.doc_metadata:
            with st.expander("💰 Premium Calculator"):
                render_premium_calculator()
        
        st.markdown("---")
        
        # Document Info
        if st.session_state.doc_metadata:
            st.markdown("### 📊 Document")
            meta = st.session_state.doc_metadata
            st.info(f"""
            **{meta.filename}**  
            {meta.word_count:,} words · {len(st.session_state.document_chunks)} chunks  
            Confidence: {meta.validation_score:.0f}%
            """)
        
        st.markdown("---")
        
        # Advanced Settings
        with st.expander("🔧 Advanced"):
            st.session_state.chunk_strategy = st.selectbox(
                "Chunking",
                ["semantic", "recursive", "fixed"]
            )
            st.session_state.chunk_size = st.slider("Size", 500, 2000, 1000, 100)
        
        st.markdown("---")
        
        if st.button("🔄 New Session", use_container_width=True):
            for key in ['messages', 'conversation_id', 'document_chunks', 'doc_metadata', 'premium_data']:
                st.session_state[key] = [] if key in ['messages', 'document_chunks'] else None
            st.rerun()
    
    # Main content
    render_top_bar()
    
    if st.session_state.mode == 'chat':
        render_chat_interface()
    else:
        render_batch_mode()


if __name__ == "__main__":
    main()
