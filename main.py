import os
import requests
import feedparser
import google.generativeai as genai
from datetime import datetime

RSS_FEEDS = [
    "https://www.neftegaz.ru/rss/news.xml",
    "https://tass.ru/rss/v2.xml?theme=10",
    "https://www.rosneft.ru/press/news/rss/"
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_latest_news():
    news_items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.get('title', 'Без заголовка')
                link = entry.get('link', '')
                published = entry.get('published', '')
                news_items.append(f"• {title}\n   {published}\n  🔗 {link}")
        except Exception as e:
            print(f"Ошибка чтения {url}: {e}")
    return "\n\n".join(news_items) if news_items else "Новости не найдены."

def summarize_with_gemini(raw_news):
    if not GEMINI_API_KEY:
        raise ValueError("Секрет GEMINI_API_KEY не найден!")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Ты — профессиональный аналитик нефтегазовой отрасли России. 
Сделай краткую, структурированную еженедельную сводку на русском языке.
Обязательно выдели: 
1) 📌 Главные события
2) 📈 Влияние на рынок и цены  
3) 🔮 Перспективы отрасли
Используй эмодзи и форматирование Markdown.

Новости для анализа:
{raw_news}"""

    response = model.generate_content(prompt)
    return response.text

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload)
    if resp.status_code == 200:
        print("✅ Успешно отправлено в Telegram!")
    else:
        print(f"❌ Ошибка Telegram: {resp.text}")

if __name__ == "__main__":
    print("📡 Сбор новостей...")
    raw_news = get_latest_news()
    
    print("🤖 Генерация сводки через Google Gemini AI...")
    try:
        summary = summarize_with_gemini(raw_news)
    except Exception as e:
        print(f"⚠️ Ошибка ИИ: {e}")
        summary = f"⚠️ Не удалось сгенерировать сводку.\nДетали: {e}"
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 **Еженедельная сводка нефтегазовой отрасли РФ**\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
