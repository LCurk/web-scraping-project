import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def extract_star_rating(container):
    """
    Count yellow SVG stars inside a review or testimonial element.
    """
    try:
        stars = container.find_elements(
            By.XPATH,
            ".//*[local-name()='path' and @fill='#ffce31']"
        )
        return min(len(stars), 5)
    except Exception:
        return 0


def init_browser():
    """
    Initialize Chrome WebDriver using webdriver-manager.
    """
    print("🔧 Initializing Chrome WebDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    return driver


def collect_products(driver):
    """
    Scrape product titles and prices from paginated product pages.
    """
    print("\n📦 Collecting PRODUCTS...")
    products = []
    page_index = 1

    while True:
        driver.get(f"https://web-scraping.dev/products?page={page_index}")
        time.sleep(1)

        product_cards = driver.find_elements(
            By.CSS_SELECTOR,
            "div.product-item, div[class*='product']"
        )

        if not product_cards:
            break

        newly_added = 0

        for card in product_cards:
            try:
                raw_text = card.text.strip()
                lines = raw_text.split("\n")
                title = lines[0]

                price_match = re.search(r'[$€£]?\s*\d+\.\d{2}', raw_text)
                price = price_match.group(0) if price_match else "N/A"

                if title and title.lower() != "log in":
                    if not any(p["title"] == title for p in products):
                        products.append({
                            "title": title,
                            "price": price
                        })
                        newly_added += 1
            except Exception:
                continue

        print(f"   Page {page_index}: +{newly_added}")
        if newly_added == 0:
            break

        page_index += 1

    return products


def collect_reviews(driver):
    """
    Scrape reviews dynamically loaded via 'Load more' button.
    Stops once reviews older than 2023 are reached.
    """
    print("\n⭐ Collecting REVIEWS (2023 and newer)...")
    reviews_data = []

    driver.get("https://web-scraping.dev/reviews")
    wait = WebDriverWait(driver, 10)
    time.sleep(2)

    reached_old_reviews = False

    while not reached_old_reviews:
        review_blocks = driver.find_elements(By.CLASS_NAME, "review")

        for block in review_blocks:
            try:
                lines = block.text.strip().split("\n")

                review_date = None
                review_year = None

                for line in lines:
                    year_match = re.search(r"(20\d{2})", line)
                    if year_match:
                        review_year = int(year_match.group(1))
                        review_date = line
                        break

                if not review_date:
                    continue

                if review_year < 2023:
                    print(f"   ⛔ Encountered review from {review_year}. Stopping.")
                    reached_old_reviews = True
                    break

                review_text = max(lines, key=len)
                rating = extract_star_rating(block) or 5

                if not any(r["text"] == review_text for r in reviews_data):
                    reviews_data.append({
                        "date": review_date,
                        "text": review_text,
                        "rating": rating
                    })

            except Exception:
                continue

        if reached_old_reviews:
            break

        # Scroll and trigger "Load more"
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        try:
            load_more = driver.find_element(By.ID, "page-load-more")
            if not load_more.is_displayed():
                break

            count_before = len(review_blocks)
            driver.execute_script("arguments[0].click();", load_more)

            wait.until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "review")) > count_before
            )
            time.sleep(1)

        except Exception:
            break

    print(f"   ✅ Total reviews collected: {len(reviews_data)}")
    return reviews_data


def collect_testimonials(driver):
    """
    Scrape testimonial cards using infinite scroll.
    """
    print("\n💬 Collecting TESTIMONIALS...")
    testimonials = []

    driver.get("https://web-scraping.dev/testimonials")
    time.sleep(2)

    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    cards = driver.find_elements(By.CSS_SELECTOR, "div[class*='testimonial']")

    for card in cards:
        try:
            text = card.text.replace("\n", " ").strip()

            if (
                "Take a look" in text
                or "collection" in text
                or len(text) < 10
                or len(text) > 400
            ):
                continue

            if not any(t["text"] == text for t in testimonials):
                testimonials.append({
                    "text": text,
                    "rating": extract_star_rating(card) or 5
                })

        except Exception:
            continue

    print(f"   ✅ Total testimonials collected: {len(testimonials)}")
    return testimonials


def run_scraper():
    """
    Main execution flow.
    """
    driver = init_browser()

    try:
        results = {
            "products": collect_products(driver),
            "reviews": collect_reviews(driver),
            "testimonials": collect_testimonials(driver)
        }

    finally:
        driver.quit()

    with open("scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("\n✅ SCRAPING FINISHED")
    print(f"📦 Products: {len(results['products'])}")
    print(f"⭐ Reviews (2023+): {len(results['reviews'])}")
    print(f"💬 Testimonials: {len(results['testimonials'])}")


if __name__ == "__main__":
    run_scraper()
