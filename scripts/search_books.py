#!/usr/bin/env python3
"""
Z-Library 書籍搜尋腳本
根據概念描述搜尋並推薦相關書籍

用法：
    python3 search_books.py "道德哲學" --limit 5
    python3 search_books.py "認知心理學" --output results.json
"""

import asyncio
import json
import argparse
from pathlib import Path
from urllib.parse import unquote
from playwright.async_api import async_playwright

# 配置
CONFIG_DIR = Path.home() / ".zlibrary"
STORAGE_STATE = CONFIG_DIR / "storage_state.json"
ZLIBRARY_SEARCH_URL = "https://z-lib.fm/s/"


async def search_books(concept: str, limit: int = 5) -> list[dict]:
    """
    在 Z-Library 搜尋書籍並返回推薦清單
    
    Args:
        concept: 搜尋概念/關鍵詞
        limit: 返回結果數量上限
        
    Returns:
        書籍資訊清單
    """
    
    if not STORAGE_STATE.exists():
        print("❌ 未找到 Z-Library 登入狀態")
        print("💡 請先執行: python3 scripts/login.py")
        return []
    
    results = []
    
    async with async_playwright() as p:
        print(f"🔍 搜尋概念：「{concept}」")
        print("=" * 50)
        
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(STORAGE_STATE))
        page = await context.new_page()
        
        try:
            # 構建搜尋 URL
            search_url = f"{ZLIBRARY_SEARCH_URL}{concept.replace(' ', '%20')}"
            print(f"📡 訪問搜尋頁面...")
            
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)  # 等待動態內容載入
            
            # 找 z-bookcard 元素 (Z-Library 的 Web Components)
            book_cards = await page.query_selector_all('z-bookcard')
            
            if not book_cards:
                # 備選：嘗試其他選擇器
                book_cards = await page.query_selector_all('[class*="bookCard"], .resItemBox')
            
            print(f"📚 找到 {len(book_cards)} 個搜尋結果")
            
            seen_urls = set()  # 用於去重
            
            for element in book_cards:
                if len(results) >= limit:
                    break
                    
                try:
                    # 提取書名 (slot="title")
                    title_el = await element.query_selector('[slot="title"]')
                    title = await title_el.inner_text() if title_el else ""
                    
                    if not title:
                        continue
                    
                    # 提取作者 (slot="author")
                    author_el = await element.query_selector('[slot="author"]')
                    author = await author_el.inner_text() if author_el else "未知作者"
                    
                    # 提取 URL (從父元素的 href 或查找 a 標籤)
                    # z-bookcard 本身可能是個連結
                    url = await element.get_attribute('href')
                    
                    if not url:
                        # 嘗試找內部的 a 標籤
                        parent = await element.evaluate_handle('el => el.closest("a")')
                        if parent:
                            url = await parent.evaluate('el => el.href')
                    
                    if not url:
                        # 從頁面上下文中找對應的連結
                        links = await page.query_selector_all(f'a[href*="/book/"]')
                        for link in links:
                            link_text = await link.inner_text()
                            if title.lower() in link_text.lower():
                                url = await link.get_attribute('href')
                                break
                    
                    if not url:
                        # 從書籍 ID 推斷 URL
                        book_id = await element.get_attribute('data-id')
                        if book_id:
                            url = f"/book/{book_id}"
                    
                    # 確保 URL 完整
                    if url and not url.startswith('http'):
                        url = f"https://z-lib.fm{url}"
                    
                    # 去重
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # 提取其他資訊
                    extend_el = await element.query_selector('[slot="extend"]')
                    extend_text = await extend_el.inner_text() if extend_el else ""
                    
                    # 嘗試從 extend 中解析格式、年份等
                    file_format = "PDF" if "pdf" in extend_text.lower() else "EPUB" if "epub" in extend_text.lower() else ""
                    
                    book_info = {
                        "index": len(results) + 1,
                        "title": title.strip(),
                        "author": author.strip(),
                        "url": url or "",
                        "format": file_format,
                        "year": "",
                        "language": "",
                        "size": ""
                    }
                    
                    results.append(book_info)
                    print(f"  {len(results)}. 《{title.strip()[:40]}》- {author.strip()[:25]}")
                    
                except Exception as e:
                    # 靜默跳過解析錯誤
                    continue
            
            # 如果 z-bookcard 解析失敗，嘗試從連結提取
            if len(results) < limit:
                print(f"\n🔄 嘗試備用解析方法...")
                links = await page.query_selector_all('a[href*="/book/"]')
                
                for link in links:
                    if len(results) >= limit:
                        break
                    
                    try:
                        href = await link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # 從 URL 解析書名
                        parts = href.split('/')
                        if len(parts) >= 4:
                            # URL 格式: /book/{id}/{hash}/{title}.html
                            title_slug = parts[-1].replace('.html', '')
                            title = unquote(title_slug).replace('-', ' ')
                            
                            if len(title) > 3:  # 過濾太短的
                                url = f"https://z-lib.fm{href}" if not href.startswith('http') else href
                                seen_urls.add(href)
                                
                                book_info = {
                                    "index": len(results) + 1,
                                    "title": title[:100],
                                    "author": "（請查看詳情頁）",
                                    "url": url,
                                    "format": "",
                                    "year": "",
                                    "language": "",
                                    "size": ""
                                }
                                results.append(book_info)
                                print(f"  {len(results)}. 《{title[:40]}》")
                    except:
                        continue
            
        except Exception as e:
            print(f"❌ 搜尋過程發生錯誤: {e}")
        
        finally:
            await browser.close()
    
    print("=" * 50)
    print(f"✅ 共推薦 {len(results)} 本書籍")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Z-Library 書籍搜尋工具")
    parser.add_argument("concept", help="搜尋概念或關鍵詞")
    parser.add_argument("--limit", "-l", type=int, default=5, help="推薦書籍數量 (預設: 5)")
    parser.add_argument("--output", "-o", help="輸出 JSON 檔案路徑")
    
    args = parser.parse_args()
    
    # 執行搜尋
    results = asyncio.run(search_books(args.concept, args.limit))
    
    # 輸出結果
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"📄 結果已儲存至: {output_path}")
    else:
        # 輸出到標準輸出
        print("\n📋 推薦書籍清單 (JSON):")
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
