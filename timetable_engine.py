import asyncio
import os
from playwright.async_api import async_playwright

# Update: Fixed syntax error for Railway deployment
async def get_timetable_screenshot(group_name: str) -> str | None:
    """
    tsue.edupage.org saytidan guruh jadvalini screenshot qiladi.
    """
    output_path = f"static/timetable_{group_name.replace('/', '_')}.png"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ]
            )
            page = await browser.new_page(viewport={"width": 1280, "height": 900})

            print(f"[Timetable] Fetching: {group_name}")
            await page.goto("https://tsue.edupage.org/timetable/", wait_until="domcontentloaded", timeout=20000)

            # 1. "Sinflar" (Классы) menyusini darhol bosish
            try:
                await page.click(".as-menu-item-label", timeout=3000)
            except Exception:
                try:
                    await page.click("text=Sinflar", timeout=2000)
                except Exception:
                    pass

            # 2. Guruhni topish va tanlash
            try:
                await page.wait_for_selector(f"text={group_name}", timeout=3000)
                await page.click(f"text={group_name}")
                print(f"[Timetable] Group {group_name} clicked.")
            except Exception:
                await page.keyboard.type(group_name)
                await page.keyboard.press("Enter")

            # 3. Jadval yuklanishini kutish
            try:
                await page.wait_for_selector("div.print-nobreak, .timetable", timeout=4000)
            except Exception:
                pass

            await page.wait_for_timeout(500)
            
            # Screenshot olish
            target = await page.query_selector("div.print-nobreak") or await page.query_selector(".timetable")
            if target:
                await target.screenshot(path=output_path)
            else:
                await page.screenshot(path=output_path)

            await browser.close()
            return output_path

    except Exception as e:
        print(f"[Timetable] Error: {e}")
        return None
