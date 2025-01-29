import time
import sqlite3
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Телеграм токен і ID каналу
TOKEN = "7589363266:AAFSTX6Jl1twanxeIvwgmMgnFMDlCu6hPNY"
CHANNEL_ID = "@weatherlviv1256_bot"

# Ініціалізація бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Функція для парсингу рецептів
def scrape_cookpad():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    url = "https://cookpad.com/ua/search/%D0%BE%D0%B1%D1%96%D0%B4"
    driver.get(url)
    time.sleep(5)
    
    recipes = driver.find_elements(By.CLASS_NAME, "basic-recipe-list-item")
    data = []
    
    for recipe in recipes[:5]:  # Беремо лише 5 рецептів
        try:
            title = recipe.find_element(By.CLASS_NAME, "basic-recipe-list-item__title").text
            link = recipe.find_element(By.TAG_NAME, "a").get_attribute("href")
            image = recipe.find_element(By.TAG_NAME, "img").get_attribute("src")
            data.append((title, link, image))
        except:
            continue
    
    driver.quit()
    return data

# Функція для збереження в базу даних
def save_to_db(recipes):
    conn = sqlite3.connect("recipes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            image TEXT,
            posted INTEGER DEFAULT 0
        )
    """)
    
    for title, link, image in recipes:
        cursor.execute("SELECT * FROM recipes WHERE link = ?", (link,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO recipes (title, link, image) VALUES (?, ?, ?)", (title, link, image))
    
    conn.commit()
    conn.close()

# Функція для отримання неопублікованого рецепта
def get_unposted_recipe():
    conn = sqlite3.connect("recipes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE posted = 0 ORDER BY RANDOM() LIMIT 1")
    recipe = cursor.fetchone()
    conn.close()
    return recipe

# Функція для відправки повідомлення в канал
async def post_recipe():
    recipe = get_unposted_recipe()
    if recipe:
        recipe_id, title, link, image, _ = recipe
        text = f"🍽 *{title}*\n🔗 [Дивитися рецепт]({link})"
        
        await bot.send_photo(CHANNEL_ID, photo=image, caption=text, parse_mode="Markdown")
        
        conn = sqlite3.connect("recipes.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE recipes SET posted = 1 WHERE id = ?", (recipe_id,))
        conn.commit()
        conn.close()

# Запускаємо парсинг і плануємо постинг
def main():
    recipes = scrape_cookpad()
    save_to_db(recipes)
    scheduler.add_job(post_recipe, "interval", hours=6)  # Постимо кожні 6 годин
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    main()
