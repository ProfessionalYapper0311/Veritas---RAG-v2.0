# Veritas &mdash; Privacy-First Observability with GlassFlow Rius

Veritas integrates distributed tracing via **GlassFlow Rius** (`glassflow-rius`) to monitor pipeline execution times, node transitions, and operational latency across the RAG lifecycle without exposing user data.

---

## Privacy-First Architecture

Unlike traditional logging and tracing agents that ingest user questions and sensitive model responses into third-party clouds, the Veritas observability layer is strictly configured with **zero payload capture**:

* **No Input Capture (`capture_input=False`)**: User queries and confidential inputs are never captured or sent to external servers.
* **No Output Capture (`capture_output=False`)**: Generated answers and retrieved document passages remain strictly inside your application memory.
* **Metadata & Latency Only**: Only span names, execution timestamps, duration, and status codes are recorded for operational health and latency profiling.

---

## Configuration Variables

Control observability behavior via your `.env` configuration file:

```ini
# GlassFlow Rius API Key (obtained from your GlassFlow dashboard)
RIUS_API_KEY="your_rius_api_key"

# Service name displayed in trace catalogs
RIUS_SERVICE_NAME="veritas--rag"

# Kill switch: set to true to disable all telemetry
RIUS_DISABLED=false

# Keep set to false to enforce privacy-first telemetry
RIUS_CAPTURE_CONTENT=false
```

> [!TIP]
> If `RIUS_API_KEY` is omitted or `RIUS_DISABLED=true`, Veritas runs completely standalone with zero external network requests for tracing.

---

## Instrumented Pipeline Spans

The `@trace("name")` decorator in `app/observability.py` instruments critical workflow stages:

| Span Name | Module | What It Measures |
| :--- | :--- | :--- |
| **`guard`** | `app/graph.py` | Latency of input regex validation and injection detection. |
| **`retrieve`** | `app/graph.py` | Time required to embed the query and query Pinecone vector storage. |
| **`generate`** | `app/graph.py` | Google Gemini 3.8 Flash model invocation and answer generation duration. |
| **`validate`** | `app/graph.py` | Output safety scan checking for sensitive credentials. |
| **`chat`** | `app/graph.py` | End-to-end user request turn latency. |
| **`embed`** | `app/aws.py` | Google Gemini embedding generation latency. |
| **`answer`** | `app/aws.py` | Generation call latency. |
| **`upsert`** | `app/vector.py` | Vector upsert duration to Pinecone namespaces. |
| **`search`** | `app/vector.py` | Pinecone cosine similarity query duration. |
| **`process_s3_key`** | `worker/ingest.py`| Complete document ingestion lifecycle (S3 fetch, parse, chunk, embed, upsert). |
