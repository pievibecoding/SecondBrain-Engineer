# Local Ingest Test Guide

Test nhanh 1 file `.docx` từ `local-nas` lên backend, LightRAG, PostgreSQL, vector DB và graph.

## 5 Bước

### 1) Chạy stack local
```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

### 2) Chép file test vào `local-nas`
Ví dụ:
```powershell
copy "C:\path\to\test.docx" "D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Demo\docs\"
```

Folder test nên là:
```text
/local-nas/projects/Demo/docs
```

### 3) Tạo folder trên web
Vào `Admin > NAS Folders`, thêm:
```text
/local-nas/projects/Demo/docs
```

Chọn:
- `manual` để kiểm tra qua queue
- `auto` nếu muốn file vào luồng ingest tự động

### 4) Bấm `Scan now`
Vào `Admin > NAS Folders`, bấm `Scan now` ở đúng folder vừa thêm.

- Nếu folder là `auto`, file sẽ đi thẳng vào ingest.
- Nếu folder là `manual`, file sẽ vào `NAS Queue` để bạn `Approve` trên UI.

### 5) Verify
Khi thành công, kiểm tra:
- `Admin > Documents` thấy file ở trạng thái `indexed`
- `LightRAG` có chunks/entities/relations
- `PostgreSQL` có record `nas_files`, chunk, vector, entity/relation

## Kết quả mong đợi

Trong PostgreSQL sẽ có:
- `nas_files.status = indexed`
- `lightrag_doc_status.status = processed`
- `lightrag_doc_chunks` có dữ liệu
- `lightrag_full_entities` và `lightrag_full_relations` có row mới

## Nếu không thấy file

1. Kiểm tra path trong web có đúng là `/local-nas/projects/Demo/docs`
2. Kiểm tra file thật có nằm đúng trong thư mục mount chưa
3. Kiểm tra lại đã bấm `Scan now` trên đúng folder chưa
4. Nếu file vào `rejected`, mở `nas_files.reject_reason`
5. Nếu file vào `failed`, mở `nas_files.error_msg`

## Ghi chú quan trọng

- Local test này là workflow chuẩn cho repo hiện tại.
- `nas-connector` là đường production/legacy; local test chuẩn hiện tại chạy hoàn toàn trên UI.
- Với DOCX/PDF/XLSX, backend sẽ pre-parse trước rồi mới gửi sang LightRAG.
