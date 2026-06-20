"""
Test script: So sánh pdfplumber vs pymupdf vs LightRAG native cho PDF
Chạy: python scripts/test_pdf_parser.py [path_to_pdf]
Mặc định test file SATO PDF export nếu có, fallback sang sensor PDF
"""

import sys
from pathlib import Path

try:
    import pdfplumber
    import fitz  # pymupdf
except ImportError as e:
    print(f"ERROR: {e}. Chạy: pip install pdfplumber pymupdf")
    sys.exit(1)

# Danh sách file test — ưu tiên file đã so sánh với DOCX
TEST_FILES = [
    Path(r"D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Swarovski\Manual\Hướng dẫn vận hành_SATO_V2.docx".replace(".docx", ".pdf")),
    Path(r"D:\Robolinks Intern\Project\SecondBrain\local-nas\Sensor\Autonics\Sensorguidebook.pdf"),
    Path(r"D:\Robolinks Intern\Project\SecondBrain\local-nas\Sensor\Keyence\KC_500W.pdf"),
]

# Nếu có arg thì dùng file đó
if len(sys.argv) > 1:
    TEST_FILES = [Path(sys.argv[1])]

PDF_PATH = next((f for f in TEST_FILES if f.exists()), None)

if PDF_PATH is None:
    # Tìm file PDF bất kỳ trong local-nas
    base = Path(r"D:\Robolinks Intern\Project\SecondBrain\local-nas")
    pdfs = list(base.rglob("*.pdf"))
    if pdfs:
        PDF_PATH = pdfs[0]
    else:
        print("ERROR: Không tìm thấy file PDF nào trong local-nas")
        sys.exit(1)

print(f"File: {PDF_PATH.name}")
print(f"Path: {PDF_PATH}")
print(f"Size: {PDF_PATH.stat().st_size / 1024:.1f} KB")
print("=" * 70)


# ─── Parser 1: pdfplumber ─────────────────────────────────────────────────

def parse_pdfplumber(path: Path) -> dict:
    """
    pdfplumber: detect bảng theo border/line, extract text theo layout.
    Tốt cho: PDF text-based có bảng rõ ràng.
    """
    blocks = []
    total_chars = 0
    table_count = 0
    page_count = 0

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract bảng trước
            tables = page.extract_tables()
            table_bboxes = []

            for table in tables:
                if not table:
                    continue
                table_count += 1
                rows = []
                for row in table:
                    cells = [str(c or "").strip().replace("\n", " ") for c in row]
                    rows.append("| " + " | ".join(cells) + " |")
                if rows:
                    sep = "| " + " | ".join(["---"] * len(table[0])) + " |"
                    rows.insert(1, sep)
                    md = "\n".join(rows)
                    blocks.append({
                        "type": "table",
                        "page": page_num,
                        "markdown": md,
                        "rows": len(table),
                        "cols": len(table[0]) if table else 0,
                    })

            # Extract text, loại trừ vùng bảng
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                # Skip trang mục lục (nhiều dòng kết thúc bằng số)
                lines = text.strip().split("\n")
                non_toc_lines = [
                    l for l in lines
                    if not (l.strip() and l.strip()[-1].isdigit() and len(l.strip()) < 60
                            and "." * 3 in l)
                ]
                clean_text = "\n".join(non_toc_lines).strip()
                if clean_text:
                    blocks.append({
                        "type": "text",
                        "page": page_num,
                        "text": clean_text,
                        "chars": len(clean_text),
                    })
                    total_chars += len(clean_text)

    return {
        "parser": "pdfplumber",
        "blocks": blocks,
        "page_count": page_count,
        "table_count": table_count,
        "text_chars": total_chars,
        "total_blocks": len(blocks),
    }


# ─── Parser 2: pymupdf ────────────────────────────────────────────────────

