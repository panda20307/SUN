%pip install playwright google-genai python-dotenv
!playwright install chromium
import os
import asyncio

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from playwright.async_api import async_playwright


# --------------------------------------------------
# 1. GEMINI API CONFIGURATION
# --------------------------------------------------

API_KEY = "AQ.Ab8RN6J2mDiTmVIN9klxOnezs4ZKOZ60ShuPaEaq9US-Cg3LYQ"

if not API_KEY:
    raise ValueError(
        "Gemini API key not found. Set GEMINI_API_KEY first."
    )

client = genai.Client(api_key=API_KEY)


# --------------------------------------------------
# 2. START CHROME BROWSER
# --------------------------------------------------

playwright = await async_playwright().start()

browser = await playwright.chromium.launch(
    headless=False
)

page = await browser.new_page()

print("[CHROME] Browser started successfully!")


# --------------------------------------------------
# 3. AMAZON TOOLS
# --------------------------------------------------

async def open_amazon() -> str:
    """Opens Amazon India in Chrome."""

    print("  [CHROME] Opening amazon.in...")

    await page.goto(
        "https://www.amazon.in",
        wait_until="domcontentloaded",
        timeout=60000
    )

    return "Amazon India homepage is open."


async def search_product(keyword: str) -> str:
    """Searches for a product on Amazon India."""

    print(f"  [CHROME] Searching for: {keyword}")

    await page.wait_for_selector(
        "#twotabsearchtextbox",
        timeout=20000
    )

    await page.fill(
        "#twotabsearchtextbox",
        keyword
    )

    await page.click("#nav-search-submit-button")

    await page.wait_for_selector(
        "[data-component-type='s-search-result']",
        timeout=20000
    )

    return f"Search results loaded for '{keyword}'."


async def get_top_products(limit: int = 5) -> str:
    """Extracts product titles and prices."""

    print(f"  [CHROME] Reading top {limit} products...")

    cards = await page.locator(
        "[data-component-type='s-search-result']"
    ).all()

    results = []

    for card in cards:

        if len(results) >= limit:
            break

        title_loc = card.locator("h2 span").first

        price_loc = card.locator(
            ".a-price .a-offscreen"
        ).first

        title = (
            await title_loc.inner_text()
            if await title_loc.count() > 0
            else "No title"
        )

        price = (
            await price_loc.inner_text()
            if await price_loc.count() > 0
            else "Price unavailable"
        )

        results.append(
            f"{len(results)+1}. {title.strip()} | {price.strip()}"
        )

    if not results:
        return "No products found. Check whether Amazon displayed a CAPTCHA."

    return "\n".join(results)


# --------------------------------------------------
# 4. REGISTER AGENT TOOLS
# --------------------------------------------------

tools = [
    open_amazon,
    search_product,
    get_top_products
]


# --------------------------------------------------
# 5. AGENT GOAL
# --------------------------------------------------

goal = """
You are an intelligent shopping assistant.

Perform the following tasks:

1. Open Amazon India.
2. Search for 'wireless mouse under 1000'.
3. Extract the top 5 products and their prices.
4. Compare all available products.
5. Recommend the best value-for-money product.

Consider:
- Price
- Product name
- Features if visible
- Value for money

Only recommend products present in the extracted results.

Clearly mention the product name, price and reason
for recommending it.
"""


# --------------------------------------------------
# 6. GEMINI MODEL FALLBACK
# --------------------------------------------------

models_to_try = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]

success = False

for model_name in models_to_try:

    try:

        print(f"\nTrying Gemini model: {model_name}")

        chat = client.aio.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.0
            )
        )

        response = await chat.send_message(goal)

        print(
            f"\nAgent Recommendation (via {model_name}):\n"
        )

        print(response.text)

        success = True
        break

    except ClientError as e:

        print(f"\n[!] Client error: {e}")

        # Invalid API key: no point trying other models.
        if e.code == 400:
            print(
                "\nAPI key is invalid or the request is incorrect."
                "\nCheck your Gemini API key."
            )
            break

        # Rate limit: try another model.
        elif e.code == 429:
            print("Rate limit reached. Trying fallback model...")
            continue

        else:
            print("Request failed. Trying fallback model...")
            continue

    except ServerError as e:

        print(
            f"\n[!] {model_name} server error ({e.code})."
        )

        print("Switching to fallback model...")

        continue

    except Exception as e:

        print(f"\n[!] Unexpected error: {type(e).__name__}: {e}")

        break


if not success:
    print("\n[!] All attempts failed. Check the error messages above.")


# --------------------------------------------------
# 7. CLEANUP (RUN WHEN FINISHED)
# --------------------------------------------------

# Uncomment these lines when you want to close Chrome.

# await browser.close()
# await playwright.stop()
from google.genai.errors import ServerError

async def open_amazon() -> str:
    """Opens Amazon India (amazon.in) in the Chrome browser."""
    print("  [CHROME] Opening amazon.in...")
    await page.goto("https://www.amazon.in", wait_until="domcontentloaded")
    return "Amazon India homepage is open."

async def search_product(keyword: str) -> str:
    """Searches for a product keyword on Amazon India."""
    print(f"  [CHROME] Searching Amazon.in for: '{keyword}'")
    await page.wait_for_selector("#twotabsearchtextbox", timeout=10000)
    await page.fill("#twotabsearchtextbox", keyword)
    await page.click("#nav-search-submit-button")
    await page.wait_for_selector("[data-component-type='s-search-result']", timeout=10000)
    return f"Search results loaded for '{keyword}'."

async def get_top_products(limit: int = 5) -> str:
    """Extracts the titles and prices of the top search results on Amazon India."""
    print(f"  [CHROME] Reading top {limit} products...")
    cards = await page.locator("[data-component-type='s-search-result']").all()
    results = []

    for card in cards[:limit]:
        title_loc = card.locator("h2 span").first
        price_loc = card.locator(".a-price .a-offscreen").first
        
        title = (await title_loc.inner_text()).strip() if await title_loc.count() > 0 else "No title"
        price = (await price_loc.inner_text()).strip() if await price_loc.count() > 0 else "Price unavailable"
        results.append(f"- {title} | {price}")

    return "\n".join(results)

tools = [open_amazon, search_product, get_top_products]

goal = """
Open Amazon India, search for 'wireless mouse under 1000', 
check the top 5 products, and recommend the best value option from the list.
"""

# Fallback list so a 503 spike never stalls your live class
models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

for model_name in models_to_try:
    try:
        print(f"Trying {model_name}...")
        chat = client.aio.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(tools=tools, temperature=0.0)
        )
        response = await chat.send_message(goal)
        print(f"\nAgent Recommendation (via {model_name}):\n", response.text)
        break
    except ServerError as e:
        print(f"  [!] {model_name} busy ({e.code}), switching to fallback...")
