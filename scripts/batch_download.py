#!/usr/bin/env python3
"""
Z-Library 批量下載腳本
批量下載多本書籍，優先 PDF 格式

用法：
    python3 batch_download.py --urls urls.json --output ~/Z-Library
    python3 batch_download.py --url "https://z-lib.fm/book/123" --output ~/Z-Library
"""

import asyncio
import json
import argparse
from pathlib import Path
from playwright.async_api import async_playwright

# 配置
CONFIG_DIR = Path.home() / ".zlibrary"
STORAGE_STATE = CONFIG_DIR / "storage_state.json"
DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "Z-Library"
DELAY_BETWEEN_DOWNLOADS = 5  # 秒
MAX_RETRIES = 3


async def download_single_book(page, url: str, output_dir: Path, retry_count: int = 0) -> Path | None:
    """
    下載單本書籍
    
    Args:
        page: Playwright page 物件
        url: 書籍頁面 URL
        output_dir: 下載目錄
        retry_count: 當前重試次數
        
    Returns:
        下載的檔案路徑，失敗則返回 None
    """
    
    download_path = None
    
    async def handle_download(download):
        nonlocal download_path
        suggested_filename = download.suggested_filename
        # 解碼檔名（避免亂碼）
        try:
            from urllib.parse import unquote
            suggested_filename = unquote(suggested_filename)
        except:
            pass
            
        download_path = output_dir / suggested_filename
        await download.save_as(download_path)
        print(f"    💾 已儲存: {download_path.name}")
    
    # 移除舊的 listener 以免重複
    try:
        page.remove_listener('download', handle_download)
    except:
        pass
    page.on('download', handle_download)
    
    try:
        print(f"  📖 訪問書籍頁面...")
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)
        
        # 嘗試添加到我的圖書館
        try:
            add_lib_btn = await page.query_selector('.book-details-button:has-text("Add to My Library"), .book-details-button:has-text("添加到我的图书馆"), .book-details-button:has-text("添加到我的圖書館")')
            if add_lib_btn:
                await add_lib_btn.click()
                print("    📚 已添加到我的圖書館")
            else:
                # 檢查是否已經添加 (按鈕文字可能變成 "Remove from My Library" 或類似)
                pass
        except Exception as e:
            print(f"    ⚠️ 添加到圖書館失敗: {e}")
        
        # 1. 嘗試直接下載 PDF
        pdf_link = await page.query_selector('a[href*="/dl/"][href*="pdf"], a.addDownloadedBook[href*="pdf"]')
        
        if pdf_link:
            print(f"    ✅ 找到 PDF 下載連結")
            await pdf_link.click()
        else:
            # 2. 嘗試透過下拉選單轉換
            print(f"    🔍 檢查格式選項...")
            format_btn = await page.query_selector('#btnCheckOtherFormats, .dlDropdownBtn, [class*="book-details-button-toggle"]')
            
            if format_btn:
                await format_btn.click()
                await asyncio.sleep(2)
                
                # 找 PDF 轉換選項
                convert_link = await page.query_selector('a[data-convert_to="pdf"], a[href*="convertedTo=pdf"], .dropdown-menu a:has-text("PDF")')
                
                if convert_link:
                    print(f"    🔄 啟動 PDF 轉換...")
                    await convert_link.click()
                    
                    # 等待轉換完成
                    print(f"    ⏳ 等待轉換中 (約需 30-60 秒)...")
                    for i in range(60):
                        # 檢查是否出現轉換後的下載連結
                        dl_link = await page.query_selector('a[href*="/dl/"][href*="convertedTo=pdf"]')
                        if dl_link and await dl_link.is_visible():
                            print(f"    ✅ 轉換完成，開始下載")
                            await dl_link.click()
                            break
                        
                        # 檢查是否已經開始下載 (有些轉換會自動觸發下載)
                        if download_path:
                            break
                            
                        await asyncio.sleep(1)
                else:
                    print(f"    ⚠️ 無 PDF 選項，嘗試下載預設格式 (EPUB)")
                    dl_link = await page.query_selector('a[href*="/dl/"], .addDownloadedBook')
                    if dl_link:
                        await dl_link.click()
            else:
                # 3. 無下拉選單，直接下載
                print(f"    ⚠️ 無格式選項，直接下載")
                dl_link = await page.query_selector('a[href*="/dl/"], .addDownloadedBook')
                if dl_link:
                    await dl_link.click()

        # 等待下載完成
        for i in range(120):
            if download_path and download_path.exists():
                return download_path
            await asyncio.sleep(1)
            if i % 10 == 0 and i > 0:
                print(f"    ⏳ 下載中... {i}秒")
        
        print(f"    ⚠️ 下載超時或失敗")
        
    except Exception as e:
        print(f"    ❌ 下載錯誤: {e}")
        
        # 重試邏輯
        if retry_count < MAX_RETRIES:
            print(f"    🔄 重試中... ({retry_count + 1}/{MAX_RETRIES})")
            await asyncio.sleep(5)
            return await download_single_book(page, url, output_dir, retry_count + 1)
    
    return None


