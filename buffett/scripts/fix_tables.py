#!/usr/bin/env python3
"""
修复 marker 转换中首页业绩对比表损坏的 5 份文件：
2004, 2015, 2018, 2019, 2020

方案：用 pymupdf 提取首页纯文本 → 解析数据 → 生成标准 Markdown 表格 → 替换 marker 版本首页
"""

import re
from pathlib import Path
import pymupdf

ROOT = Path("/home/dtl/projects/data/BuffettLetters")
LETTERS = ROOT / "letters"
PDF_DIR = LETTERS / "original_pdf"

# 各年份的表格列结构
TABLE_CONFIGS = {
    2004: {
        "title": "Berkshire's Corporate Performance vs. the S&P 500",
        "columns": ["Year", "in Per-Share\nBook Value of\nBerkshire\n(1)",
                    "in S&P 500\nwith Dividends\nIncluded\n(2)",
                    "Relative\nResults\n(1)-(2)"],
        "num_cols": 3,
    },
    2015: {
        "title": "Berkshire's Performance vs. the S&P 500",
        "columns": ["Year", "in Per-Share\nBook Value of\nBerkshire",
                    "in Per-Share\nMarket Value of\nBerkshire",
                    "in S&P 500\nwith Dividends\nIncluded"],
        "num_cols": 3,
    },
    2018: {
        "title": "Berkshire's Performance vs. the S&P 500",
        "columns": ["Year", "in Per-Share\nBook Value of\nBerkshire",
                    "in Per-Share\nMarket Value of\nBerkshire",
                    "in S&P 500\nwith Dividends\nIncluded"],
        "num_cols": 3,
    },
    2019: {
        "title": "Berkshire's Performance vs. the S&P 500",
        "columns": ["Year", "in Per-Share\nMarket Value of\nBerkshire",
                    "in S&P 500\nwith Dividends\nIncluded"],
        "num_cols": 2,
    },
    2020: {
        "title": "Berkshire's Performance vs. the S&P 500",
        "columns": ["Year", "in Per-Share\nMarket Value of\nBerkshire",
                    "in S&P 500\nwith Dividends\nIncluded"],
        "num_cols": 2,
    },
}


def extract_table_data(pdf_path: Path, num_cols: int) -> list[dict]:
    """从 PDF 首页提取业绩表数据"""
    doc = pymupdf.open(str(pdf_path))
    rows = []

    # 可能跨 1-2 页
    for page_idx in range(min(2, len(doc))):
        page = doc[page_idx]
        text = page.get_text("text")
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
        
            # 匹配年份行: "1965 . . . . . . ." 或纯 "1965"（后跟 dots 行）
            year_match = re.match(r"^(\d{4})\s*[.\s]*$", line)
            compound_match = re.match(
                r"^(Compounded|Average) Annual Gain", line, re.IGNORECASE
            )
            overall_match = re.match(r"^Overall Gain", line, re.IGNORECASE)
        
            if year_match:
                year = year_match.group(1)
                # 收集后续非空行中的数值（跳过 dots 行）
                values = []
                j = 1
                while len(values) < num_cols and i + j < len(lines):
                    val = lines[i + j].strip()
                    j += 1
                    if not val:
                        continue
                    # 跳过纯 dots 行
                    if re.match(r"^[.\s]+$", val):
                        continue
                    # 如果遇到下一个年份或 Compounded/Overall，停止
                    if re.match(r"^\d{4}", val) or re.match(r"^(Compounded|Overall)", val, re.IGNORECASE):
                        break
                    # 清理尾部 dots
                    val = re.sub(r"[.\s]+$", "", val)
                    if val:
                        values.append(val)
                if len(values) == num_cols:
                    rows.append({"year": year, "values": values})
                i += j - 1  # 回退一行（因为下个循环 i+=1 不在这里）
                i = max(i, i)  # 安全
                # 直接跳到消耗完的位置
                i = i  # i 已经正确
            elif compound_match:
                # Compounded Annual Gain 行
                values = []
                j = 1
                while len(values) < num_cols and i + j < len(lines):
                    val = lines[i + j].strip()
                    j += 1
                    if not val:
                        continue
                    if re.match(r"^[.\s]+$", val):
                        continue
                    if re.match(r"^(Overall|\d{4})", val, re.IGNORECASE):
                        break
                    val = re.sub(r"[.\s]+$", "", val)
                    if val:
                        values.append(val)
                if len(values) >= num_cols:
                    range_match = re.search(r"(\d{4})[–—-](\d{4})", line)
                    gain_type = "Compounded Annual Gain" if "compounded" in line.lower() else "Average Annual Gain"
                    label = f"{gain_type} – {range_match.group(1)}-{range_match.group(2)}" if range_match else gain_type
                    rows.append({"year": label, "values": values[:num_cols]})
                i += j - 1
            elif overall_match:
                values = []
                j = 1
                while len(values) < num_cols and i + j < len(lines):
                    val = lines[i + j].strip()
                    j += 1
                    if not val:
                        continue
                    if re.match(r"^[.\s]+$", val):
                        continue
                    if re.match(r"^(Compounded|\d{4})", val, re.IGNORECASE):
                        break
                    val = re.sub(r"[.\s]+$", "", val)
                    if val:
                        values.append(val)
                if len(values) >= num_cols:
                    range_match = re.search(r"(\d{4})[–—-](\d{4})", line)
                    label = f"Overall Gain – {range_match.group(1)}-{range_match.group(2)}" if range_match else "Overall Gain"
                    rows.append({"year": label, "values": values[:num_cols]})
                i += j - 1
            else:
                i += 1

    doc.close()
    return rows


