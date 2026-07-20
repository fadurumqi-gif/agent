import os
import requests
import feedparser
import uuid
import urllib3
from datetime import datetime

# Отключаем предупреждения о сертификатах (для GigaChat)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RSS_FEEDS = [
    "https://www.neftegaz.ru/rss/news.xml",
    "https://tass.ru/rss/v2.xml?theme=10",
    "https://www.rosneft.ru/press/news/rss/"
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
# По умолчанию используем openrouter, если не указано иное
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter").lower()

def get_latest_news():
    news_items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.get('title', 'Без заголовка')
                link = entry.get('link', '')
                published = entry.get('published', '')
                news_items.append(f"• {title}\n  📅 {published}\n  🔗 {link}")
        except Exception as e:
            print(f"Ошибка чтения {url}: {e}")
    return "\n\n".join(news_items) if news_items else "Новости не найдены."

def summarize_openrouter(raw_news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Ключ OPENROUTER_API_KEY не найден в секретах GitHub!")
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "OilGas Weekly Bot"
    }
    prompt = f"Ты — ведущий аналитик нефтегазовой отрасли России. Сделай краткую, структурированную еженедельную сводку на русском языке. Выдели: 1) Главные события, 2) Влияние на рынок/цены, 3) Перспективы. Используй эмодзи и Markdown.\n\nНовости:\n{raw_news}"
    
    data = {
        "model": "google/gemma-2-9b-it:free", # Бесплатная модель
        "messages": [{"role": "user", "content": prompt}]
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status() # Здесь была ошибка 401, теперь мы точно узнаем почему
    return resp.json()["choices"][0]["message"]["content"]

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
    
    print(f"🤖 Генерация сводки через {LLM_PROVIDER.upper()}...")
    
    try:
        summary = summarize_openrouter(raw_news)
    except Exception as e:
        print(f"⚠️ Ошибка ИИ: {e}")
        summary = "⚠️ Не удалось сгенерировать сводку. Проверьте логи GitHub Actions."
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 **Еженедельная сводка нефтегазовой отрасли РФ**\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
