import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db_connection

def test_hitl_deletion_workflow():
    client = TestClient(app)
    results = []

    # 1. Ask chat to delete all stored documents (including user's exact phrasing with typo)
    user_prompt = "delete all the stored deocument in your database"
    r_chat = client.post('/api/chat', json={'question': user_prompt})
    assert r_chat.status_code == 200, f"Chat failed: {r_chat.status_code} {r_chat.text}"
    chat_resp = r_chat.json()
    assert chat_resp.get('status') == 'pending_approval', f"Expected pending_approval, got {chat_resp}"
    approval_id = chat_resp.get('approval_id')
    assert approval_id, "Missing approval_id in response"
    results.append("PASS: Chat intercepted 'delete all documents' and requested HITL approval")

    # 2. Verify approval record in DB
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, question, status FROM approvals WHERE id = %s", (approval_id,)).fetchone()
        assert row is not None, "Approval record not found in DB"
        assert row['status'] == 'pending'
        assert row['question'] == user_prompt
    results.append("PASS: Approval record stored in database with 'pending' status")

    # 3. Approve the deletion request via /api/approvals/{id}/decision
    r_decision = client.post(f"/api/approvals/{approval_id}/decision", json={'approve': True})
    assert r_decision.status_code == 200, f"Decision failed: {r_decision.status_code} {r_decision.text}"
    dec_resp = r_decision.json()
    assert dec_resp.get('status') == 'approved'
    assert dec_resp.get('executed') is True, f"Expected executed=True, got {dec_resp}"
    assert dec_resp.get('action') == 'delete_all_documents', f"Expected delete_all_documents, got {dec_resp.get('action')}"
    assert 'detail' in dec_resp
    results.append("PASS: Approval decision triggered execution of delete_all_tenant_documents")

    # 4. Verify database state & audit log
    with get_db_connection() as conn:
        app_row = conn.execute("SELECT status, reviewer, reviewed_at FROM approvals WHERE id = %s", (approval_id,)).fetchone()
        assert app_row['status'] == 'approved'
        assert app_row['reviewer'] is not None

        # Check audit log for execution event
        audit_row = conn.execute(
            "SELECT action, detail FROM audit_events WHERE action = 'documents_bulk_deleted' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert audit_row is not None, "Audit event 'documents_bulk_deleted' was not recorded"
        assert audit_row['detail'].get('scope') == 'all'
    results.append("PASS: Approvals audit log recorded 'documents_bulk_deleted'")

    # 5. Test rejection workflow
    r_chat_reject = client.post('/api/chat', json={'question': 'delete all documents from workspace'})
    assert r_chat_reject.status_code == 200
    reject_approval_id = r_chat_reject.json().get('approval_id')

    r_reject_dec = client.post(f"/api/approvals/{reject_approval_id}/decision", json={'approve': False})
    assert r_reject_dec.status_code == 200
    rej_resp = r_reject_dec.json()
    assert rej_resp.get('status') == 'rejected'
    assert rej_resp.get('executed') is False
    results.append("PASS: Rejection records status='rejected' and does NOT execute deletion")

    print("\n" + "=" * 60)
    print("VERITAS HITL DELETION WORKFLOW TEST: ALL PASSED")
    print("=" * 60)
    for r in results:
        print(f"  [+] {r}")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    test_hitl_deletion_workflow()
