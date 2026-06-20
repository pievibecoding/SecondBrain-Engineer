# So sánh Chi tiết 11 Công cụ/Framework Nguồn Mở trong Hệ Sinh Thái AI, RAG và Quản lý Kiến thức

## Giới thiệu Chung

Dưới đây là bảng so sánh chi tiết về chức năng và quy trình làm việc (Workflow) của 11 công cụ/framework nguồn mở phổ biến trong hệ sinh thái AI, RAG và Quản lý kiến thức hiện nay.

Các công cụ này được chia thành **4 nhóm bản chất**:

1. **Framework & Engine GraphRAG chuyên sâu**: Graphiti, Microsoft GraphRAG, LightRAG
2. **Nền tảng RAG & Agentic RAG tất-cả-trong-một (All-in-One)**: Dify, RAGFlow, Arkon
3. **Thư viện Core/Hạ tầng cho AI & Dữ liệu**: LangChain/LlamaIndex, Neo4j
4. **Ứng dụng Quản lý kiến thức cá nhân/Cộng tác (Local-first/Wiki)**: Logseq, AFFiNE

---

## 1. Bảng so sánh Tổng quan & Chức năng cốt lõi

| Tên Công Cụ | Bản chất / Phân loại chính | Kiến trúc dữ liệu lưu trữ chính | Điểm mạnh nhất (Core Feature) | Đối tượng / Khách hàng mục tiêu |
|---|---|---|---|---|
| **Arkon** | Enterprise AI Knowledge Hub & MCP Server | PostgreSQL (pgvector), Redis, MinIO | Biên dịch tài liệu (SOPs, chính sách) thành Wiki có cấu trúc thông qua pipeline MRP, đóng vai trò làm MCP Server bảo mật cho LLM (như Claude) | Doanh nghiệp muốn quản lý tài liệu nội bộ tập trung cho AI |
| **Graphiti** | Temporal Knowledge Graph Engine | Graph DB (Neo4j, FalkorDB...) + Vector/BM25 | Quản lý đồ thị tri thức theo dòng thời gian (temporal); tự động cập nhật/vô hiệu hóa các sự kiện cũ | Kỹ sư xây dựng Trí nhớ dài hạn (Memory) cho AI Agent/Chatbot |
| **Microsoft GraphRAG** | Global-Query GraphRAG Framework | File-based (Parquet) hoặc Vector DB sau khi trích xuất | Khả năng gom cụm cộng đồng (Leiden algorithm) để trả lời các câu hỏi mang tính tổng quát toàn cục (Global query) | Nhà nghiên cứu, doanh nghiệp cần phân tích xu hướng, tổng hợp toàn bộ kho tài liệu lớn |
| **LightRAG** | Dual-level GraphRAG Engine | Vector DB + Graph DB (Key-Value/Graph tinh gọn) | Kết hợp truy vấn cả mức độ Cục bộ (Local) lẫn Toàn cục (Global) với chi phí trích xuất đồ thị cực thấp và tốc độ nhanh | Developer cần GraphRAG tối ưu chi phí, hiệu năng cao, linh hoạt |
| **Dify** | LLMOps & Agent Workflow Platform | Vector DB (hỗ trợ nhiều loại) + SQL | Giao diện kéo thả (Low-code) trực quan, mạnh mẽ; tích hợp sẵn RAG nâng cao, Agent, Multi-Agent workflow, LLM orchestration | Developer, Product Manager muốn xây dựng nhanh ứng dụng AI từ Prototype đến Production |
| **RAGFlow** | Deep-doc Parsing RAG Platform | Elasticsearch / OpenSearch + Vector DB | Khả năng đọc và hiểu cấu trúc tài liệu phức tạp (Deep-doc parsing) như bảng biểu, biểu đồ trong PDF, Word nhờ mô hình thị giác (OCR/AI) | Doanh nghiệp có dữ liệu thô phức tạp, không định dạng, cần độ chính xác RAG cao |
| **WhyHow Knowledge Studio** | Graph Creation & Management Tool | Graph DB (Neo4j) + Vector DB | Giao diện trực quan giúp người dùng thiết kế, kiểm soát ontology (thực thể/quan hệ) và làm sạch đồ thị trước khi đưa vào RAG | Đội ngũ Data Engineer/AI Specialist cần tối ưu hóa và "gác cổng" cấu trúc dữ liệu đồ thị |
| **Logseq** | Privacy-first Knowledge Base (PKM) | Local Files (Markdown/Org-mode) + SQLite | Ghi chú dạng Bullet-point, tự động liên kết hai chiều (Bi-directional linking), ưu tiên bảo mật dữ liệu cục bộ | Cá nhân quản lý kiến thức (PKM), nhà nghiên cứu độc lập |
| **AFFiNE** | All-in-one Workspace (Next-gen Notion) | Local-first/Cloud CRDT (Yjs) + Block suite | Không gian làm việc kết hợp hoàn hảo giữa Bảng tài liệu (Docs) và Bảng vẽ tư duy (Whiteboard) | Đội nhóm sáng tạo, quản lý dự án trực quan, ghi chú đa phương tiện |
| **Neo4j (Community)** | Native Graph Database Engine | Đồ thị gốc (Nodes, Edges, Properties) | Cơ sở dữ liệu đồ thị hiệu năng cao nhất, hỗ trợ truy vấn Cypher phức tạp, tích hợp sẵn Vector Search trên đồ thị | Data Architect, Backend Engineer xây dựng hạ tầng dữ liệu liên kết |
| **LangChain / LlamaIndex** | Orchestration Framework (Code-first SDK) | Trực quan hóa/Kết nối mọi DB (Vector, Graph, SQL) | Cung cấp đầy đủ các khối linh kiện (chữ, chunk, prompt, agent, tool) dạng code-first để tùy biến mọi cấu trúc AI | Lập trình viên AI (Python/JS) muốn tự code và tùy biến sâu hệ thống RAG/Agent chuyên sâu |