def generate_markdown_table(config: dict, rows: list[dict]) -> str:
    """生成标准 Markdown 表格"""
    num_cols = config["num_cols"]
    title = config["title"]

    # 表头
    header_labels = ["Year"]
    for col in config["columns"][1:]:
        # 多行表头用 <br> 连接
        header_labels.append(col.replace("\n", "<br>"))

    # 计算列宽
    col_widths = [max(len(h), 36) for h in header_labels]
    col_widths[0] = max(col_widths[0], 36)

    lines = []
    lines.append(f"## {title}")
    lines.append("")

    # 表格头
    header_cells = [f" {h:<{col_widths[i]}} " for i, h in enumerate(header_labels)]
    lines.append("|" + "|".join(header_cells) + "|")

    # 分隔线
    sep_cells = ["-" * (col_widths[i] + 2) for i in range(len(header_labels))]
    lines.append("|" + "|".join(sep_cells) + "|")

    # 数据行
    for row in rows:
        year_cell = f" {row['year']:<{col_widths[0]}} "
        cells = [year_cell]
        for j, val in enumerate(row["values"]):
            cells.append(f" {val:<{col_widths[j+1]}} ")
        lines.append("|" + "|".join(cells) + "|")

    return "\n".join(lines)


def find_body_start(md_content: str) -> int:
    """找到正文开始位置（BERKSHIRE HATHAWAY INC. 标题）"""
    patterns = [
        r"^#+\s*\*?\*?BERKSHIRE HATHAWAY",
        r"^\*?\*?BERKSHIRE HATHAWAY INC\.",
        r"^####?\s+\*?\*?To the Shareholders",
    ]
    for pat in patterns:
        m = re.search(pat, md_content, re.MULTILINE)
        if m:
            return m.start()
    return -1


def find_note_line(md_content: str, body_start: int) -> str:
    """提取 Note 行（如果在首页表格后面）"""
    before_body = md_content[:body_start]
    note_match = re.search(
        r"(\*?\*?Note:?\*?\*?:?\s*Data are for calendar years.*?)(?:\n\n|\Z)",
        before_body,
        re.DOTALL,
    )
    if note_match:
        return "\n" + note_match.group(1).strip() + "\n"
    return ""


def fix_file(year: int):
    """修复单个文件"""
    config = TABLE_CONFIGS[year]
    pdf_path = PDF_DIR / f"{year}.pdf"
    md_path = LETTERS / f"{year}.md"

    if not pdf_path.exists():
        print(f"  ✗ PDF 不存在: {pdf_path}")
        return False
    if not md_path.exists():
        print(f"  ✗ MD 不存在: {md_path}")
        return False

    # 1. 提取表格数据
    rows = extract_table_data(pdf_path, config["num_cols"])
    if not rows:
        print(f"  ✗ 未能从 PDF 提取数据")
        return False

    print(f"  提取到 {len(rows)} 行数据（{rows[0]['year']} - {rows[-1]['year']}）")

    # 2. 生成 Markdown 表格
    table_md = generate_markdown_table(config, rows)

    # 3. 读取当前 marker 输出
    md_content = md_path.read_text(encoding="utf-8")

    # 4. 找正文开始位置
    body_start = find_body_start(md_content)
    if body_start < 0:
        print(f"  ✗ 未找到正文起始位置")
        return False

    # 5. 提取 Note 行
    note = find_note_line(md_content, body_start)

    # 6. 拼接：新表格 + Note + 原正文
    body = md_content[body_start:]
    new_content = table_md + "\n" + note + "\n" + body

    # 7. 写回
    md_path.write_text(new_content, encoding="utf-8")
    print(f"  ✓ 已修复（表格 {len(rows)} 行，正文从 '{body[:50].strip()}'...）")
    return True


def main():
    print("=== 修复首页业绩表 ===\n")
    fixed = 0
    for year in sorted(TABLE_CONFIGS.keys()):
        print(f"[{year}]")
        if fix_file(year):
            fixed += 1
        print()
    print(f"完成，修复 {fixed}/{len(TABLE_CONFIGS)} 份。")


if __name__ == "__main__":
    main()
