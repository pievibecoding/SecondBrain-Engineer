# NAS Connector Rules — SecondBrain

> Load khi làm việc với nas-connector/ hoặc NAS-related backend code.

---

## NAS Setup

| Item | Value |
|---|---|
| Type | Synology NAS |
| Network | LAN nội bộ (cùng subnet với server) |
| Protocol | SMB/CIFS (port 445) |
| Host OS mount | `//NAS_IP/SHARE_NAME` → `/mnt/synology` |
| Docker volume | `/mnt/synology:/mnt/nas:ro` (read-only) |
| User | `secondbrain` — dedicated account, read-only permissions |

---

## Environment Variables

```ini
NAS_HOST=192.168.1.x        # IP Synology trên LAN
NAS_USER=secondbrain         # Dedicated user, NOT admin
NAS_PASS=...
NAS_SHARE=documents          # Synology Shared Folder name
NAS_MOUNT_PATH=/mnt/synology # Host OS mount point
BACKEND_API_URL=http://backend:8000
```

---

## Single Source of Truth (QUAN TRỌNG)

**nas-connector KHÔNG tự lưu file state.**
Mọi file hash tracking đều qua backend API:

```python
# ĐÚNG — gọi backend để check hash
async def file_changed(nas_path: str, current_hash: str) -> bool:
    resp = await httpx.get(
        f"{BACKEND_URL}/api/internal/nas/hash",
        params={"path": nas_path}
    )
    stored_hash = resp.json().get("hash")
    return stored_hash != current_hash

# SAI — KHÔNG lưu SQLite local
import sqlite3  # KHÔNG trong nas-connector
```

---

## NasFile State Machine

```
DETECTED
  ├── auto folder → QUEUED → backend triggers LightRAG ingestion
  └── manual folder → PENDING_REVIEW → admin approves → QUEUED

QUEUED → INDEXING → INDEXED (success)
                  → FAILED (error, có error_msg)

PENDING_REVIEW → QUEUED (admin approve)
               → REJECTED (admin reject, có reject_reason)
```

State transitions chỉ được thực hiện bởi **backend API** — nas-connector chỉ REPORT file mới, không tự chuyển state.

---

## Folder Types

```
auto-sync folder:
  nas-connector detect → POST /api/internal/nas/report → backend tự QUEUE

manual-review folder:
  nas-connector detect → POST /api/internal/nas/report → backend set PENDING_REVIEW
                      → backend notify admin → admin approve/reject qua UI
```

---

## SMB Mount (Host OS setup — chạy trước docker-compose)

```bash
# Tạo mount point
sudo mkdir -p /mnt/synology

# Mount Synology share
sudo mount -t cifs //NAS_IP/documents /mnt/synology \
  -o username=secondbrain,password=NAS_PASS,uid=1000,gid=1000,vers=3.0

# Auto-mount khi reboot — thêm vào /etc/fstab
//NAS_IP/documents /mnt/synology cifs username=secondbrain,password=NAS_PASS,uid=1000,gid=1000,vers=3.0 0 0
```

---

## File Change Detection

nas-connector so sánh hash của file để phát hiện thay đổi.
Poll interval: mỗi 5 phút.

```python
# Supported file types cho ingestion
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt'}

# Binary files — chỉ index metadata, không parse content
METADATA_ONLY_EXTENSIONS = {'.dwg', '.dxf', '.png', '.jpg', '.mp4', '.avi', '.step', '.stl'}
```

---

## Folder Path Convention (Important for AI context extraction)

LightRAG extract entity từ folder path — **convention này ảnh hưởng đến chất lượng AI**:

```
/projects/{ProjectName}-{Year}/{stage}/{type}/filename.ext

Ví dụ:
/projects/Heineken-BinhDuong-2024/design/electrical/DA-CB01-v3.dwg
/projects/Vinamilk-Line3-2023/documentation/SOP-vận-hành-CB01.pdf
/internal/HR/onboarding/quy-trinh-onboarding-2024.docx

→ AI infer: PROJECT=Heineken-BinhDuong-2024, STAGE=design, TYPE=electrical
```

Nếu NAS của Robolinks chưa theo convention này → note trong config để LightRAG adjust metadata extraction.
