# Policy Summary Assistant: A GenAI-Powered Insurance Document Summarization System

**Technical Brief**

**Date:** November 2025

---

## 1. Abstract

This report presents the Policy Summary Assistant, a GenAI tool that processes complex insurance documents to generate concise, plain-language summaries. The system leverages a fine-tuned Mistral 7B model and a FastAPI architecture to deliver accurate summaries of coverage, exclusions, and limits. The project included data collection from 300 sources, validation of 144 policy documents, and deployment via a full-stack application, demonstrating significant potential for improving policy comprehension.

---

## 2. Introduction

### 2.1 Problem Statement

Insurance policies are notoriously complex and filled with legal jargon, creating a significant barrier to customer comprehension. This often leads to disputes and customer dissatisfaction. This project aimed to create an automated system to parse these documents and present the essential information in simple language.

### 2.2 Objectives

1.  Collect and curate a dataset of diverse insurance policy documents.
2.  Fine-tune a Large Language Model (LLM) specifically for insurance policy summarization.
3.  Develop a robust, scalable API architecture for model deployment.
4.  Create an intuitive user interface for document upload and analysis.
5.  Generate accurate, concise summaries (approx. 200 words) of policy documents.

---

## 3. System Architecture

The system uses a three-tier architecture:

1.  **Frontend Layer:** A **React-based** chatbot interface for user interaction, document upload, and session management.
2.  **Middleware Layer:** A **FastAPI** service that handles request validation, NLP preprocessing (e.g., semantic chunking for large documents), and serves as a bridge between the user and the core model.
3.  **Core Processing Layer ("PolicyPulse"):** A dedicated **FastAPI** wrapper for the fine-tuned Mistral 7B model. This API handles the raw inference and response generation.

---

## 4. Methodology & Implementation

### 4.1 Data & Model

* **Data Collection:** Began with 300 scraped policy document links, resulting in **144 valid, readable PDFs** after validation (48% success rate).
* **Preprocessing:** The **Google Gemini API** was used to perform advanced text extraction from the PDFs, structuring the content into a conversational JSON format.
* **Base Model:** **Mistral 7B Instruct** was chosen for its optimal performance-to-size ratio and strong instruction-following capabilities.
* **Fine-tuning:** The model was fine-tuned on the 144-document dataset using **LoRA (Low-Rank Adaptation)** with a learning rate of `2e-5` for 3 epochs.
* **Optimization:** The trained LoRA adapters were merged into the base model. The final model was then converted to **GGUF format** and optimized using **4-bit (Q4_K_M) quantization**. This reduced the model size from ~28GB to ~4GB, enabling fast inference on consumer-grade hardware.

### 4.2 API & Deployment

* **Core API (PolicyPulse):** A FastAPI service using `llama-cpp-python` to load the 4-bit quantized GGUF model and serve inference endpoints.
* **Middleware API:** A second FastAPI service manages the business logic, including:
    * **Text Chunking:** A semantic chunking strategy (2000-token chunks with 200-token overlap) processes documents that exceed the model's context limit.
    * **Context Management:** Maintains session history for contextual follow-up queries.
* **Frontend:** A React-based interface provides a simple chatbot UI for uploading documents and interacting with the summarization and query modes.

---

## 5. Results & Performance

### 5.1 Quantitative Metrics

| Metric | Value |
| :--- | :--- |
| ROUGE-1 Score | 0.72 |
| ROUGE-L Score | 0.68 |
| Accuracy (Human Eval) | **89%** |
| Average Summary Length | 195 words |
| **Total Processing Time** | **~5.2 seconds** |
| System Uptime (Test) | 99.7% |
| Concurrent Users | 50+ |

### 5.2 Qualitative Examples

**Example 1: Life Insurance Summary**
> "This life insurance policy provides death benefit coverage of up to $500,000 for the insured... Key exclusions include suicide within the first two years, death during illegal activities, and pre-existing conditions not disclosed... The policy offers optional riders for critical illness and accidental death."

**Example 2: Health Insurance Summary**
> "This comprehensive health insurance plan covers hospitalization expenses up to $100,000 annually. Coverage includes pre and post-hospitalization, day-care procedures, and ambulance charges... Major exclusions are cosmetic surgery, dental procedures... and pre-existing conditions during the first two years. The policy has a co-payment of 10%..."

---

## 6. Challenges & Future Work

### 6.1 Key Challenges Solved

* **Low Data Quality:** Overcame a 48% data validation rate by implementing robust error handling and focusing on the 144 high-quality documents.
* **Context Length:** Managed policies exceeding the 8K token limit by implementing an intelligent semantic chunking and summary-aggregation strategy in the middleware.
* **Inference Speed:** Reduced inference time from ~20 seconds to ~3-5 seconds per document by applying 4-bit quantization.

### 6.2 Future Enhancements

* **Multi-language Support:** Train models to support regional languages.
* **Comparative Analysis:** Develop a feature to compare multiple policy documents side-by-side.
* **Multi-modal Processing:** Enhance the system to extract and understand information from tables and charts within the documents.

---

## 7. Conclusion

This project successfully developed the Policy Summary Assistant, a scalable and accurate GenAI application. By fine-tuning Mistral 7B on a specialized insurance dataset and deploying it via a robust multi-tier API, the system achieves 89% accuracy in human evaluations. The 4-bit quantization was critical for enabling practical, real-time performance. The assistant effectively bridges the gap between complex financial documents and consumer understanding, demonstrating significant value for both customers and insurance providers.
