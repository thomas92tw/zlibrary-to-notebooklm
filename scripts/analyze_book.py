#!/usr/bin/env python3
"""
PDF 書籍分析腳本
提取 PDF 內容並生成「5 個核心問題與解答」分析報告

用法：
    python3 analyze_book.py ~/Z-Library/book.pdf
    python3 analyze_book.py ~/Z-Library/book.pdf --output ~/Z-Library/analysis.md
"""

import argparse
import re
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ 請先安裝 PyMuPDF: pip install pymupdf")
    exit(1)


# 配置
MAX_PAGES = 50  # 提取前 N 頁
QUESTIONS_COUNT = 5


def extract_pdf_text(pdf_path: Path, max_pages: int = MAX_PAGES) -> tuple[str, dict]:
    """
    提取 PDF 文字內容
    
    Args:
        pdf_path: PDF 檔案路徑
        max_pages: 最大提取頁數
        
    Returns:
        (提取的文字內容, 元數據字典)
    """
    
    doc = fitz.open(pdf_path)
    
    # 提取元數據
    title = doc.metadata.get("title", "")
    if not title or title.strip() == "":
        title = pdf_path.stem
        
    metadata = {
        "title": title,
        "author": doc.metadata.get("author", "未知作者"),
        "subject": doc.metadata.get("subject", ""),
        "keywords": doc.metadata.get("keywords", ""),
        "total_pages": len(doc),
        "extracted_pages": min(max_pages, len(doc))
    }
    
    # 提取文字
    text_content = []
    pages_to_extract = min(max_pages, len(doc))
    
    for page_num in range(pages_to_extract):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_content.append(f"--- 第 {page_num + 1} 頁 ---\n{text}")
    
    doc.close()
    
    return "\n\n".join(text_content), metadata


def generate_analysis_template(metadata: dict, content_preview: str) -> str:
    """
    生成分析報告 Markdown 模板
    
    注意：此函數生成模板結構，實際的深度分析需要由 AI 完成
    """
    
    title = metadata.get("title", "未知書名")
    author = metadata.get("author", "未知作者")
    total_pages = metadata.get("total_pages", 0)
    extracted_pages = metadata.get("extracted_pages", 0)
    
    # 清理標題（移除特殊字符）
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
    
    report = f"""# 《{safe_title}》閱讀分析報告

## 📖 書籍資訊

| 項目 | 內容 |
|:-----|:-----|
| **書名** | {title} |
| **作者** | {author} |
| **總頁數** | {total_pages} 頁 |
| **分析範圍** | 前 {extracted_pages} 頁 |
| **分析日期** | {datetime.now().strftime('%Y-%m-%d')} |

---

## 🎯 內容概述

> [!NOTE]
> 以下分析基於書籍前 {extracted_pages} 頁的內容提取。

{{CONTENT_OVERVIEW}}

---

## 💡 5 個核心問題與解答

### 問題 1：{{Q1_TITLE}}

**問題描述**：{{Q1_QUESTION}}

**解答**：
{{Q1_ANSWER}}

---

### 問題 2：{{Q2_TITLE}}

**問題描述**：{{Q2_QUESTION}}

**解答**：
{{Q2_ANSWER}}

---

### 問題 3：{{Q3_TITLE}}

**問題描述**：{{Q3_QUESTION}}

**解答**：
{{Q3_ANSWER}}

---

### 問題 4：{{Q4_TITLE}}

**問題描述**：{{Q4_QUESTION}}

**解答**：
{{Q4_ANSWER}}

---

### 問題 5：{{Q5_TITLE}}

**問題描述**：{{Q5_QUESTION}}

**解答**：
{{Q5_ANSWER}}

---

## 📚 延伸思考

- {{EXTENSION_1}}
- {{EXTENSION_2}}
- {{EXTENSION_3}}

---

## 🔗 相關連結

- **原始檔案**：`~/Z-Library/{safe_title}.pdf`
- **NotebookLM**：[手動上傳後填入連結]

---

*本報告由 Antigravity Z-Library Workflow 自動生成*
"""
    
    return report


