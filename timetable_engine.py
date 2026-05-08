import asyncio
import os
from playwright.async_api import async_playwright


async def get_timetable_screenshot(group_name: str) -> str | None:
    """
    tsue.edupage.org saytidan guruh jadvalini screenshot qiladi.
    
    Args:
        group_name: Guruh nomi, masalan "II-53/24"
    
    Returns:
        Screenshot faylining yo'li yoki None (xatolik bo'lsa)
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
            # Sahifa yuklanishini kutamiz (faqat DOM tayyor bo'lishi kifoya)
            await page.goto("https://tsue.edupage.org/timetable/", wait_until="domcontentloaded", timeout=20000)

            # 1. "Sinflar" (Классы) menyusini darhol bosish
            try:
                # 'Sinflar' yoki '.as-menu-item-label' kabi elementni tezkor bosish
                await page.click(".as-menu-item-label", timeout=3000)
            except:
                await page.click("text=Sinflar", timeout=2000) rescue None

            # 2. Guruhni topish va tanlash (JS orqali tezroq)
            # Ro'yxat paydo bo'lishi bilan uning ichidan guruhni topamiz
            try:
                # Guruhni matn bo'yicha qidirib, darhol click qilamiz
                await page.wait_for_selector(f"text={group_name}", timeout=3000)
                await page.click(f"text={group_name}")
                print(f"[Timetable] Group {group_name} clicked.")
            except:
                # Agar ro'yxatda topilmasa, qidiruv (typing) qilib ko'ramiz
                await page.keyboard.type(group_name)
                await page.keyboard.press("Enter")

            # 3. Jadval yuklanishini kutish (element paydo bo'lguncha)
            try:
                await page.wait_for_selector("div.print-nobreak, .timetable", timeout=4000)
            except:
                pass # Agar chiqmasa, fallback screenshotga o'tadi

            # Animatsiya tugashi uchun juda qisqa kutish
            await page.wait_for_timeout(300)
            
            # Screenshot olish
            target = await page.query_selector("div.print-nobreak") or await page.query_selector(".timetable")
            if target:
                await target.screenshot(path=output_path)
                print(f"[Timetable] Fast click screenshot done for {group_name}")
            else:
                await page.screenshot(path=output_path)
                print("[Timetable] Full page fallback")

            await browser.close()
            return output_path

    except Exception as e:
        print(f"[Timetable] Error for {group_name}: {e}")
        return None
