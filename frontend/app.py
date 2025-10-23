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
from collections import deque
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
    page_title="Insurance AI Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STUNNING TEAL & CORAL UI/UX STYLING
# ============================================================================

st.markdown("""
<style>
    /* Global Styles - Cream Background */
    .stApp {
        background: linear-gradient(135deg, #fef9f3 0%, #f7e8d3 50%, #fff8f0 100%);
    }
    
    /* Remove default padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Main Header - Deep Teal to Turquoise Gradient */
    .hero-header {
        background: linear-gradient(135deg, #0d7377 0%, #14b8a6 50%, #00cfc8 100%);
        padding: 3rem 2rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(13, 115, 119, 0.3);
        backdrop-filter: blur(10px);
        border: 2px solid rgba(255, 255, 255, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .hero-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
        animation: pulse 8s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 0.8; }
    }
    
    .hero-title {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
        text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        color: rgba(255,255,255,0.95);
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }
    
    /* Glass Card System - White with Teal Accents */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid rgba(20, 184, 166, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(13, 115, 119, 0.1);
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        box-shadow: 0 12px 48px rgba(20, 184, 166, 0.2);
        transform: translateY(-4px);
        border-color: rgba(20, 184, 166, 0.4);
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    /* Stat Cards - Coral Gradient */
    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #fff5f0 100%);
        border: 2px solid rgba(251, 113, 133, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #fb7185 0%, #f97316 100%);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .stat-card:hover::before {
        transform: scaleX(1);
    }
    
    .stat-card:hover {
        border-color: #fb7185;
        box-shadow: 0 8px 24px rgba(251, 113, 133, 0.3);
        transform: translateY(-4px);
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0d7377 0%, #14b8a6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }
    
    .stat-label {
        color: #6b7280;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.5rem;
    }
    
    /* Message Bubbles */
    .message-container {
        display: flex;
        margin: 1rem 0;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* User Message - Teal Gradient */
    .message-user {
        background: linear-gradient(135deg, #0d7377 0%, #14b8a6 100%);
        color: white;
        padding: 1.25rem 1.5rem;
        border-radius: 20px 20px 4px 20px;
        margin-left: auto;
        max-width: 70%;
        box-shadow: 0 4px 16px rgba(13, 115, 119, 0.3);
        font-weight: 500;
    }
    
    /* Assistant Message - White with Teal Border */
    .message-assistant {
        background: white;
        color: #1f2937;
        padding: 1.25rem 1.5rem;
        border-radius: 20px 20px 20px 4px;
        margin-right: auto;
        max-width: 70%;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border: 2px solid rgba(20, 184, 166, 0.3);
    }
    
    /* Primary Buttons - Teal to Coral Gradient */
    .stButton>button {
        background: linear-gradient(135deg, #0d7377 0%, #14b8a6 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px rgba(13, 115, 119, 0.3);
        width: 100%;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #fb7185 0%, #f97316 100%);
        box-shadow: 0 8px 32px rgba(251, 113, 133, 0.4);
        transform: translateY(-2px);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* Progress Bar - Teal */
    .stProgress > div > div {
        background: linear-gradient(90deg, #0d7377 0%, #00cfc8 100%);
    }
    
    /* Input Fields - Teal Focus */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border: 2px solid rgba(20, 184, 166, 0.3);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
        background: white;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #14b8a6;
        box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
    }
    
    /* File Uploader */
    .uploadedFile {
        background: white;
        border: 2px dashed rgba(20, 184, 166, 0.4);
        border-radius: 12px;
        padding: 1.5rem;
    }
    
    /* Validation Badges */
    .validation-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
        margin: 0.5rem;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #fb7185 0%, #f97316 100%);
        color: white;
    }
    
    .badge-error {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
    }
    
    /* Info Boxes */
    .info-box {
        background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
        border-left: 4px solid #0d7377;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 4px solid #10b981;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #ffe4e6 0%, #fecdd3 100%);
        border-left: 4px solid #fb7185;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left: 4px solid #ef4444;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Sidebar Styling - Cream with Teal Accent */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fef9f3 0%, #fff5f0 100%);
        border-right: 2px solid rgba(20, 184, 166, 0.2);
    }
    
    /* Loading Animation */
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid rgba(20, 184, 166, 0.2);
        border-top: 4px solid #0d7377;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Chunk Visualizer */
    .chunk-preview {
        background: #f0fdfa;
        border-left: 3px solid #14b8a6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        font-size: 0.875rem;
        font-family: 'Courier New', monospace;
    }
    
    /* Metric Cards */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .metric-card {
        flex: 1;
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid rgba(20, 184, 166, 0.2);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0d7377;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #6b7280;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    /* Tabs Enhancement - Teal Accent */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.7);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0d7377 0%, #14b8a6 100%);
        color: white;
    }
    
    /* Select Box - Teal */
    .stSelectbox > div > div {
        border: 2px solid rgba(20, 184, 166, 0.3);
        border-radius: 12px;
    }
    
    /* Slider - Teal */
    .stSlider > div > div > div {
        background: #14b8a6;
    }
    
    /* Expander - Teal Accent */
    .streamlit-expanderHeader {
        background: rgba(20, 184, 166, 0.1);
        border-radius: 8px;
        border: 1px solid rgba(20, 184, 166, 0.2);
    }
    
    /* Radio Buttons - Coral Accent */
    .stRadio > div {
        background: rgba(251, 113, 133, 0.05);
        padding: 1rem;
        border-radius: 12px;
    }
    
    /* Success Messages */
    .element-container:has(> .stAlert) {
        animation: slideIn 0.3s ease-out;
    }
    
    /* Metrics Enhancement */
    [data-testid="stMetricValue"] {
        color: #0d7377;
        font-weight: 700;
    }
    
    /* Coral Accent Elements */
    .coral-accent {
        color: #fb7185;
        font-weight: 600;
    }
    
    .teal-accent {
        color: #0d7377;
        font-weight: 600;
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
        'processing_time': 0
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
        """
        Semantic chunking: Respects sentence and paragraph boundaries
        Best for insurance documents with structured content
        """
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
    
    @staticmethod
    def recursive_chunking(text: str, max_chunk_size: int = 1000) -> List[Chunk]:
        """Recursive chunking: Hierarchical splitting with priority separators"""
        separators = ['\n\n\n', '\n\n', '\n', '. ', ' ']
        
        def split_text(text: str, separators: List[str]) -> List[str]:
            if not separators:
                return [text]
            
            separator = separators[0]
            chunks = []
            
            for segment in text.split(separator):
                if len(segment) <= max_chunk_size:
                    chunks.append(segment)
                else:
                    chunks.extend(split_text(segment, separators[1:]))
            
            return chunks
        
        text_chunks = split_text(text, separators)
        
        return [
            Chunk(
                id=f"chunk_{i}",
                text=chunk.strip(),
                page=0,
                start_char=0,
                end_char=len(chunk),
                token_count=DocumentChunker.estimate_tokens(chunk),
                metadata={'type': 'recursive'}
            )
            for i, chunk in enumerate(text_chunks) if chunk.strip()
        ]
    
    @staticmethod
    def fixed_size_chunking(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Chunk]:
        """Fixed-size chunking with overlap"""
        words = text.split()
        chunks = []
        chunk_id = 0
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(Chunk(
                id=f"chunk_{chunk_id}",
                text=chunk_text,
                page=0,
                start_char=0,
                end_char=len(chunk_text),
                token_count=DocumentChunker.estimate_tokens(chunk_text),
                metadata={'type': 'fixed', 'word_count': len(chunk_words)}
            ))
            
            i += chunk_size - overlap
            chunk_id += 1
        
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
        """
        Validate if document is an insurance policy
        Returns: (is_valid, confidence_score, found_keywords)
        """
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
    
    @staticmethod
    def validate_document_structure(text: str) -> Dict:
        """Validate document has proper structure"""
        validations = {
            'has_headers': bool(re.search(r'^[A-Z\s]{10,}$', text, re.MULTILINE)),
            'has_sections': bool(re.search(r'(?:section|article|clause)\s*\d+', text, re.IGNORECASE)),
            'has_numbers': bool(re.search(r'\d+', text)),
            'has_dates': bool(re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', text)),
            'min_length': len(text) >= 500,
            'has_proper_sentences': text.count('.') >= 5
        }
        
        score = sum(validations.values()) / len(validations) * 100
        
        return {
            'validations': validations,
            'structure_score': score,
            'is_well_structured': score >= 60
        }

# ============================================================================
# ENHANCED TEXT EXTRACTION
# ============================================================================

def extract_text_from_pdf(file) -> Tuple[str, int]:
    """Enhanced PDF extraction - Returns: (text, page_count)"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages)
        
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
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

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_hero():
    """Render hero header"""
    st.markdown("""
    <div class="hero-header">
        <h1 class="hero-title">🛡️ Insurance AI Analyzer</h1>
        <p class="hero-subtitle">Advanced Policy Analysis with Intelligent Document Processing</p>
    </div>
    """, unsafe_allow_html=True)

def render_validation_badge(is_valid: bool, score: float):
    """Render validation status badge"""
    if score >= 70:
        badge_class = "badge-success"
        icon = "✅"
        text = "High Confidence"
    elif score >= 40:
        badge_class = "badge-warning"
        icon = "⚠️"
        text = "Medium Confidence"
    else:
        badge_class = "badge-error"
        icon = "❌"
        text = "Low Confidence"
    
    st.markdown(f"""
    <span class="validation-badge {badge_class}">
        {icon} {text} ({score:.1f}%)
    </span>
    """, unsafe_allow_html=True)

def render_stats_grid(metadata: DocumentMetadata, chunks: List[Chunk]):
    """Render statistics in grid layout"""
    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    stats = [
        ("📄", metadata.total_pages, "Pages"),
        ("💬", metadata.word_count, "Words"),
        ("🧩", len(chunks), "Chunks"),
        ("⚡", sum(c.token_count for c in chunks), "Tokens")
    ]
    
    for col, (icon, value, label) in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                <div class="stat-number">{value:,}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    render_hero()
    
    # Sidebar Configuration
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        if st.button("🔄 Check API Status", use_container_width=True):
            with st.spinner("Checking API..."):
                st.session_state.api_health = check_api_health()
        
        if st.session_state.api_health:
            health = st.session_state.api_health
            if health.get('model_loaded'):
                st.markdown('<div class="success-box"><strong>✅ API Connected</strong><br>Model is ready</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-box"><strong>⚠️ API Error</strong><br>Model not loaded</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("#### 🧩 Chunking Strategy")
        chunk_strategy = st.selectbox(
            "Select method",
            ["Semantic (Recommended)", "Recursive", "Fixed Size"],
            help="Semantic chunking preserves context and is best for insurance documents"
        )
        
        st.session_state.chunk_strategy = chunk_strategy.split()[0].lower()
        
        with st.expander("🔧 Advanced Settings"):
            st.session_state.chunk_size = st.slider(
                "Chunk Size (tokens)",
                min_value=500,
                max_value=2000,
                value=1000,
                step=100
            )
            
            st.session_state.chunk_overlap = st.slider(
                "Overlap (tokens)",
                min_value=0,
                max_value=500,
                value=200,
                step=50
            )
        
        st.markdown("---")
        
        if st.button("🔄 New Analysis", use_container_width=True, type="primary"):
            for key in ['messages', 'conversation_id', 'document_chunks', 'doc_metadata', 'processed_text', 'validation_passed']:
                st.session_state[key] = [] if key == 'messages' or key == 'document_chunks' else None if key != 'validation_passed' else False
            st.rerun()
        
        if st.session_state.doc_metadata:
            st.markdown("---")
            st.markdown("### 📊 Document Info")
            meta = st.session_state.doc_metadata
            st.info(f"""
            **File:** {meta.filename}  
            **Type:** {meta.file_type.upper()}  
            **Validation:** {meta.validation_score:.1f}%  
            **Processing:** {st.session_state.processing_time:.2f}s
            """)
    
    # Main Content Area
    if not st.session_state.doc_metadata:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📁 Upload Insurance Policy Document")
        st.markdown("Supported formats: PDF, Word (.docx), Text (.txt)")
        
        tab1, tab2 = st.tabs(["📤 Upload File", "✍️ Paste Text"])
        
        with tab1:
            uploaded_file = st.file_uploader(
                "Choose your policy document",
                type=['pdf', 'docx', 'txt'],
                help="Upload your insurance policy document for AI-powered analysis",
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                start_time = time.time()
                progress_bar = st.progress(0, text="Initializing...")
                
                try:
                    progress_bar.progress(10, text="📖 Reading document...")
                    file_content = uploaded_file.read()
                    file_hash = DocumentValidator.calculate_hash(file_content)
                    
                    progress_bar.progress(25, text="🔍 Extracting text...")
                    uploaded_file.seek(0)
                    
                    if uploaded_file.type == "application/pdf":
                        text, page_count = extract_text_from_pdf(uploaded_file)
                        file_type = "pdf"
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        text = extract_text_from_word(uploaded_file)
                        page_count = 1
                        file_type = "docx"
                    else:
                        uploaded_file.seek(0)
                        text = file_content.decode('utf-8')
                        page_count = 1
                        file_type = "txt"
                    
                    progress_bar.progress(50, text="✅ Validating content...")
                    is_valid, confidence, keywords = DocumentValidator.validate_insurance_content(text)
                    structure_check = DocumentValidator.validate_document_structure(text)
                    
                    progress_bar.progress(70, text="🧩 Creating intelligent chunks...")
                    
                    chunker = DocumentChunker()
                    if st.session_state.chunk_strategy == 'semantic':
                        chunks = chunker.semantic_chunking(text, st.session_state.chunk_size, st.session_state.chunk_overlap)
                    elif st.session_state.chunk_strategy == 'recursive':
                        chunks = chunker.recursive_chunking(text, st.session_state.chunk_size)
                    else:
                        chunks = chunker.fixed_size_chunking(text, st.session_state.chunk_size, st.session_state.chunk_overlap)
                    
                    progress_bar.progress(90, text="📊 Finalizing analysis...")
                    
                    word_count = len(text.split())
                    
                    metadata = DocumentMetadata(
                        filename=uploaded_file.name,
                        file_type=file_type,
                        total_pages=page_count,
                        total_chars=len(text),
                        word_count=word_count,
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
                    
                    progress_bar.progress(100, text="✅ Complete!")
                    time.sleep(0.5)
                    progress_bar.empty()
                    
                    st.success(f"✅ Document processed successfully in {st.session_state.processing_time:.2f}s!")
                    st.rerun()
                
                except Exception as e:
                    progress_bar.empty()
                    st.error(f"❌ Error processing document: {str(e)}")
        
        with tab2:
            policy_text = st.text_area(
                "Paste your insurance policy text",
                height=300,
                placeholder="Paste the complete policy document text here..."
            )
            
            if policy_text and st.button("🚀 Process Text", use_container_width=True):
                start_time = time.time()
                
                with st.spinner("Processing..."):
                    try:
                        is_valid, confidence, keywords = DocumentValidator.validate_insurance_content(policy_text)
                        
                        chunker = DocumentChunker()
                        if st.session_state.chunk_strategy == 'semantic':
                            chunks = chunker.semantic_chunking(policy_text, st.session_state.chunk_size, st.session_state.chunk_overlap)
                        elif st.session_state.chunk_strategy == 'recursive':
                            chunks = chunker.recursive_chunking(policy_text, st.session_state.chunk_size)
                        else:
                            chunks = chunker.fixed_size_chunking(policy_text, st.session_state.chunk_size, st.session_state.chunk_overlap)
                        
                        metadata = DocumentMetadata(
                            filename="pasted_text.txt",
                            file_type="txt",
                            total_pages=1,
                            total_chars=len(policy_text),
                            word_count=len(policy_text.split()),
                            hash=DocumentValidator.calculate_hash(policy_text.encode()),
                            upload_time=datetime.now(),
                            is_valid=is_valid,
                            validation_score=confidence
                        )
                        
                        st.session_state.doc_metadata = metadata
                        st.session_state.document_chunks = chunks
                        st.session_state.processed_text = policy_text
                        st.session_state.validation_passed = is_valid
                        st.session_state.processing_time = time.time() - start_time
                        
                        st.success("✅ Text processed successfully!")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        metadata = st.session_state.doc_metadata
        chunks = st.session_state.document_chunks
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Document Validation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            render_validation_badge(metadata.is_valid, metadata.validation_score)
            
            if metadata.validation_score >= 70:
                st.markdown('<div class="success-box">✅ <strong>Document validated as insurance policy</strong><br>High confidence in content relevance</div>', unsafe_allow_html=True)
            elif metadata.validation_score >= 40:
                st.markdown('<div class="warning-box">⚠️ <strong>Possible insurance policy</strong><br>Moderate confidence - some keywords missing</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-box">❌ <strong>May not be an insurance policy</strong><br>Low confidence - missing key policy elements</div>', unsafe_allow_html=True)
        
        with col2:
            st.metric("Confidence Score", f"{metadata.validation_score:.1f}%", 
                     delta="Valid" if metadata.is_valid else "Invalid")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Document Statistics")
        render_stats_grid(metadata, chunks)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 💬 Ask Questions About Your Policy")
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            query = st.text_input(
                "Your question",
                placeholder="What are the coverage benefits?",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.button("🚀 Ask", use_container_width=True, type="primary")
        
        st.markdown("**💡 Suggested Questions:**")
        suggestion_cols = st.columns(3)
        suggestions = [
            "What is the sum insured?",
            "What are the exclusions?",
            "What is the premium amount?"
        ]
        
        for col, suggestion in zip(suggestion_cols, suggestions):
            with col:
                if st.button(suggestion, use_container_width=True, key=f"suggest_{suggestion}"):
                    query = suggestion
                    send_button = True
        
        if send_button and query:
            with st.spinner("🤔 Analyzing policy..."):
                result = send_chat_query(
                    query=query,
                    chunks=st.session_state.document_chunks,
                    conversation_id=st.session_state.conversation_id
                )
                
                if 'error' not in result:
                    st.session_state.messages.append({"role": "user", "content": query})
                    st.session_state.messages.append({"role": "assistant", "content": result['response']})
                    st.session_state.conversation_id = result.get('conversation_id')
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result['error']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.messages:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("### 📝 Conversation History")
            
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    st.markdown(f'<div class="message-container"><div class="message-user"><strong>You</strong><br>{msg["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="message-container"><div class="message-assistant"><strong>AI Assistant</strong><br>{msg["content"]}</div></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
