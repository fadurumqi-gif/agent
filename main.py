import os
import requests
import feedparser
import uuid
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RSS_FEEDS = [
    "https://www.neftegaz.ru/rss/news.xml",
    "https://tass.ru/rss/v2.xml?theme=10",
    "https://www.rosneft.ru/press/news/rss/"
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "5734651032"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gigachat").lower()

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

def summarize_gigachat(raw_news):
    api_key = os.environ.get("GIGACHAT_API_KEY")
    if not api_key:
        raise ValueError("Ключ GIGACHAT_API_KEY не найден!")
    
    # Шаг 1: Получаем токен доступа
    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    token_resp = requests.post(auth_url, headers=headers, data={"scope": "GIGACHAT_API_PERS"}, verify=False)
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    # Шаг 2: Запрашиваем суммаризацию
    chat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    chat_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    prompt = f"Ты — ведущий аналитик нефтегазовой отрасли России. Сделай краткую, структурированную еженедельную сводку на русском языке. Выдели: 1) Главные события, 2) Влияние на рынок/цены, 3) Перспективы. Используй эмодзи и Markdown.\n\nНовости:\n{raw_news}"
    
    data = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    resp = requests.post(chat_url, headers=chat_headers, json=data, verify=False)
    resp.raise_for_status()
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
        if LLM_PROVIDER == "gigachat":
            summary = summarize_gigachat(raw_news)
        else:
            summary = "⚠️ OpenRouter временно недоступен"
    except Exception as e:
        print(f"⚠️ Ошибка ИИ: {e}")
        summary = "⚠️ Не удалось сгенерировать сводку. Проверьте логи GitHub Actions."
    
    today = datetime.now().strftime("%d.%m.%Y")
    final_message = f"🛢 **Еженедельная сводка нефтегазовой отрасли РФ**\n📅 {today}\n\n{summary}"
    
    print("📤 Отправка в Telegram...")
    send_to_telegram(final_message)
