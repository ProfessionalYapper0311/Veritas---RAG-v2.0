import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

def run_sanity_checks():
    client = TestClient(app)
    results = []

    # 1. Health checks
    r_live = client.get('/health/live')
    assert r_live.status_code == 200, f"/health/live failed: {r_live.status_code}"
    assert r_live.json() == {'status': 'alive'}
    results.append("PASS: /health/live returns alive")

    r_ready = client.get('/health/ready')
    assert r_ready.status_code == 200, f"/health/ready failed: {r_ready.status_code}"
    assert r_ready.json() == {'status': 'ready'}
    results.append("PASS: /health/ready verified DB connectivity")

    # 2. Frontend HTML template render
    r_home = client.get('/')
    assert r_home.status_code == 200, f"GET / failed: {r_home.status_code}"
    html = r_home.text
    assert 'Veritas' in html
    assert 'Pinecone Serverless (1024-dim Gemini)' in html
    assert '1024-dim Titan' not in html
    assert 'Secure direct upload' in html
    assert 'Direct S3 Presigned Upload' not in html
    assert 'Sensitive actions require administrator approval.' in html
    results.append("PASS: GET / renders template with updated copy and Gemini references")

    # 3. Static assets served
    r_css = client.get('/static/css/style.css')
    assert r_css.status_code == 200
    assert 'prefers-reduced-motion' in r_css.text
    results.append("PASS: /static/css/style.css served and includes prefers-reduced-motion")

    r_js = client.get('/static/js/script.js')
    assert r_js.status_code == 200
    assert 'btn-delete-doc' in r_js.text
    assert 'btn-decide-approval' in r_js.text
    assert "onclick=\"window.VeritasApp.requestDocumentDeletion" not in r_js.text
    assert "onclick=\"window.VeritasApp.handleApprovalDecision" not in r_js.text
    results.append("PASS: /static/js/script.js served and verified free of inline XSS onclick handlers")

    # 4. API endpoints
    r_docs = client.get('/api/documents')
    assert r_docs.status_code == 200
    assert 'documents' in r_docs.json()
    results.append("PASS: GET /api/documents returns documents list")

    r_approvals = client.get('/api/approvals')
    assert r_approvals.status_code == 200
    assert 'approvals' in r_approvals.json()
    results.append("PASS: GET /api/approvals returns approvals list")

    r_metrics = client.get('/api/admin/metrics')
    assert r_metrics.status_code == 200
    assert 'documents' in r_metrics.json()
    assert 'feedback' in r_metrics.json()
    results.append("PASS: GET /api/admin/metrics returns metrics data")

    r_guardrails = client.get('/api/admin/guardrails')
    assert r_guardrails.status_code == 200
    assert 'events' in r_guardrails.json()
    results.append("PASS: GET /api/admin/guardrails returns guardrail events")

    print("\n" + "=" * 50)
    print("VERITAS COMPREHENSIVE SANITY CHECK: ALL PASSED")
    print("=" * 50)
    for r in results:
        print(f"  [+] {r}")
    print("=" * 50 + "\n")

if __name__ == '__main__':
    run_sanity_checks()
