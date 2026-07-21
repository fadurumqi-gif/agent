import os
import requests
import feedparser
import html
from datetime import datetime

# Расширенные RSS-ленты
RSS_FEEDS = {
    # Нефтегазовые новости
    "oil_gas": [
        "https://www.neftegaz.ru/rss/news.xml",
        "https://tass.ru/rss/v2.xml?theme=10",
        "https://www.rosneft.ru/press/news/rss/",
        "https://www.gazprom.ru/press/news/rss/",
        "https://www.lukoil.ru/press/news/rss/"
            ],
    # Цены на нефть
    "oil_prices": [
        "https://www.oilprice.com/rss/main",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F",
        "https://www.investing.com/rss/news_301.rss"
    ],
    # Химия и удобрения
    "chemistry": [
        "https://www.himinfo.ru/rss/",
        "https://www.uniprom.ru/press/news/rss/",
        "https://www.sibur.ru/press/news/rss/",
        "https://www.phosagro.ru/press/news/rss/"
        "https://www.surgutneftegas.ru/press/news/rss/",  # Сургутнефтегаз
"https://www.tatneft.ru/press/news/rss/",  # Татнефть
"https://www.eurochem.ru/press/news/rss/",  # ЕвроХим (удобрения)
    ]
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_latest_news():
    """Собирает новости из всех категорий"""
    all_news = {
        "oil_gas": [],
        "oil_prices": [],
        "chemistry": []
    }
    
    for category, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:  # По 3 новости из каждого источника
                    title = entry.get('title', 'Без заголовка')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    safe_title = html.escape(title)
                    all_news[category].append(f"• <b>{safe_title}</b>\n  📅 {published}\n  🔗 <a href='{link}'>Источник</a>")
            except Exception as e:
                print(f"Ошибка чтения {url}: {e}")
    
    return all_news

def get_free_model_from_openrouter():
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            free_models = [m["id"] for m in models if m.get("id", "").endswith(":free")]
            if free_models:
                for preferred in ["meta-llama/llama-3-8b-instruct:free", "mistralai/mistral-7b-instruct:free", "google/gemma-2-9b-it:free"]:
                    if preferred in free_models:
                        return preferred
                return free_models[0]
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
    return "meta-llama/llama-3-8b-instruct:free"

def summarize_with_ai(all_news):
    if not OPENROUTER_API_KEY:
        return "⚠️ Ошибка: Ключ OPENROUTER_API_KEY не найден в настройках GitHub."
    
    model_id = get_free_model_from_openrouter()
    print(f"🤖 Используем модель: {model_id}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "OilGas Weekly Bot"
    }
    
    # Формируем расширенный промпт
    oil_gas_news = "\n\n".join(all_news["oil_gas"]) if all_news["oil_gas"] else "Новости не найдены."
    oil_prices_news = "\n\n".join(all_news["oil_prices"]) if all_news["oil_prices"] else "Данные о ценах не найдены."
    chemistry_news = "\n\n".join(all_news["chemistry"]) if all_news["chemistry"] else "Новости о проектах не найдены."
    
    prompt = f"""Ты — профессиональный аналитик нефтегазовой и химической отрасли России. 
Сделай подробную, структурированную еженедельную сводку на русском языке.

ОБЯЗАТЕЛЬНО включи следующие разделы:

1) 📊 АНАЛИЗ ЦЕН НА НЕФТЬ
   - Текущие цены на Brent, WTI, Urals
   - Динамика за неделю (рост/падение в %)
   - Основные факторы, влияющие на цены

2) 🛢 ГЛАВНЫЕ СОБЫТИЯ В НЕФТЕГАЗОВОЙ ОТРАСЛИ РФ
   - Ключевые новости компаний (Роснефть, Газпром, Лукойл и др.)
   - Влияние на рынок и перспективы

3)  НОВЫЕ ПРОЕКТЫ В ХИМИИ, УДОБРЕНИЯХ, НЕФТЕ- И ГАЗОПЕРЕРАБОТКЕ
   - Запуск новых производств
   - Инвестиционные проекты
   - Модернизация существующих мощностей
   - Перспективы развития отрасли

4) 🔮 ПРОГНОЗ И ПЕРСПЕКТИВЫ
   - Ожидания на следующую неделю
   - Ключевые риски и возможности

Используй эмодзи и переносы строк для удобства чтения. НЕ используй HTML-теги.

=== НОВОСТИ НЕФТЕГАЗОВОЙ ОТРАСЛИ ===
{oil_gas_news}

=== ЦЕНЫ НА НЕФТЬ ===
{oil_prices_news}

=== ХИМИЯ, УДОБРЕНИЯ, ПЕРЕРАБОТКА ===
{chemistry_news}"""

    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=60)  # Увеличен таймаут для большого промпта
    
    if resp.status_code == 200:
        try:
            content = resp.json()["choices"][0]["message"]["content"]
            if "<!doctype" in content.lower() or "<html" in content.lower():
                return "⚠️ ИИ вернул некорректный формат данных. Повторите попытку позже."
            return content
        except Exception:
            return "⚠️ Не удалось прочитать ответ ИИ."
    else:
        return f"⚠️ Сервис ИИ временно недоступен (ошибка {resp.status_code}). Попробуйте запустить вручную позже."

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
    print("📡 Сбор новостей из всех источников...")
    all_news = get_latest_news()
    
    print(f"📰 Собрано новостей:")
    print(f"   - Нефтегаз: {len(all_news['oil_gas'])}")
    print(f"   - Цены на нефть: {len(all_news['oil_prices'])}")
    print(f"   - Химия/удобрения: {len(all_news['chemistry'])}")
    
    print("🤖 Генерация расширенной сводки через OpenRouter AI...")
    summary = summarize_with_ai(all_news)
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 <b>Еженедельная сводка: Нефтегаз, Химия, Цены на нефть</b>\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
