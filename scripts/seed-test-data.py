#!/usr/bin/env python3
"""
SecondBrain — Local stack validation and seed script.

Usage (after docker compose up -d and alembic upgrade head):
  python scripts/seed-test-data.py

What it does:
  1. Ingest 2 sample documents from local-nas/ into LightRAG
  2. Run a test query to verify search works
  3. Print status summary
"""
import sys
import time
import json
import httpx
from pathlib import Path

LIGHTRAG_URL = "http://localhost:9621"
BACKEND_URL = "http://localhost:8000"

ROOT = Path(__file__).parent.parent
LOCAL_NAS = ROOT / "local-nas"

SAMPLE_FILES = [
    {
        "local_path": LOCAL_NAS / "projects" / "Heineken-BinhDuong-2024" / "documentation" / "SOP-van-hanh-CB01.txt",
        "nas_path": "/projects/Heineken-BinhDuong-2024/documentation/SOP-van-hanh-CB01.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/Heineken-BinhDuong-2024/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "projects" / "Heineken-BinhDuong-2024" / "documentation" / "BOM-Heineken-2024.txt",
        "nas_path": "/projects/Heineken-BinhDuong-2024/documentation/BOM-Heineken-2024.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/Heineken-BinhDuong-2024/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "projects" / "Heineken-BinhDuong-2024" / "documentation" / "Troubleshooting-G120.txt",
        "nas_path": "/projects/Heineken-BinhDuong-2024/documentation/Troubleshooting-G120.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/Heineken-BinhDuong-2024/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "projects" / "Vinamilk-Line3-2023" / "documentation" / "SOP-bao-tri-dinh-ky.txt",
        "nas_path": "/projects/Vinamilk-Line3-2023/documentation/SOP-bao-tri-dinh-ky.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/Vinamilk-Line3-2023/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "projects" / "Vinamilk-Line3-2023" / "documentation" / "BOM-Vinamilk-Line3.txt",
        "nas_path": "/projects/Vinamilk-Line3-2023/documentation/BOM-Vinamilk-Line3.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/Vinamilk-Line3-2023/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "projects" / "THP-Group-2024" / "documentation" / "SOP-robot-palletizing.txt",
        "nas_path": "/projects/THP-Group-2024/documentation/SOP-robot-palletizing.txt",
        "metadata": {"source": "local-seed", "folder": "/projects/THP-Group-2024/documentation", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "internal" / "technical" / "catalog-encoder-Omron.txt",
        "nas_path": "/internal/technical/catalog-encoder-Omron.txt",
        "metadata": {"source": "local-seed", "folder": "/internal/technical", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "internal" / "technical" / "quy-trinh-FAT.txt",
        "nas_path": "/internal/technical/quy-trinh-FAT.txt",
        "metadata": {"source": "local-seed", "folder": "/internal/technical", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "internal" / "HR" / "quy-trinh-onboarding.txt",
        "nas_path": "/internal/HR/quy-trinh-onboarding.txt",
        "metadata": {"source": "local-seed", "folder": "/internal/HR", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
    {
        "local_path": LOCAL_NAS / "internal" / "HR" / "noi-quy-cong-ty.txt",
        "nas_path": "/internal/HR/noi-quy-cong-ty.txt",
        "metadata": {"source": "local-seed", "folder": "/internal/HR", "folder_type": "auto", "uploaded_by": "seed-script"},
    },
]


def check_health():
    """Verify backend and LightRAG are reachable."""
    print("Checking services...")
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"  ✅ Backend: {BACKEND_URL}")
    except Exception as e:
        print(f"  ❌ Backend unreachable: {e}")
        print("     → Run: docker compose -f docker-compose.yml -f docker-compose.local.yml up -d")
        sys.exit(1)

    try:
        r = httpx.get(f"{LIGHTRAG_URL}/health", timeout=5)
        print(f"  ✅ LightRAG: {LIGHTRAG_URL}")
    except Exception:
        # LightRAG may not have /health — try a query instead
        try:
            r = httpx.post(f"{LIGHTRAG_URL}/api/v1/query",
                          json={"query": "test", "mode": "naive"}, timeout=10)
            print(f"  ✅ LightRAG reachable (status {r.status_code})")
        except Exception as e:
            print(f"  ❌ LightRAG unreachable: {e}")
            print("     → Check: docker compose logs lightrag")
            sys.exit(1)


def ingest_file(local_path: Path, nas_path: str, metadata: dict) -> str | None:
    """Ingest a local file into LightRAG by sending the text content directly."""
    if not local_path.exists():
        print(f"  ⚠️  File not found: {local_path}")
        return None

    print(f"  Ingesting: {nas_path}")
    try:
        text_content = local_path.read_text(encoding="utf-8")
        # LightRAG latest uses /documents/text endpoint
        resp = httpx.post(
            f"{LIGHTRAG_URL}/documents/text",
            json={
                "text": text_content,
                "file_source": nas_path,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        doc_id = result.get("id", "unknown")
        print(f"  ✅ Accepted — doc_id: {doc_id}, status: {result.get('status')}")
        return doc_id
    except httpx.HTTPStatusError as e:
        print(f"  ❌ HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def test_query(query: str) -> bool:
    """Run a test query and print result."""
    print(f"\nQuery: '{query}'")
    try:
        resp = httpx.post(
            f"{LIGHTRAG_URL}/query",
            json={"query": query, "mode": "mix"},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        answer = result.get("response", "")
        print(f"  Response ({len(answer)} chars): {answer[:300]}{'...' if len(answer) > 300 else ''}")
        return True
    except Exception as e:
        print(f"  ❌ Query failed: {e}")
        return False


def create_test_user():
    """Register a test user in the backend."""
    print("\nCreating test user...")
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/auth/register",
            json={"username": "testuser", "email": "test@robolinks.vn", "password": "password123"},
            timeout=10,
        )
        if resp.status_code == 201:
            token = resp.json().get("access_token")
            print(f"  ✅ User created — token: {token[:20]}...")
            return token
        elif resp.status_code == 409:
            # Already exists — login instead
            resp2 = httpx.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"email": "test@robolinks.vn", "password": "password123"},
                timeout=10,
            )
            if resp2.status_code == 200:
                token = resp2.json().get("access_token")
                print(f"  ✅ User exists — logged in, token: {token[:20]}...")
                return token
        print(f"  ⚠️  Unexpected status {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ {e}")
        return None


def main():
    print("=" * 50)
    print("SecondBrain — Local Stack Validation")
    print("=" * 50)

    check_health()

    print("\nIngesting sample documents...")
    doc_ids = []
    for f in SAMPLE_FILES:
        doc_id = ingest_file(f["local_path"], f["nas_path"], f["metadata"])
        if doc_id:
            doc_ids.append(doc_id)

    if doc_ids:
        print(f"\nWaiting 5s for LightRAG to process {len(doc_ids)} document(s)...")
        time.sleep(5)

        test_query("Dự án Heineken dùng motor gì?")
        test_query("Quy trình onboarding nhân viên mới gồm những bước nào?")
    else:
        print("\n⚠️  No documents ingested — skipping query test")

    token = create_test_user()
    if token:
        print("\n✅ Backend auth working")

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Documents ingested: {len(doc_ids)}")
    print(f"  Backend auth: {'✅' if token else '❌'}")
    print(f"  Frontend: http://localhost:3000")
    print(f"  Backend API docs: http://localhost:8000/docs")
    print(f"  LightRAG Web UI: http://localhost:9621")
    print(f"  Seq logs: http://localhost:5380")
    print("=" * 50)


if __name__ == "__main__":
    main()
