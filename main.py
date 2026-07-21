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
                safe_title = html.escape(title)
                news_items.append(f"• <b>{safe_title}</b>\n  📅 {published}\n  🔗 <a href='{link}'>Источник</a>")
        except Exception as e:
            print(f"Ошибка чтения {url}: {e}")
    return "\n\n".join(news_items) if news_items else "Новости не найдены."

def get_free_model_from_openrouter():
    """Динамически получает актуальную бесплатную модель от OpenRouter"""
    try:
        # Запрашиваем список всех моделей (это не требует ключа)
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            # Фильтруем только те, что имеют суффикс :free
            free_models = [m["id"] for m in models if m.get("id", "").endswith(":free")]
            
            if free_models:
                # Отдаем приоритет самым стабильным и "умным" бесплатным моделям
                for preferred in ["meta-llama/llama-3-8b-instruct:free", "mistralai/mistral-7b-instruct:free", "google/gemma-2-9b-it:free"]:
                    if preferred in free_models:
                        return preferred
                # Если ни одной из предпочтительных нет, берем первую попавшуюся бесплатную
                return free_models[0]
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
    
    # Фолбэк на самую известную модель, если список получить не удалось
    return "meta-llama/llama-3-8b-instruct:free"

def summarize_with_ai(raw_news):
    if not OPENROUTER_API_KEY:
        return "⚠️ Ошибка: Ключ OPENROUTER_API_KEY не найден в настройках GitHub."
    
    # Получаем актуальную модель
    model_id = get_free_model_from_openrouter()
    print(f"🤖 Используем модель: {model_id}")
    
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

    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        return f"⚠️ Сервис ИИ недоступен. Модель: {model_id}. Ошибка: {resp.status_code} - {resp.text}"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
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
