import os
import requests
import feedparser
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
# RSS-ленты новостей нефтегазовой отрасли РФ
RSS_FEEDS = [
    "https://www.neftegaz.ru/rss/news.xml",
    "https://tass.ru/rss/v2.xml?theme=10" # Экономика, включает нефтегаз
]

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032" # Ваш ID

def get_latest_news():
    """Собирает последние новости из RSS-лент"""
    news_items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: # Берем по 3 последние новости из каждого источника
                title = entry.get('title', 'Без заголовка')
                link = entry.get('link', '')
                published = entry.get('published', '')
                news_items.append(f"• {title}\n  Дата: {published}\n  Ссылка: {link}")
        except Exception as e:
            print(f"Ошибка при чтении {url}: {e}")
    
    return "\n\n".join(news_items) if news_items else "Новости не найдены."

def summarize_with_ai(raw_news):
    """Отправляет новости в OpenRouter для суммаризации"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com", # Обязательно для OpenRouter
        "X-Title": "OilGas Weekly Summary Bot"
    }
    
    prompt = f"""Ты — профессиональный аналитик нефтегазовой отрасли России. 
Сделай краткую, структурированную еженедельную сводку на русском языке на основе следующих новостей. 
Выдели: 1) Главные события, 2) Влияние на рынок, 3) Перспективы. 
Используй эмодзи для читаемости и форматирование Markdown.

Новости для анализа:
{raw_news}"""

    data = {
        # Используем БЕСПЛАТНУЮ модель OpenRouter (обязательно с суффиксом :free)
        "model": "meta-llama/llama-3-8b-instruct:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def send_to_telegram(message):
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Сообщение успешно отправлено в Telegram!")
    else:
        print(f"Ошибка Telegram: {response.text}")

if __name__ == "__main__":
    print("Сбор новостей...")
    raw_news = get_latest_news()
    
    print("Генерация сводки через ИИ...")
    summary = summarize_with_ai(raw_news)
    
    # Добавляем заголовок с датой
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 **Еженедельная сводка нефтегазовой отрасли РФ**\n📅 {today}\n\n{summary}"
    
    print("Отправка в Telegram...")
    send_to_telegram(final_message)
