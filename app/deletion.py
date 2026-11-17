"""
Document Deletion & Purge Workflow for Project Veritas.

Handles permanent, synchronized cleanup across all storage tiers:
1. Pinecone Vector Database: Deletes tenant vectors (by namespace or metadata filter)
2. AWS S3 Bucket: Deletes document objects and any incoming/staged files under tenant prefix
3. PostgreSQL Database: Deletes document catalog records and logs structured audit events
"""

import logging
import uuid
from app.aws import client
from app.config import get_settings
from app.db import get_db_connection, audit
from app.vector import delete_all_vectors, delete_document_vectors

log = logging.getLogger(__name__)


def delete_all_tenant_documents(tenant: str, actor: str) -> dict:
    """
    Permanently purge ALL documents belonging to a tenant across:
    1. Pinecone vector namespace
    2. AWS S3 object store
    3. PostgreSQL document catalog
    """
    s = get_settings()
    s3 = client('s3')

    # 1. Retrieve all existing document records for tenant from PostgreSQL
    with get_db_connection() as conn:
        docs = conn.execute(
            "SELECT id, title, s3_key FROM documents WHERE tenant_id = %s",
            (tenant,)
        ).fetchall()

    doc_ids = [str(d['id']) for d in docs]
    titles = [d['title'] for d in docs]
    s3_keys = [d['s3_key'] for d in docs if d['s3_key']]

    log.info("Initiating bulk deletion of %d documents for tenant '%s'", len(docs), tenant)

    # 2. Wipe Pinecone vectors for this tenant namespace
    try:
        delete_all_vectors(tenant)
    except Exception as exc:
        log.error("Pinecone bulk vector deletion error for tenant %s: %s", tenant, exc)

    # 3. Clean AWS S3
    s3_deleted_count = 0

    # A. Delete specific known document keys
    if s3_keys:
        try:
            objects = [{'Key': k} for k in s3_keys]
            for i in range(0, len(objects), 1000):
                batch = objects[i:i + 1000]
                resp = s3.delete_objects(Bucket=s.s3_bucket, Delete={'Objects': batch})
                s3_deleted_count += len(resp.get('Deleted', []))
        except Exception as exc:
            log.error("S3 batch deletion error for tenant %s keys: %s", tenant, exc)

    # B. Also purge any remaining incoming or orphaned files under tenants/{tenant}/
    try:
        paginator = s3.get_paginator('list_objects_v2')
        prefix = f"tenants/{tenant}/"
        for page in paginator.paginate(Bucket=s.s3_bucket, Prefix=prefix):
            contents = page.get('Contents', [])
            if contents:
                to_delete = [{'Key': obj['Key']} for obj in contents]
                resp = s3.delete_objects(Bucket=s.s3_bucket, Delete={'Objects': to_delete})
                s3_deleted_count += len(resp.get('Deleted', []))
    except Exception as exc:
        log.error("S3 tenant prefix purge error for '%s': %s", prefix, exc)

    # 4. Remove all records from PostgreSQL documents table
    deleted_db_count = 0
    with get_db_connection() as conn:
        res = conn.execute("DELETE FROM documents WHERE tenant_id = %s", (tenant,))
        deleted_db_count = res.rowcount if hasattr(res, 'rowcount') else len(docs)
        audit(conn, actor, tenant, 'documents_bulk_deleted', {
            'scope': 'all',
            'deleted_count': deleted_db_count,
            'titles': titles,
            'document_ids': doc_ids,
            's3_objects_deleted': s3_deleted_count
        })

    log.info(
        "Bulk deletion complete for tenant '%s': %d DB rows removed, %d S3 objects deleted",
        tenant, deleted_db_count, s3_deleted_count
    )

    return {
        'scope': 'all',
        'deleted_documents_count': deleted_db_count,
        'deleted_titles': titles,
        's3_objects_deleted': s3_deleted_count
    }


def delete_single_document(tenant: str, doc_id: str | uuid.UUID, actor: str) -> dict:
    """
    Permanently delete a single document by its UUID across:
    1. Pinecone vector namespace (filtered by document_id)
    2. AWS S3 object store (by s3_key)
    3. PostgreSQL document catalog
    """
    s = get_settings()
    s3 = client('s3')

    with get_db_connection() as conn:
        doc = conn.execute(
            "SELECT id, title, s3_key FROM documents WHERE id = %s AND tenant_id = %s",
            (doc_id, tenant)
        ).fetchone()

    if not doc:
        log.warning("Document %s for tenant %s not found in DB", doc_id, tenant)
        return {
            'scope': 'single',
            'found': False,
            'deleted_documents_count': 0,
            'title': None
        }

    title = doc['title']
    s3_key = doc['s3_key']

    # 1. Delete vector embeddings in Pinecone
    try:
        delete_document_vectors(tenant, str(doc_id))
    except Exception as exc:
        log.error("Pinecone vector deletion error for doc %s: %s", doc_id, exc)

    # 2. Delete S3 object
    s3_deleted = False
    if s3_key:
        try:
            s3.delete_object(Bucket=s.s3_bucket, Key=s3_key)
            s3_deleted = True
        except Exception as exc:
            log.error("S3 deletion error for key %s: %s", s3_key, exc)

    # 3. Delete from PostgreSQL
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM documents WHERE id = %s AND tenant_id = %s",
            (doc_id, tenant)
        )
        audit(conn, actor, tenant, 'document_deleted', {
            'document_id': str(doc_id),
            'title': title,
            's3_key': s3_key,
            's3_deleted': s3_deleted
        })

    log.info("Document %s ('%s') successfully deleted for tenant '%s'", doc_id, title, tenant)

    return {
        'scope': 'single',
        'found': True,
        'deleted_documents_count': 1,
        'title': title,
        's3_deleted': s3_deleted
    }


def resolve_and_execute_approval_action(
    approval_id: uuid.UUID,
    question: str,
    tenant: str,
    actor: str
) -> dict:
    """
    Inspect the approved request question text, identify the intended operation,
    and dispatch the appropriate execution workflow.
    """
    q_lower = question.lower().strip()

    # 1. Check for bulk deletion requests
    bulk_delete_signals = [
        'delete all',
        'delete every',
        'delete stored',
        'delete database',
        'empty database',
        'purge database',
        'clear database',
        'delete all documents',
        'delete all stored documents',
        'delete all the stored',
        'delete all old document versions',
        'remove all documents',
        'wipe all documents'
    ]

    if any(sig in q_lower for sig in bulk_delete_signals):
        log.info("Approval %s matched bulk document deletion signal", approval_id)
        result = delete_all_tenant_documents(tenant, actor)
        return {
            'executed': True,
            'action': 'delete_all_documents',
            'detail': result
        }

    # 2. Check for single document deletion requests
    if 'delete' in q_lower or 'remove' in q_lower:
        with get_db_connection() as conn:
            docs = conn.execute(
                "SELECT id, title FROM documents WHERE tenant_id = %s",
                (tenant,)
            ).fetchall()

        for d in docs:
            # If document title appears in the approval question
            if d['title'].lower() in q_lower or str(d['id']) in q_lower:
                log.info("Approval %s matched single document deletion for '%s' (%s)", approval_id, d['title'], d['id'])
                result = delete_single_document(tenant, d['id'], actor)
                return {
                    'executed': True,
                    'action': 'delete_single_document',
                    'detail': result
                }

    # Default: non-destructive or generic approval record
    return {
        'executed': False,
        'action': 'none',
        'detail': {}
    }