---

## 2. So sánh Quy trình làm việc (Workflow)

Để thấy rõ sự khác biệt, dưới đây là cách dữ liệu đi vào (Ingestion) và đi ra khi người dùng hỏi (Retrieval) của từng công cụ:

### Nhóm 1: GraphRAG chuyên sâu

#### Graphiti

**Ingestion:**
- Văn bản thô (Episodes)
- $\rightarrow$ LLM trích xuất Entities/Relations dựa trên Pydantic Ontology
- $\rightarrow$ Lưu vào Neo4j kèm theo nhãn thời gian (Timestamp)
- $\rightarrow$ Nếu thông tin cũ bị thay đổi, cạnh (Edge) cũ sẽ bị set trạng thái hết hạn thay vì xóa đi

**Retrieval:**
- User hỏi
- $\rightarrow$ Tìm kiếm kết hợp (BM25 + Semantic Vector) để định vị node
- $\rightarrow$ Duyệt đồ thị (Graph Traversal) để lấy context theo đúng mốc thời gian yêu cầu

#### Microsoft GraphRAG

**Ingestion:**
- Tài liệu
- $\rightarrow$ Chunks
- $\rightarrow$ LLM trích xuất thực thể/quan hệ
- $\rightarrow$ Tạo đồ thị
- $\rightarrow$ Chạy thuật toán Leiden để chia đồ thị thành các cụm cộng đồng (Communities) từ nhỏ đến lớn
- $\rightarrow$ Dùng LLM viết báo cáo tóm tắt (Summaries) cho từng cụm
- $\rightarrow$ Lưu lại

**Retrieval (Global):**
- User hỏi câu mang tính tổng quát
- $\rightarrow$ Lấy tất cả báo cáo tóm tắt của các cụm cộng đồng
- $\rightarrow$ LLM tổng hợp các báo cáo song song
- $\rightarrow$ Đưa ra câu trả lời cuối cùng (Khá tốn kém token)

#### LightRAG

**Ingestion:**
- Cắt nhỏ tài liệu
- $\rightarrow$ LLM trích xuất mạng lưới thực thể cục bộ lẫn góc nhìn toàn cục
- $\rightarrow$ Lưu trữ tinh gọn vào hệ thống Key-Value/Vector mà không cần kiến trúc đồ thị quá nặng nề

**Retrieval:**
- User hỏi
- $\rightarrow$ Kích hoạt đồng thời 2 luồng tìm kiếm: Cục bộ (chi tiết thực thể cụ thể) và Toàn cục (mối quan hệ bao quát)
- $\rightarrow$ Trộn kết quả
- $\rightarrow$ LLM sinh câu trả lời

### Nhóm 2: Nền tảng All-in-One (Low-code/No-code)

#### Dify

**Ingestion:**
- Upload tài liệu lên giao diện Web
- $\rightarrow$ Chọn chiến lược Chunking (Tự động hoặc Thủ công)
- $\rightarrow$ Tạo Vector và lưu vào Vector DB tích hợp

**Workflow/Retrieval:**
- Thiết kế ứng dụng bằng giao diện kéo thả
- Ví dụ: Start node $\rightarrow$ LLM Node phân loại câu hỏi $\rightarrow$ RAG Retrieval Node $\rightarrow$ Code Node để format $\rightarrow$ LLM Answer
- Hỗ trợ Agent tự gọi Tool

#### RAGFlow

