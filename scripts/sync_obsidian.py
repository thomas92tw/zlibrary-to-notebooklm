#!/usr/bin/env python3
"""
Obsidian 同步腳本
將分析報告同步到 Obsidian vault

用法：
    python3 sync_obsidian.py --source ~/Z-Library/*.md --vault ~/Documents/note_2026
    python3 sync_obsidian.py --source ~/Z-Library/analysis.md --vault ~/Documents/note_2026 --subfolder Z-Library
"""

import argparse
import shutil
from pathlib import Path
from datetime import datetime
from glob import glob


# 預設配置
DEFAULT_VAULT = Path("/Users/thomastseng/Documents/note_2026")
DEFAULT_SUBFOLDER = "Z-Library"


def sync_to_obsidian(
    source_files: list[Path],
    vault_path: Path,
    subfolder: str = DEFAULT_SUBFOLDER,
    create_index: bool = True
) -> dict:
    """
    將 Markdown 檔案同步到 Obsidian vault
    
    Args:
        source_files: 來源 Markdown 檔案清單
        vault_path: Obsidian vault 路徑
        subfolder: 目標子資料夾
        create_index: 是否創建索引頁
        
    Returns:
        同步結果資訊
    """
    
    print(f"📂 Obsidian 同步")
    print("=" * 50)
    print(f"  📁 Vault: {vault_path}")
    print(f"  📁 子資料夾: {subfolder}")
    print(f"  📄 檔案數量: {len(source_files)}")
    
    # 驗證 vault 路徑
    if not vault_path.exists():
        print(f"❌ Vault 路徑不存在: {vault_path}")
        return {"success": False, "error": "Vault not found"}
    
    # 建立目標資料夾
    target_dir = vault_path / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✅ 目標資料夾: {target_dir}")
    
    # 同步檔案
    synced_files = []
    failed_files = []
    
    for source_file in source_files:
        if not source_file.exists():
            print(f"  ⚠️ 檔案不存在: {source_file}")
            failed_files.append(str(source_file))
            continue
        
        # 只同步 .md 檔案
        if source_file.suffix.lower() != '.md':
            print(f"  ⏭️ 跳過非 Markdown 檔案: {source_file.name}")
            continue
        
        # 複製檔案
        target_file = target_dir / source_file.name
        
        try:
            shutil.copy2(source_file, target_file)
            synced_files.append({
                "source": str(source_file),
                "target": str(target_file),
                "name": source_file.name
            })
            print(f"  ✅ 已同步: {source_file.name}")
        except Exception as e:
            print(f"  ❌ 同步失敗: {source_file.name} - {e}")
            failed_files.append(str(source_file))
    
    # 建立索引頁
    index_path = None
    if create_index and synced_files:
        index_path = create_research_index(target_dir, synced_files)
    
    # 結果摘要
    result = {
        "success": True,
        "synced_count": len(synced_files),
        "failed_count": len(failed_files),
        "synced_files": synced_files,
        "failed_files": failed_files,
        "target_dir": str(target_dir),
        "index_path": str(index_path) if index_path else None
    }
    
    print("\n" + "=" * 50)
    print(f"📊 同步完成: {len(synced_files)} 成功, {len(failed_files)} 失敗")
    
    return result


def create_research_index(target_dir: Path, synced_files: list[dict]) -> Path:
    """
    建立研究索引頁
    
    Args:
        target_dir: 目標資料夾
        synced_files: 已同步的檔案清單
        
    Returns:
        索引檔案路徑
    """
    
    index_path = target_dir / "_研究索引.md"
    
    # 生成索引內容
    content = f"""# 📚 Z-Library 研究索引

> 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📖 書籍分析報告

| # | 書籍 | 同步時間 |
|:--|:-----|:---------|
"""
    
    for i, file_info in enumerate(synced_files, 1):
        name = file_info['name'].replace('.md', '')
        # 使用 Obsidian 內部連結格式
        content += f"| {i} | [[{name}]] | {datetime.now().strftime('%Y-%m-%d')} |\n"
    
    content += f"""

---

## 📝 使用說明

1. 點擊上方連結查看各書籍的分析報告
2. 每份報告包含「5 個核心問題與解答」
3. 可搭配 NotebookLM 進行深度閱讀

## 🔗 相關資源

- **本地 PDF 檔案**: `~/Z-Library/`
- **NotebookLM**: [登入後手動上傳 PDF](https://notebooklm.google.com/)

---

*由 Antigravity Z-Library Workflow 自動生成*
"""
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  📋 已建立索引頁: {index_path.name}")
    
    return index_path


def main():
    parser = argparse.ArgumentParser(description="Obsidian Vault 同步工具")
    parser.add_argument("--source", "-s", required=False, help="來源檔案模式 (例如: ~/Z-Library/*.md)，若未提供則使用配置檔設定")
    parser.add_argument("--vault", "-v", default=str(DEFAULT_VAULT),
                        help=f"Obsidian vault 路徑 (預設: {DEFAULT_VAULT})")
    parser.add_argument("--subfolder", "-f", default=DEFAULT_SUBFOLDER,
                        help=f"目標子資料夾 (預設: {DEFAULT_SUBFOLDER})")
    parser.add_argument("--no-index", action="store_true",
                        help="不建立研究索引頁")
    
    args = parser.parse_args()
    
    # 讀取配置
    config_path = Path.home() / ".gemini" / "zlibrary-to-notebooklm" / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        # 預設配置
        config = {
            'download': {
                'output_dir': '~/Desktop/Z-Library',
                'reports_subdir': 'Reports'
            },
            'obsidian': {
                'subfolder': 'Z-Library'
            }
        }

    # 確定來源目錄
    base_dir = Path(config['download']['output_dir']).expanduser()
    reports_base = base_dir / config['download'].get('reports_subdir', 'Reports')
    reports_dir = reports_base / "Markdown"
    
    source_files = []
    if args.source:
        # 如果指定了模式，直接使用
        source_pattern = Path(args.source).expanduser()
        if '*' in str(source_pattern):
            source_files = [Path(f) for f in glob(str(source_pattern))]
        else:
            source_files = [source_pattern]
    else:
        # 否則掃描 reports_dir 下的所有 .md 檔案
        if not reports_dir.exists():
            print(f"❌ 報告目錄不存在: {reports_dir}")
            return
        source_files = list(reports_dir.glob("*.md"))
    
    if not source_files:
        print(f"❌ 未找到符合的檔案。請檢查 --source 參數或報告目錄: {reports_dir}")
        return # Changed from exit(1) to return for cleaner script flow
    
    vault_path = Path(args.vault).expanduser()
    
    # 執行同步
    result = sync_to_obsidian(
        source_files=source_files,
        vault_path=vault_path,
        subfolder=args.subfolder,
        create_index=not args.no_index
    )
    
    if result['success']:
        print("\n✅ 同步成功！")
        print(f"📂 請在 Obsidian 中查看: {result['target_dir']}")
    else:
        print(f"\n❌ 同步失敗: {result.get('error', '未知錯誤')}")


if __name__ == "__main__":
    main()