async def batch_download(urls: list[str], output_dir: Path) -> list[dict]:
    """
    批量下載書籍
    
    Args:
        urls: 書籍頁面 URL 清單
        output_dir: 下載目錄
        
    Returns:
        下載結果清單
    """
    
    # 載入配置
    config_path = CONFIG_DIR / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'download': {
                'output_dir': str(DEFAULT_OUTPUT_DIR),
                'books_subdir': 'Books',
                'reports_subdir': 'Reports',
                'delay_between_books': 5
            }
        }

    if not STORAGE_STATE.exists():
        print("❌ 未找到 Z-Library 登入狀態")
        print("💡 請先執行: python3 scripts/login.py")
        return []
    
    # 設定輸出目錄
    # 優先使用命令行參數，如果沒有則使用配置檔，最後是預設值
    if output_dir != DEFAULT_OUTPUT_DIR: # 判斷是否為命令行預設值
        base_dir = output_dir
    else:
        base_dir = Path(config['download']['output_dir']).expanduser()
    
    books_dir = base_dir / config['download'].get('books_subdir', 'Books')
    books_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    async with async_playwright() as p:
        print(f"📥 開始批量下載 {len(urls)} 本書籍")
        print(f"📁 下載目錄: {books_dir}")
        print("=" * 50)
        
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=False)  # 使用有頭模式以便處理驗證
        context = await browser.new_context(
            storage_state=str(STORAGE_STATE),
            accept_downloads=True
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        for i, book_data in enumerate(urls):
            url = book_data.get('url')
            if not url:
                print(f"\n[{i+1}/{len(urls)}] ⚠️ 跳過無效的書籍資料: {book_data}")
                results.append({
                    "index": i + 1,
                    "url": None,
                    "success": False,
                    "path": None,
                    "error": "URL missing"
                })
                continue

            print(f"\n[{i+1}/{len(urls)}] 下載書籍...")
            print(f"  🔗 {url[:60]}...")
            
            downloaded_path = await download_single_book(page, url, books_dir)
            
            result = {
                "index": i + 1,
                "url": url,
                "success": downloaded_path is not None,
                "path": str(downloaded_path) if downloaded_path else None
            }
            results.append(result)
            
            if downloaded_path:
                print(f"  ✅ 下載成功: {downloaded_path.name}")
            else:
                print(f"  ❌ 下載失敗")
            
            # 書籍間延遲（避免觸發限速）
            if i < len(urls) - 1:
                delay = config['download']['delay_between_books']
                print(f"  ⏳ 等待 {delay} 秒...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # 統計結果
    success_count = sum(1 for r in results if r['success'])
    print("\n" + "=" * 50)
    print(f"📊 下載完成: {success_count}/{len(urls)} 本成功")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Z-Library 批量下載工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--urls", help="JSON 檔案，包含書籍 URL 清單")
    group.add_argument("--url", help="單一書籍 URL")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT_DIR), help=f"下載目錄 (預設: {DEFAULT_OUTPUT_DIR})")
    
    args = parser.parse_args()
    
    # 解析 URL 清單
    if args.urls:
        with open(args.urls, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 支援兩種格式：純 URL 清單或包含 url 欄位的物件清單
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    urls = data # 直接傳遞字典列表
                else:
                    # 如果是字串列表，包裝成字典
                    urls = [{'url': url} for url in data]
            else:
                urls = [data] if isinstance(data, dict) else [{'url': data}]
    else:
        urls = [{'url': args.url}]
    
    output_dir = Path(args.output).expanduser()
    
    # 執行下載
    results = asyncio.run(batch_download(urls, output_dir))
    
    # 輸出結果摘要
    print("\n📋 下載結果:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        filename = Path(r['path']).name if r['path'] else "N/A"
        print(f"  {status} [{r['index']}] {filename}")


if __name__ == "__main__":
    main()