**Ingestion:**
- Upload tài liệu
- $\rightarrow$ Đi qua bộ Deep Document Parsing (Nhận diện đâu là tiêu đề, đâu là bảng biểu, chú thích hình ảnh dựa trên AI Vision)
- $\rightarrow$ Cắt nhỏ dựa trên ngữ cảnh cấu trúc (chứ không cắt bừa theo số ký tự)
- $\rightarrow$ Vector hóa

**Retrieval:**
- User hỏi
- $\rightarrow$ Kết hợp Hybrid Search (Vector + Toàn văn)
- $\rightarrow$ Trích xuất chính xác các chunk kèm bảng biểu gốc
- $\rightarrow$ LLM trả lời

#### Arkon

**Ingestion:**
- Nạp tài liệu doanh nghiệp
- $\rightarrow$ Chạy qua pipeline MRP (Map $\rightarrow$ Reduce $\rightarrow$ Plan-review $\rightarrow$ Refine $\rightarrow$ Verify $\rightarrow$ Commit) để phân tích liên kết chéo giữa các tài liệu
- $\rightarrow$ Biên dịch thành một trang Wiki có tính liên kết chặt chẽ
- $\rightarrow$ Đẩy vào DB

**Retrieval:**
- Client (như Claude Desktop) gửi yêu cầu qua giao diện MCP
- $\rightarrow$ Arkon phân quyền truy cập của user
- $\rightarrow$ Đóng gói ngữ cảnh từ Wiki
- $\rightarrow$ Trả về cho LLM xử lý

### Nhóm 3: Hạ tầng & Thư viện Lập trình

#### LangChain / LlamaIndex

**Ingestion & Retrieval:**
- Không có workflow cố định
- Lập trình viên tự viết code kết nối:
  - Khai báo DocumentLoader
  - $\rightarrow$ TextSplitter
  - $\rightarrow$ VectorStore
- Khi gọi, tự viết logic Router, Reranking, Agentic Loop bằng mã nguồn (Python/TypeScript)

#### Neo4j (Community)

**Workflow:**
- Đóng vai trò là nơi lưu trữ nền tảng
- Nhận câu lệnh Cypher Query để tạo, đọc, cập nhật hoặc xóa cấu trúc đồ thị
- Cung cấp API để các framework khác (như Graphiti, LangChain) gọi vào tìm kiếm vector hoặc duyệt node

### Nhóm 4: Ứng dụng Quản lý Kiến thức (Workspace)

#### Logseq & AFFiNE

**Workflow:**
- Người dùng trực tiếp tương tác, viết lách, kéo thả
- Dữ liệu lưu cục bộ dưới dạng file Markdown hoặc cấu trúc Block
- Gần đây, cả hai đều tích hợp AI cục bộ (Local AI/Ollama) hoặc API để biến các trang ghi chú cá nhân thành kho tri thức cho tính năng Chat-with-your-docs

---

## 3. Tóm tắt khuyến nghị lựa chọn

### Chọn Dify nếu...
Bạn cần làm sản phẩm AI nhanh chóng, có giao diện kéo thả cho cả team cùng làm, tích hợp nhiều LLM.

### Chọn RAGFlow nếu...
Dữ liệu của bạn có quá nhiều file PDF chứa bảng biểu phức tạp mà các công cụ khác đọc ra bị lỗi font/mất cấu trúc.

### Chọn Microsoft GraphRAG nếu...
Bạn có một kho sách/tài liệu nghiên cứu khổng lồ và cần AI trả lời những câu hỏi mang tính vĩ mô như "Tóm tắt các xu hướng công nghệ xuất hiện trong 1000 tài liệu này".

### Chọn Graphiti nếu...
Bạn đang làm trợ lý ảo cá nhân (AI Companion) cần nhớ lịch sử trò chuyện và cập nhật trạng thái của người dùng theo thời gian thực (ví dụ: "Hôm qua user thích đi ăn lẩu, hôm nay họ đã chuyển sang ăn chay").

### Chọn LightRAG nếu...
Bạn thích kiến trúc GraphRAG nhưng cần nó chạy mượt, tiết kiệm tiền API và cài đặt nhanh gọn.

### Chọn Arkon nếu...
Bạn cần một giải pháp MCP bảo mật cho doanh nghiệp để kết nối trực tiếp tài liệu nội bộ với Claude.

### Chọn LangChain / LlamaIndex nếu...
Bạn là lập trình viên muốn tự tay code và kiểm soát từng dòng lệnh của hệ thống AI.

---

**Tài liệu này cung cấp cái nhìn tổng quan về các công cụ RAG và AI phổ biến hiện nay, giúp bạn lựa chọn giải pháp phù hợp nhất với nhu cầu của mình.**
