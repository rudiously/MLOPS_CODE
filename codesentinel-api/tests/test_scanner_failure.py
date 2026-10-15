import pytest
from sqlalchemy import select
from app.db.models import PRScan
from app.services import scanner

DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -0,0 +1 @@
+dangerous()
"""

def test_scan_diff_marks_scan_failed_and_reraises(db_session, monkeypatch):
    monkeypatch.setattr(scanner, "model_predict", lambda *_: (_ for _ in ()).throw(RuntimeError("model unavailable")))
    db = db_session()
    with pytest.raises(RuntimeError, match="model unavailable"):
        scanner.scan_diff(db, repo_name="acme/demo", pr_number=8, diff=DIFF)
    assert db.scalar(select(PRScan)).status == "failed"
    db.close()
