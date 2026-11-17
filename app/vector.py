import logging
import time
from functools import lru_cache
from pinecone import Pinecone, ServerlessSpec
from pinecone.errors.exceptions import NotFoundError

from app.config import get_settings
from app.observability import trace

log = logging.getLogger(__name__)


def _is_index_ready(status) -> bool:
    """Helper to check index ready state across Pinecone dict/model variants."""
    if isinstance(status, dict):
        return bool(status.get('ready', False))
    return bool(getattr(status, 'ready', False))


@lru_cache
def index():
    """Return an initialized Pinecone index. Safe for repeated requests in one process."""
    s = get_settings()
    if not s.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing from .env")
    if not s.pinecone_index_name:
        raise RuntimeError("PINECONE_INDEX_NAME is missing from .env")
    pc = Pinecone(api_key=s.pinecone_api_key)
    name = s.pinecone_index_name

    # Describe rather than list: avoids listing every index and works for existing indexes.
    try:
        info = pc.describe_index(name)
    except Exception as exc:
        # Only create on an actual 404; never hide auth/network failures.
        is_404 = (
            isinstance(exc, NotFoundError)
            or getattr(exc, 'status_code', None) == 404
            or getattr(exc, 'status', None) == 404
        )
        if not is_404:
            raise
        log.info('Creating Pinecone index %s (dimension=%d, metric=cosine)', name, s.embed_dim)
        try:
            pc.create_index(
                name=name,
                dimension=s.embed_dim,
                metric='cosine',
                spec=ServerlessSpec(cloud=s.pinecone_cloud, region=s.pinecone_region)
            )
        except Exception as create_exc:
            # Another process may have created the index concurrently.
            is_409 = (
                getattr(create_exc, 'status_code', None) == 409
                or getattr(create_exc, 'status', None) == 409
                or create_exc.__class__.__name__ == 'ConflictError'
            )
            if not is_409:
                raise
        info = pc.describe_index(name)

    if info.dimension and int(info.dimension) != s.embed_dim:
        raise ValueError(
            f'Pinecone index {name} dimension={info.dimension}, expected {s.embed_dim}. '
            'Use a different index name or matching EMBED_DIM.'
        )
    if str(info.metric).lower() != 'cosine':
        raise ValueError(f'Pinecone index {name} must use cosine metric, got {info.metric}')

    deadline = time.monotonic() + s.pinecone_ready_timeout
    while not _is_index_ready(pc.describe_index(name).status):
        if time.monotonic() >= deadline:
            raise TimeoutError(f'Pinecone index {name} was not ready within {s.pinecone_ready_timeout}s')
        time.sleep(3)

    log.info('Pinecone index %s ready', name)
    return pc.Index(name)


def namespace(tenant: str) -> str:
    """Namespace isolation per tenant."""
    return 'tenant-' + tenant


@trace("upsert")
def upsert(tenant: str, records: list):
    """Upsert vector records into tenant namespace."""
    return index().upsert(vectors=records, namespace=namespace(tenant))


@trace("search")
def search(tenant: str, vector: list[float], groups: list | set, owner: str, limit: int = 5) -> list[dict]:
    """Similarity search filtered by tenant ACL."""
    groups_list = list(groups) if groups else []
    if groups_list:
        acl = {
            '$or': [
                {'allowed_groups': {'$in': groups_list}},
                {'owner_sub': {'$eq': owner}}
            ]
        }
    else:
        acl = {'owner_sub': {'$eq': owner}}

    result = index().query(
        vector=vector,
        top_k=limit,
        include_metadata=True,
        namespace=namespace(tenant),
        filter=acl
    )
    return [
        {'id': m.id, 'score': m.score, 'metadata': m.metadata or {}}
        for m in (result.matches or [])
    ]


def delete_all_vectors(tenant: str):
    """Purge all vectors in the tenant's Pinecone namespace."""
    try:
        index().delete(delete_all=True, namespace=namespace(tenant))
        log.info("Deleted all vectors in namespace %s", namespace(tenant))
    except Exception as exc:
        if isinstance(exc, NotFoundError) or getattr(exc, 'status_code', None) == 404 or '404' in str(exc) or 'not found' in str(exc).lower():
            log.info("Namespace %s already empty or not found in Pinecone", namespace(tenant))
            return
        log.error("Failed to delete all vectors in namespace %s: %s", namespace(tenant), exc)
        raise


def delete_document_vectors(tenant: str, doc_id: str):
    """Delete all vector chunks for a specific document ID in the tenant namespace."""
    try:
        index().delete(filter={'document_id': str(doc_id)}, namespace=namespace(tenant))
        log.info("Deleted vector chunks for document %s in namespace %s", doc_id, namespace(tenant))
    except Exception as exc:
        if isinstance(exc, NotFoundError) or getattr(exc, 'status_code', None) == 404 or '404' in str(exc) or 'not found' in str(exc).lower():
            log.info("No vectors found for document %s in namespace %s", doc_id, namespace(tenant))
            return
        log.error("Failed to delete vectors for document %s: %s", doc_id, exc)
        raise


def delete_document(tenant: str, ids: str | list[str]):
    """Delete document vector IDs from tenant namespace safely."""
    if not ids:
        return
    id_list = [ids] if isinstance(ids, str) else list(ids)
    try:
        index().delete(ids=id_list, namespace=namespace(tenant))
    except Exception as exc:
        if isinstance(exc, NotFoundError) or getattr(exc, 'status_code', None) == 404 or '404' in str(exc) or 'not found' in str(exc).lower():
            return
        raise