def analyze_book(pdf_path: Path, output_path: Path | None = None) -> str:
    """
    分析書籍並生成報告
    
    Args:
        pdf_path: PDF 檔案路徑
        output_path: 輸出 Markdown 檔案路徑（可選）
        
    Returns:
        生成的 Markdown 報告內容
    """
    
    print(f"📖 開始分析: {pdf_path.name}")
    print("=" * 50)
    
    # 載入配置
    config_path = Path.home() / ".gemini" / "zlibrary-to-notebooklm" / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'download': {
                'output_dir': '~/Desktop/Z-Library',
                'reports_subdir': 'Reports'
            }
        }

    # 1. 提取 PDF 內容
    print("📄 提取 PDF 文字內容...")
    content, metadata = extract_pdf_text(pdf_path)
    
    print(f"  ✅ 書名: {metadata['title']}")
    print(f"  ✅ 作者: {metadata['author']}")
    print(f"  ✅ 提取頁數: {metadata['extracted_pages']}/{metadata['total_pages']}")
    print(f"  ✅ 文字長度: {len(content):,} 字符")
    
    # 2. 生成報告模板
    print("\n📝 生成分析報告模板...")
    report_template = generate_analysis_template(metadata, content[:5000])
    
    # 3. 儲存報告
    # The provided snippet introduces a 'config' variable which is not available here.
    # Assuming the intent is to use a default 'Reports' subdirectory relative to the PDF's parent directory
    # if output_path is not explicitly given.
    if output_path is None:
        # 設定輸出目錄
        # The original code had a duplicate '設定輸出目錄' comment and an undefined 'config' variable.
        # I'm assuming 'config' would be passed or globally available, and for now,
        # I'll use a placeholder for 'config' to make the code syntactically valid,
        # or revert to the original logic if 'config' is truly not intended to be introduced here.
        # Given the instruction, I will insert the new logic as provided, assuming 'config' will be defined elsewhere.
        # For the purpose of this edit, I will assume 'config' is available.
        # If 'config' is not defined, this will cause a NameError.
        # To make it syntactically correct and reflect the user's intent, I'll add a dummy config for now.
        # In a real scenario, 'config' should be loaded from a file or passed as an argument.
        
        # Placeholder for config, assuming it will be defined globally or passed.
        # For this specific edit, I'll assume a simple structure for 'config' to avoid NameError.
        # In a real application, 'config' would be loaded from a configuration file.
        config = {
            'download': {
                'output_dir': pdf_path.parent, # Default to PDF's parent if config not fully set
                'reports_subdir': 'Reports'
            }
        }
        
        base_dir = Path(config['download']['output_dir']).expanduser()
        reports_base = base_dir / config['download'].get('reports_subdir', 'Reports')
        
        md_dir = reports_base / "Markdown"
        txt_dir = reports_base / "Text"
        
        md_dir.mkdir(parents=True, exist_ok=True)
        txt_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成檔名 (使用 PDF 檔名作為基礎)
        base_name = pdf_path.stem
        report_path = md_dir / f"{base_name}.md"
        content_path = txt_dir / f"{base_name}_content.txt"
    else:
        # If output_path is provided, use it for the report and derive content_path
        report_path = output_path
        content_path = output_path.parent / f"{output_path.stem}_content.txt"

    # 生成報告內容
    if len(content) == 0:
        print(f"  ⚠️ 警告: 無法提取文字 (可能是掃描檔或加密)")
        report_content = f"""# 《{metadata['title']}》分析報告

> [!WARNING] 無法提取文字
> 此 PDF 檔案似乎不包含可提取的文字層（可能是純圖片掃描檔）。
> 
> **建議行動：**
> 請直接將此 PDF 上傳至 **NotebookLM**。NotebookLM 具備強大的 OCR (光學字元識別) 功能，可以讀取掃描檔內容。
> 
> [開啟 NotebookLM](https://notebooklm.google.com/)
"""
    else:
        report_content = generate_analysis_template(metadata, content[:5000])
    
    # 寫入報告
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  ✅ 報告已儲存: {report_path}")

    # 寫入原始內容
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(f"# 《{metadata['title']}》原始內容提取\n\n")
        f.write(f"作者: {metadata['author']}\n")
        f.write(f"提取範圍: 前 {metadata['extracted_pages']} 頁\n")
        f.write("=" * 50 + "\n\n")
        f.write(content)
    print(f"  ✅ 原始內容已儲存: {content_path}")
    
    print("\n" + "=" * 50)
    print("⚠️ 注意：報告模板中的 {{...}} 區塊需要由 AI 填入具體分析內容")
    print("💡 請將 _content.txt 檔案提供給 AI 進行深度分析")
    
    return report_content


def main():
    parser = argparse.ArgumentParser(description="PDF 書籍分析工具")
    parser.add_argument("pdf", help="PDF 檔案路徑")
    parser.add_argument("--output", "-o", help="輸出 Markdown 檔案路徑")
    parser.add_argument("--pages", "-p", type=int, default=MAX_PAGES, 
                        help=f"提取頁數 (預設: {MAX_PAGES})")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf).expanduser()
    
    if not pdf_path.exists():
        print(f"❌ 檔案不存在: {pdf_path}")
        exit(1)
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"❌ 不是 PDF 檔案: {pdf_path}")
        exit(1)
    
    output_path = Path(args.output).expanduser() if args.output else None
    
    analyze_book(pdf_path, output_path)


if __name__ == "__main__":
    main()
