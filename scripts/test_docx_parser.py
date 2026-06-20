"""
Test script: So sánh python-docx DOM traversal vs LightRAG native parser
Chạy: python scripts/test_docx_parser.py
Output: in ra text đã extract, thống kê completeness
"""

from pathlib import Path
import sys

try:
    import docx
except ImportError:
    print("ERROR: python-docx chưa được cài. Chạy: pip install python-docx")
    sys.exit(1)


DOCX_PATH = Path(
    r"D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Swarovski\Manual\Hướng dẫn vận hành_SATO.docx"
)


def extract_table_as_markdown(table) -> str:
    """Extract docx table thành Markdown format."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append("| " + " | ".join(cells) + " |")

    if not rows:
        return ""

    # Insert header separator sau dòng đầu
    header_sep = "| " + " | ".join(["---"] * len(table.columns)) + " |"
    rows.insert(1, header_sep)
    return "\n".join(rows)


def parse_docx_dom(path: Path) -> dict:
    """
    DOM traversal: đọc toàn bộ paragraphs và tables theo thứ tự xuất hiện trong document.
    Không bỏ sót text nằm giữa ảnh.
    """
    doc = docx.Document(path)

    # Dùng document XML body để traverse theo đúng thứ tự DOM
    # (doc.paragraphs và doc.tables tách rời nhau, không preserve interleaved order)
    from docx.oxml.ns import qn

    blocks = []
    table_index = 0
    para_index = 0

    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":  # paragraph
            # Lấy paragraph object tương ứng
            if para_index < len(doc.paragraphs):
                para = doc.paragraphs[para_index]
                para_index += 1
                text = para.text.strip()
                if text:
                    style = para.style.name if para.style else ""
                    blocks.append({
                        "type": "paragraph",
                        "text": text,
                        "style": style,
                    })

        elif tag == "tbl":  # table
            if table_index < len(doc.tables):
                table = doc.tables[table_index]
                table_index += 1
                md = extract_table_as_markdown(table)
                if md:
                    blocks.append({
                        "type": "table",
                        "index": table_index,
                        "markdown": md,
                        "rows": len(table.rows),
                        "cols": len(table.columns),
                    })

        elif tag == "sectPr":  # section properties — bỏ qua
            pass

    return {
        "blocks": blocks,
        "para_count": sum(1 for b in blocks if b["type"] == "paragraph"),
        "table_count": sum(1 for b in blocks if b["type"] == "table"),
        "total_chars": sum(len(b["text"]) for b in blocks if b["type"] == "paragraph"),
    }


def build_plain_text(result: dict) -> str:
    """Ghép tất cả blocks thành plain text để gửi vào LightRAG."""
    parts = []
    for block in result["blocks"]:
        if block["type"] == "paragraph":
            parts.append(block["text"])
        elif block["type"] == "table":
            parts.append(f"\n[Bảng {block['index']} — {block['rows']} hàng × {block['cols']} cột]\n")
            parts.append(block["markdown"])
    return "\n\n".join(parts)


def main():
    if not DOCX_PATH.exists():
        print(f"ERROR: File không tồn tại: {DOCX_PATH}")
        sys.exit(1)

    print(f"File: {DOCX_PATH.name}")
    print(f"Size: {DOCX_PATH.stat().st_size / 1024:.1f} KB")
    print("=" * 70)

    result = parse_docx_dom(DOCX_PATH)

    print(f"\n📊 THỐNG KÊ PARSE:")
    print(f"  Paragraphs extracted : {result['para_count']}")
    print(f"  Tables extracted     : {result['table_count']}")
    print(f"  Total chars          : {result['total_chars']:,}")

    # So sánh với baseline native parser
    native_chars = 9680 * 4  # ước tính: 9680 tokens * ~4 chars/token
    completeness = result["total_chars"] / native_chars
    print(f"  Completeness vs native: {completeness:.0%}")

    print("\n" + "=" * 70)
    print("📄 NỘI DUNG THEO THỨTỰ DOM:\n")

    for i, block in enumerate(result["blocks"]):
        if block["type"] == "paragraph":
            style = f"[{block['style']}] " if "Heading" in block.get("style", "") else ""
            print(f"  P{i:03d} {style}{block['text'][:120]}")
        elif block["type"] == "table":
            print(f"\n  TABLE {block['index']} ({block['rows']}×{block['cols']}):")
            for line in block["markdown"].split("\n")[:4]:  # preview 4 dòng đầu
                print(f"    {line[:100]}")
            if block["rows"] > 4:
                print(f"    ... ({block['rows'] - 4} hàng nữa)")
            print()

    print("\n" + "=" * 70)
    print("📝 PLAIN TEXT (preview 2000 chars đầu để gửi vào LightRAG):\n")
    plain = build_plain_text(result)
    print(plain[:2000])
    print(f"\n... (tổng {len(plain):,} chars)")

    # Ghi ra file để review đầy đủ
    output_path = Path("scripts/output_docx_parse.txt")
    output_path.write_text(plain, encoding="utf-8")
    print(f"\n✅ Full output đã ghi vào: {output_path}")


if __name__ == "__main__":
    main()
