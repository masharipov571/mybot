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

            print(f"[Timetable] Opening TSUE timetable for group: {group_name}")
            await page.goto("https://tsue.edupage.org/timetable/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=20000)

            # Sahifani o'zbek tiliga o'tkazish (agar kerak bo'lsa)
            try:
                await page.select_option("select[name='lang']", "uz")
                await page.wait_for_timeout(1000)
            except Exception:
                pass  # Til tanlash bo'lmasa ham davom etamiz

            # Guruh qidirish maydonini topish
            # Sayt turli xil selector ishlatishi mumkin
            group_selectors = [
                "input[placeholder*='guruh']",
                "input[placeholder*='group']",
                "input[placeholder*='Guruh']",
                ".search-input",
                "input[type='search']",
                "input[type='text']"
            ]

            input_found = False
            for selector in group_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await page.fill(selector, group_name)
                    await page.wait_for_timeout(500)
                    await page.press(selector, "Enter")
                    input_found = True
                    print(f"[Timetable] Used selector: {selector}")
                    break
                except Exception:
                    continue

            if not input_found:
                # URL orqali urinib ko'rish
                encoded = group_name.replace("/", "%2F").replace(" ", "+")
                await page.goto(
                    f"https://tsue.edupage.org/timetable/?group={encoded}",
                    timeout=15000
                )

            await page.wait_for_timeout(3000)

            # Jadval elementini crop qilish
            timetable_selectors = [
                ".timetable",
                "#timetable",
                ".schedule",
                ".week-timetable",
                "table.main",
                "main"
            ]

            screenshot_taken = False
            for sel in timetable_selectors:
                try:
                    element = await page.query_selector(sel)
                    if element:
                        await element.screenshot(path=output_path)
                        screenshot_taken = True
                        print(f"[Timetable] Screenshot taken for: {group_name}")
                        break
                except Exception:
                    continue

            if not screenshot_taken:
                # Butun sahifani screenshot qilish
                await page.screenshot(path=output_path, full_page=False)
                print(f"[Timetable] Full page screenshot for: {group_name}")

            await browser.close()
            return output_path

    except Exception as e:
        print(f"[Timetable] Error for {group_name}: {e}")
        return None
