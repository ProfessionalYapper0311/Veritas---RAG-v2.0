# Veritas RAG v2.0 &mdash; Environment Setup & Deployment Guide

This guide walks you through setting up and running **Veritas RAG v2.0** on your local machine or staging environment. Follow each step sequentially to configure prerequisites, environment variables, database schemas, and external service credentials.

---

## 1. Prerequisites

Before starting, ensure you have the following installed:

* **Python 3.13 or newer** ([python.org](https://www.python.org/downloads/))
* **uv** (recommended package installer & runner) or standard `pip`
* **Git** for version control

### Required Third-Party Cloud Accounts

Veritas relies on a lightweight, decoupled cloud architecture:

| Service | Purpose | Where to Obtain |
| :--- | :--- | :--- |
| **Google AI Studio** | LLM generation & vector embeddings | [aistudio.google.com](https://aistudio.google.com/) |
| **Pinecone** | Serverless vector database | [pinecone.io](https://www.pinecone.io/) |
| **PostgreSQL** | Relational data, ACLs, chat memory, audit log | [render.com](https://render.com/) or local PostgreSQL |
| **AWS S3** | Secure object storage for source documents | [aws.amazon.com](https://aws.amazon.com/) |
| **GlassFlow Rius** | Request tracing & observability (optional) | [glassflow.com](https://www.glassflow.com/) |

---

## 2. Project Installation

Clone the repository and install project dependencies into an isolated virtual environment:

```bash
# Clone repository
git clone <your-repo-url>
cd Veritas---RAG-v2.0

# Using uv (recommended)
uv venv
uv sync

# Or using standard python venv
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 3. Environment Configuration (`.env`)

Create your local configuration by copying the template:

```bash
cp .env.example .env
```

Open `.env` and populate each configuration section:

```ini
# ==============================================================================
# 1. AWS S3 STORAGE CONFIGURATION
# Used for presigned browser uploads and document file hosting.
# ==============================================================================
AWS_ACCESS_KEY_ID="your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
AWS_REGION="us-east-1"
S3_BUCKET="your-s3-bucket-name"

# ==============================================================================
# 2. GOOGLE GEMINI AI CONFIGURATION
# Powers conversational answers and semantic embeddings.
# ==============================================================================
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_EMBED_MODEL="models/gemini-embedding-001"
GEMINI_CHAT_MODEL="gemini-3.8-flash"
EMBED_DIMENSION=1024

# ==============================================================================
# 3. PINECONE VECTOR DATABASE
# Serverless vector store indexing document chunk embeddings.
# ==============================================================================
PINECONE_API_KEY="your_pinecone_api_key"
PINECONE_INDEX_NAME="veritas--rag-gemini-index"
PINECONE_CLOUD="aws"
PINECONE_REGION="us-east-1"
PINECONE_READY_TIMEOUT=180

# ==============================================================================
# 4. POSTGRESQL RELATIONAL DATABASE
# Stores document metadata, access controls, chat memory, and audit logs.
# ==============================================================================
DATABASE_URL="postgresql://user:password@hostname:5432/dbname?sslmode=require"

# ==============================================================================
# 5. OBSERVABILITY & TRACING (OPTIONAL)
# Distributed trace telemetry using GlassFlow Rius.
# ==============================================================================
RIUS_API_KEY="your_rius_api_key"
RIUS_SERVICE_NAME="veritas-rag"
RIUS_DISABLED=false
RIUS_CAPTURE_CONTENT=false
```

> [!NOTE]
> If you do not have a GlassFlow Rius API key, set `RIUS_DISABLED=true` in `.env`. The entire application will run normally without external telemetry.

---

## 4. Cloud Service Setup

### A. AWS S3 Bucket & CORS Configuration
To allow the browser interface to upload documents directly to your S3 bucket via presigned URLs without routing large binary files through the web server, configure CORS on your bucket:

1. Open **AWS S3 Console** &rarr; Select your bucket &rarr; **Permissions** &rarr; **Cross-origin resource sharing (CORS)**.
2. Paste the following JSON policy:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "POST", "GET", "HEAD"],
    "AllowedOrigins": ["http://localhost:8000", "http://127.0.0.1:8000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

### B. Pinecone Index Setup
The application includes automatic index provisioning in `app/vector.py`. When you first query or ingest documents, Veritas will automatically create the index with:
* **Name**: `veritas--rag-gemini-index`
* **Dimension**: `1024`
* **Metric**: `cosine`
* **Cloud / Region**: `aws` / `us-east-1`

Alternatively, you can manually create the index in the Pinecone web console with the exact specifications above.

---

## 5. Database Initialization

Execute the database initialization script to create all required PostgreSQL tables, indexes, and constraints defined in `infra/schema.sql`:

```bash
uv run python scripts/init_db.py
```

**Expected output:**
```text
Connecting to Render PostgreSQL (credentials hidden)...
SUCCESS: Database 'dbname' initialized; verified 5 tables.
You can safely rerun this script. Existing rows are preserved.
```

The script provisions:
* `documents`: Tracks uploaded files, versions, S3 keys, and processing status (`pending`, `processing`, `ready`, `failed`).
* `chat_messages`: Multi-tenant conversational memory for context-aware multi-turn dialogues.
* `approvals`: Human-in-the-loop (HITL) queue for sensitive actions (e.g., bulk document deletion).
* `audit_events`: Tamper-evident operational audit trail recording security and data events.
* `feedback`: User sentiment logs (thumbs-up / thumbs-down ratings with optional notes).

---

## 6. Generating Sample Documents (Optional)

To test the system immediately with realistic enterprise data, run the test document generator:

```bash
uv run python scripts/generate_test_docs.py
```

This creates structured sample PDF files in the `test_docs/` directory:
* `test_docs/Acme_Employee_Handbook_2026.pdf` (HR policies, remote work guidelines, PTO schedules)
* `test_docs/Veritas_Security_and_Compliance_Policy_2026.pdf` (Information security, MFA, data classification)

---

## 7. Starting the Application

Launch the FastAPI web server with automatic reload:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser:
* **Web Application UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
* **System Health Check**: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)

---

## 8. Verifying the System

Run the automated test suites to verify that all components are healthy and communicating properly:

```bash
# 1. Health checks, endpoints, and frontend integrity
uv run python tests/test_sanity.py

# 2. Gemini 1024-dim embedding & chat generation test
uv run python tests/test_api.py

# 3. Human-in-the-Loop approval & multi-tier deletion test
uv run python tests/test_deletion.py
```

---

## 9. Common Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **`404 Resource veritas--rag-gemini-index not found`** | Pinecone index does not exist yet. | Run `uv run python -c "from app.vector import index; index()"` to auto-provision the index. |
| **`ConnectionTimeout: connection timeout expired`** | Network latency or cold SSL handshake with cloud PostgreSQL (Render). | The connection timeout in `app/db.py` is configured to `25s`. Ensure your network allows outbound TLS to port `5432`. |
| **`Network error uploading directly to S3`** | Missing or incorrect S3 CORS configuration. | Ensure your bucket CORS allows origin `http://127.0.0.1:8000` and method `PUT`. |
| **`Access is denied (os error 5)` during `uv run` on Windows** | Trying to build local package wheels on non-NTFS or exFAT volumes. | Ensure `pyproject.toml` contains `[tool.uv] package = false`. |
| **Unresolved imports in IDE (VS Code / Pylance)** | Language server has not re-indexed newly generated files. | Press `Ctrl+Shift+P` &rarr; **Python: Restart Language Server**, or select the `.venv` virtual environment interpreter. |
