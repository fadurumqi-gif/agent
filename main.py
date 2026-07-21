import os
import requests
import feedparser
import html
from datetime import datetime

# Только самые надежные RSS-источники
RSS_FEEDS = {
    "oil_gas": [
        "https://www.neftegaz.ru/rss/news.xml",
        "https://tass.ru/rss/v2.xml?theme=10"
    ],
    "oil_prices": [
        "https://www.oilprice.com/rss/main"
    ],
    "chemistry": [
        "https://www.himinfo.ru/rss/",
        "https://www.sibur.ru/press/news/rss/"
    ]
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_latest_news():
    """Собирает новости с таймаутом"""
    all_news = {
        "oil_gas": [],
        "oil_prices": [],
        "chemistry": []
    }
    
    for category, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                # Добавляем таймаут 10 секунд
                response = requests.get(url, timeout=10)
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:3]:
                    title = entry.get('title', 'Без заголовка')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    safe_title = html.escape(title)
                    all_news[category].append(f"• <b>{safe_title}</b>\n   {published}\n  🔗 <a href='{link}'>Источник</a>")
            except Exception as e:
                print(f"⚠️ Пропуск {url}: {e}")
                continue
    
    return all_news

def get_free_model_from_openrouter():
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            free_models = [m["id"] for m in models if m.get("id", "").endswith(":free")]
            if free_models:
                for preferred in ["meta-llama/llama-3-8b-instruct:free", "mistralai/mistral-7b-instruct:free"]:
                    if preferred in free_models:
                        return preferred
                return free_models[0]
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
    return "meta-llama/llama-3-8b-instruct:free"

def summarize_with_ai(all_news):
    if not OPENROUTER_API_KEY:
        return "⚠️ Ошибка: Ключ OPENROUTER_API_KEY не найден."
    
    model_id = get_free_model_from_openrouter()
    print(f"🤖 Используем модель: {model_id}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "OilGas Weekly Bot"
    }
    
    oil_gas_news = "\n".join(all_news["oil_gas"]) if all_news["oil_gas"] else "Новости не найдены."
    oil_prices_news = "\n".join(all_news["oil_prices"]) if all_news["oil_prices"] else "Данные о ценах не найдены."
    chemistry_news = "\n".join(all_news["chemistry"]) if all_news["chemistry"] else "Новости о проектах не найдены."
    
    prompt = f"""Ты — профессиональный аналитик нефтегазовой и химической отрасли России. 
Сделай краткую, структурированную еженедельную сводку на русском языке.

Включи разделы:
1) 📊 ЦЕНЫ НА НЕФТЬ (Brent, WTI, Urals, динамика)
2) 🛢 ГЛАВНЫЕ СОБЫТИЯ В НЕФТЕГАЗЕ РФ
3) 🏭 НОВЫЕ ПРОЕКТЫ В ХИМИИ, УДОБРЕНИЯХ, ПЕРЕРАБОТКЕ
4) 🔮 ПРОГНОЗ И ПЕРСПЕКТИВЫ

Используй эмодзи и переносы строк. НЕ используй HTML-теги.

=== НЕФТЕГАЗ ===
{oil_gas_news}

=== ЦЕНЫ НА НЕФТЬ ===
{oil_prices_news}

=== ХИМИЯ И УДОБРЕНИЯ ===
{chemistry_news}"""

    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=45)
    
    if resp.status_code == 200:
        try:
            content = resp.json()["choices"][0]["message"]["content"]
            if "<!doctype" in content.lower() or "<html" in content.lower():
                return "️ ИИ вернул некорректный формат."
            return content
        except Exception:
            return "⚠️ Не удалось прочитать ответ ИИ."
    else:
        return f"️ Сервис ИИ недоступен (ошибка {resp.status_code})."

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
    all_news = get_latest_news()
    
    print(f"📰 Собрано: Нефтегаз={len(all_news['oil_gas'])}, Цены={len(all_news['oil_prices'])}, Химия={len(all_news['chemistry'])}")
    
    print("🤖 Генерация сводки...")
    summary = summarize_with_ai(all_news)
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 <b>Еженедельная сводка: Нефтегаз, Химия, Цены</b>\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