def parse_pymupdf(path: Path) -> dict:
    """
    pymupdf (fitz): đọc text theo block vật lý, preserve whitespace tốt hơn native.
    Tốt cho: PDF phức tạp, preserve paragraph boundaries.
    """
    blocks = []
    total_chars = 0
    page_count = 0

    doc = fitz.open(path)
    page_count = doc.page_count

    for page_num in range(page_count):
        page = doc[page_num]
        # extract_text với sort=True để đọc theo thứ tự đọc tự nhiên
        text = page.get_text("text", sort=True)
        if text and text.strip():
            blocks.append({
                "type": "text",
                "page": page_num + 1,
                "text": text.strip(),
                "chars": len(text.strip()),
            })
            total_chars += len(text.strip())

    doc.close()

    return {
        "parser": "pymupdf",
        "blocks": blocks,
        "page_count": page_count,
        "table_count": 0,  # pymupdf không detect bảng
        "text_chars": total_chars,
        "total_blocks": len(blocks),
    }


# ─── Build plain text ─────────────────────────────────────────────────────

def build_plain_text(result: dict) -> str:
    parts = []
    for block in result["blocks"]:
        if block["type"] == "text":
            parts.append(block["text"])
        elif block["type"] == "table":
            parts.append(f"\n[Bảng trang {block['page']} — {block['rows']} hàng × {block['cols']} cột]\n")
            parts.append(block["markdown"])
    return "\n\n".join(parts)


# ─── Main ─────────────────────────────────────────────────────────────────

def print_result(result: dict, preview_chars: int = 3000):
    print(f"\n{'─'*70}")
    print(f"PARSER: {result['parser'].upper()}")
    print(f"{'─'*70}")
    print(f"  Pages          : {result['page_count']}")
    print(f"  Text blocks    : {result.get('total_blocks', 0) - result.get('table_count', 0)}")
    print(f"  Tables detected: {result['table_count']}")
    print(f"  Total chars    : {result['text_chars']:,}")

    # Preview blocks đầu tiên
    print(f"\n  📄 Blocks preview (10 đầu):")
    for i, block in enumerate(result["blocks"][:10]):
        if block["type"] == "text":
            preview = block["text"][:100].replace("\n", "↵")
            print(f"    [P{i} trang {block['page']}] {preview}")
        elif block["type"] == "table":
            print(f"    [TABLE trang {block['page']}] {block['rows']}×{block['cols']}")
            lines = block["markdown"].split("\n")
            for line in lines[:3]:
                print(f"      {line[:100]}")


def main():
    print("\n🔬 TEST 1: pdfplumber")
    result_plumber = parse_pdfplumber(PDF_PATH)
    print_result(result_plumber)

    plain_plumber = build_plain_text(result_plumber)
    out1 = Path("scripts/output_pdf_pdfplumber.txt")
    out1.write_text(plain_plumber, encoding="utf-8")
    print(f"\n  ✅ Full output → {out1} ({len(plain_plumber):,} chars)")

    print("\n🔬 TEST 2: pymupdf")
    result_mupdf = parse_pymupdf(PDF_PATH)
    print_result(result_mupdf)

    plain_mupdf = build_plain_text(result_mupdf)
    out2 = Path("scripts/output_pdf_pymupdf.txt")
    out2.write_text(plain_mupdf, encoding="utf-8")
    print(f"\n  ✅ Full output → {out2} ({len(plain_mupdf):,} chars)")

    # So sánh cuối
    print(f"\n{'='*70}")
    print("📊 SO SÁNH TỔNG HỢP")
    print(f"{'='*70}")
    print(f"{'Tiêu chí':<25} {'pdfplumber':>15} {'pymupdf':>15}")
    print(f"{'─'*55}")
    print(f"{'Tables detected':<25} {result_plumber['table_count']:>15} {result_mupdf['table_count']:>15}")
    print(f"{'Total chars':<25} {result_plumber['text_chars']:>15,} {result_mupdf['text_chars']:>15,}")
    print(f"{'Total blocks':<25} {result_plumber['total_blocks']:>15} {result_mupdf['total_blocks']:>15}")

    winner = "pdfplumber" if result_plumber["table_count"] > 0 else "pymupdf"
    print(f"\n→ Recommended for this PDF: {winner}")
    print(f"  (pdfplumber nếu có bảng, pymupdf nếu text-heavy)")


if __name__ == "__main__":
    main()
