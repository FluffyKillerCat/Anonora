# Anonora - Document Intelligence Platform

**Anonora** is a secure, AI-powered platform for document upload, redaction, and semantic search—designed with privacy and automation at its core.

---

## 🚀 Version History

- **v0.0.1** – Document upload, redaction (via OCR + Presidio), and embedding generation
- **v0.0.2** – RAG-based search (implementation in progress — `ToDo`)

---

## Capabilities (Summary)

- Extract text from scanned PDFs using OCR  
- Redact PII automatically with Microsoft Presidio  
- Generate vector embeddings for semantic search  
- Support for question answering using RAG (coming soon)  
- Automatically tag and categorize uploaded documents  
- Secure login and permission-based document access  

---

## Tech Stack

- **Frameworks**: FastAPI, Celery, Supabase (PostgreSQL), Redis  
- **AI/ML**: Sentence Transformers, Microsoft Presidio, pgvector  
- **Security**: JWT Authentication, Row-Level Security, Secure File Upload  

---



