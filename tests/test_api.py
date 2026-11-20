import os
import math
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key, "GEMINI_API_KEY must be set in your .env file"
    return genai.Client(api_key=api_key)


def test_gemini_embedding():
    """Verify models/gemini-embedding-001 produces 1024-dim L2-normalizable vectors."""
    client = get_client()
    embed_model = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")

    config = types.EmbedContentConfig(
        output_dimensionality=1024,
        task_type="RETRIEVAL_QUERY",
    )

    response = client.models.embed_content(
        model=embed_model,
        contents="Veritas RAG Google Gemini embedding test",
        config=config,
    )

    assert response.embeddings, "No embeddings returned from Gemini API"
    raw_vector = response.embeddings[0].values

    print(f"\n[Embedding Test]")
    print(f"Model: {embed_model}")
    print(f"Dimensions: {len(raw_vector)}")
    assert len(raw_vector) == 1024, f"Expected 1024 dimensions, got {len(raw_vector)}"

    # Verify L2 normalization (required for Pinecone cosine metric)
    norm = math.sqrt(sum(x * x for x in raw_vector))
    assert norm > 0, "Vector norm must be positive"
    normalized_vector = [x / norm for x in raw_vector]
    unit_norm = math.sqrt(sum(x * x for x in normalized_vector))

    print(f"Norm before normalization: {norm:.4f}")
    print(f"Norm after normalization:  {unit_norm:.4f}")
    assert abs(unit_norm - 1.0) < 1e-5, "Normalized vector must have unit length"
    print("Embedding test passed successfully!")


def test_gemini_llm():
    """Verify Gemini generation works with tool/JSON support readiness."""
    client = get_client()
    chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")

    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=150,
    )

    response = client.models.generate_content(
        model=chat_model,
        contents="Explain what RAG is in one clear sentence.",
        config=config,
    )

    assert response.text, "Gemini returned empty response text"

    print(f"\n[Chat LLM Test]")
    print(f"Model: {chat_model}")
    print(f"Response: {response.text.strip()}")
    print("Chat LLM test passed successfully!")


if __name__ == "__main__":
    print("Running Gemini API verification tests...")
    test_gemini_embedding()
    test_gemini_llm()
    print("\nAll Gemini tests passed successfully!")
