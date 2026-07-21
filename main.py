import os
import requests
import feedparser
import html
from datetime import datetime

RSS_FEEDS = [
    "https://www.neftegaz.ru/rss/news.xml",
    "https://tass.ru/rss/v2.xml?theme=10",
    "https://www.rosneft.ru/press/news/rss/"
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_latest_news():
    news_items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.get('title', 'Без заголовка')
                link = entry.get('link', '')
                published = entry.get('published', '')
                # Экранируем HTML-символы для безопасности
                safe_title = html.escape(title)
                news_items.append(f"• <b>{safe_title}</b>\n  📅 {published}\n  🔗 <a href='{link}'>Источник</a>")
        except Exception as e:
            print(f"Ошибка чтения {url}: {e}")
    return "\n\n".join(news_items) if news_items else "Новости не найдены."

def summarize_with_ai(raw_news):
    if not OPENROUTER_API_KEY:
        return "⚠️ Ошибка: Ключ OPENROUTER_API_KEY не найден в настройках GitHub."
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "OilGas Weekly Bot"
    }
    
    prompt = f"""Ты — профессиональный аналитик нефтегазовой отрасли России. 
Сделай краткую, структурированную еженедельную сводку на русском языке.
Обязательно выдели: 
1) 📌 Главные события
2) 📈 Влияние на рынок и цены  
3) 🔮 Перспективы отрасли
Используй эмодзи и теги HTML (<b>жирный</b>, <i>курсив</i>) для удобства чтения.

Новости для анализа:
{raw_news}"""

    # Список бесплатных моделей для подстраховки
    models_to_try = [
        "meta-llama/llama-3-8b-instruct:free",
        "qwen/qwen-2.5-7b-instruct:free"
    "google/gemma-2-9b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free"
    ]    
    for model in models_to_try:
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        resp = requests.post(url, headers=headers, json=data)
        
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
            
    # Если ни одна модель не сработала, возвращаем безопасное сообщение
    return f"⚠️ Сервис ИИ недоступен. Последняя ошибка: {resp.status_code} - {resp.text}"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML", # HTML намного стабильнее Markdown для ИИ-текстов
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
    
    print("🤖 Генерация сводки через OpenRouter AI...")
    summary = summarize_with_ai(raw_news)
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 <b>Еженедельная сводка нефтегазовой отрасли РФ</b>\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
