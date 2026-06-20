# Hướng dẫn kết nối Claude Desktop với SecondBrain MCP

## Tổng quan

SecondBrain cung cấp MCP server tại `http://localhost:8000/mcp`, cho phép Claude Desktop
truy vấn knowledge base kỹ thuật của Robolinks trực tiếp trong khi chat.

---

## Bước 1: Cấu hình Claude Desktop

Mở file cấu hình Claude Desktop:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Thêm vào file (hoặc merge nếu file đã có `mcpServers`):

```json
{
  "mcpServers": {
    "secondbrain-robolinks": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

Lưu file và **khởi động lại Claude Desktop**.

---

## Bước 2: Thêm Custom Instruction

Trong Claude Desktop → Settings → Custom Instructions, thêm:

```
Khi trả lời câu hỏi về kỹ thuật, dự án, thiết bị của Robolinks,
luôn dùng tool search_knowledge trước khi trả lời.
```

---

## Bước 3: Đăng nhập

SecondBrain MCP yêu cầu Bearer token. Đăng nhập qua API để lấy token:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'
```

Cấu hình token trong Claude Desktop config:

```json
{
  "mcpServers": {
    "secondbrain-robolinks": {
      "url": "http://localhost:8000/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer <your_token_here>"
      }
    }
  }
}
```

---

## Tools có sẵn

### `search_knowledge_tool`

Tìm kiếm trong knowledge base bằng ngôn ngữ tự nhiên.

**Tham số:**
- `query` (bắt buộc): câu hỏi hoặc từ khóa cần tìm
- `mode` (tùy chọn, mặc định `"mix"`): chế độ tìm kiếm — `"mix"` | `"local"` | `"global"`

**Ví dụ:**
```
search_knowledge_tool(query="Dự án Heineken dùng motor gì?")
search_knowledge_tool(query="Quy trình FAT gồm những bước nào?", mode="local")
search_knowledge_tool(query="Nhà cung cấp encoder hiện tại là ai?")
```

---

### `get_entity_tool`

Lấy thông tin chi tiết về một entity trong knowledge graph (dự án, thiết bị, linh kiện...).

**Tham số:**
- `entity_name` (bắt buộc): tên entity cần tra cứu

**Ví dụ:**
```
get_entity_tool(entity_name="Heineken Bình Dương 2024")
get_entity_tool(entity_name="Motor Siemens 1LE1")
get_entity_tool(entity_name="Conveyor CB-01")
```

**Kết quả trả về:**
- `name`: tên entity
- `type`: loại entity (PROJECT, EQUIPMENT, COMPONENT, PERSON...)
- `description`: mô tả
- `relations`: danh sách quan hệ với các entity khác
- `sources`: tài liệu nguồn có liên quan
- `graph_nodes`, `graph_edges`: dữ liệu mini graph

---

## Lưu ý

- Backend phải đang chạy tại `http://localhost:8000` trước khi dùng
- Rate limit: 100 request/phút/token
- Token hết hạn sau 24h — đăng nhập lại để lấy token mới
