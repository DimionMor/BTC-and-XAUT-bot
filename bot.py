"""
BTC & XAUT Daily Report Bot
-----------------------------
Каждый день в 10:00 (МСК) отправляет отчёт по BTC и XAUT:
  - Текущая цена
  - Изменение за день и за неделю
  - Прогнозы: краткосрочный / среднесрочный / долгосрочный
 
Хостинг: Railway
Переменные окружения (задать в Railway):
  TELEGRAM_TOKEN     — токен бота от @BotFather
  ANTHROPIC_API_KEY  — ключ Anthropic
  CHAT_ID            — твой Telegram chat_id (получить через @userinfobot)
"""
 
import os
import asyncio
import logging
from datetime import time
 
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
 
# ── Логирование ───────────────────────────────────────────────────────────────
 
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
 
# ── Конфиг ────────────────────────────────────────────────────────────────────
 
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CHAT_ID           = int(os.environ["CHAT_ID"])
 
# 10:00 МСК = 07:00 UTC
DAILY_HOUR   = 7
DAILY_MINUTE = 0
 
# ── Клиент Anthropic ──────────────────────────────────────────────────────────
 
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
 
# ── Промпт ────────────────────────────────────────────────────────────────────
 
SYSTEM_PROMPT = """Ты — опытный криптовалютный и финансовый аналитик. Составь ежедневный отчёт по BTC и XAUT.
 
Сделай следующие поиски по порядку:
1. "Bitcoin price today" — текущая цена BTC, изменение за 24ч и 7 дней
2. "Bitcoin fear and greed index today" — текущий индекс страха/жадности
3. "Bitcoin support resistance levels today" — ключевые уровни поддержки и сопротивления
4. "Bitcoin price analysis forecast" — технический анализ и прогноз от авторитетных источников (CoinDesk, CryptoQuant, Glassnode, крупные аналитики)
5. "XAUT Tether Gold price today" — текущая цена XAUT
6. "Gold price analysis forecast 2026" — анализ и прогноз по золоту
 
После поисков напиши отчёт СТРОГО по этому шаблону, без лишних переносов строк внутри пунктов:
 
📊 *ЕЖЕДНЕВНЫЙ ОТЧЁТ* — [текущая дата]
 
━━━━━━━━━━━━━━━━━━━━
₿ *BITCOIN (BTC)*
━━━━━━━━━━━━━━━━━━━━
💰 Цена: $XX,XXX (+X.X% за 24ч)
📆 За неделю: X.X% (▲/▼)
😨 Индекс страха/жадности: XX — [название уровня]
 
📊 *Ключевые уровни:*
Поддержка: $XX,XXX / $XX,XXX / $XX,XXX
Сопротивление: $XX,XXX / $XX,XXX / $XX,XXX
 
💡 *Анализ и прогноз:* [2-3 предложения конкретного технического анализа на основе найденных данных. Укажи что происходит с ценой прямо сейчас, какой сценарий наиболее вероятен на ближайшие дни, и на что обратить внимание. Без воды, только факты и конкретика.]
 
━━━━━━━━━━━━━━━━━━━━
🥇 *TETHER GOLD (XAUT)*
━━━━━━━━━━━━━━━━━━━━
💰 Цена: $X,XXX (+X.X% за 24ч)
📆 За неделю: X.X% (▲/▼)
 
📊 *Ключевые уровни:*
Поддержка: $X,XXX / $X,XXX
Сопротивление: $X,XXX / $X,XXX
 
💡 *Анализ и прогноз:* [2-3 предложения конкретного анализа по золоту/XAUT. Макроэкономический контекст, ключевые драйверы цены, ближайший прогноз.]
 
━━━━━━━━━━━━━━━━━━━━
📌 *Источники:* [2-3 основных источника]
 
ВАЖНЫЕ ПРАВИЛА:
- Все цифры должны быть реальными из поиска, не выдуманными
- Индекс страха/жадности ищи на alternative.me или coinmarketcap
- Уровни поддержки/сопротивления бери из технического анализа, не придумывай
- Прогноз должен быть связным текстом, не набором несвязанных фраз
- Не противоречь сам себе в одном отчёте
- Пиши на русском языке
"""
 
# ── Генерация отчёта ──────────────────────────────────────────────────────────
 
def generate_report() -> str:
    """Запускает Claude с web_search и возвращает готовый отчёт."""
    messages = [{
        "role": "user",
        "content": "Составь ежедневный отчёт по BTC и XAUT по заданному формату. Используй актуальные данные из интернета."
    }]
 
    while True:
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )
 
        tool_uses  = [b for b in response.content if b.type == "tool_use"]
        text_parts = [b.text for b in response.content if b.type == "text"]
 
        if response.stop_reason == "end_turn" or not tool_uses:
            return "\n".join(text_parts) or "❌ Не удалось составить отчёт."
 
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": t.id, "content": "Результаты поиска получены."}
                for t in tool_uses
            ]
        })
 
 
# ── Отправка отчёта ───────────────────────────────────────────────────────────
 
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Генерирую ежедневный отчёт BTC/XAUT...")
 
    # Уведомляем что начали
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="⏳ Собираю данные по BTC и XAUT...",
    )
 
    try:
        report = await asyncio.get_event_loop().run_in_executor(None, generate_report)
        logger.info("Отчёт готов, отправляю.")
 
        # Разбиваем если длиннее 4096 символов
        for i in range(0, len(report), 4096):
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=report[i:i+4096],
                parse_mode="Markdown",
            )
 
    except Exception as e:
        logger.error(f"Ошибка генерации отчёта: {e}")
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"❌ Ошибка при составлении отчёта:\n{e}",
        )
 
 
# ── Команды ───────────────────────────────────────────────────────────────────
 
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я отслеживаю BTC и XAUT.\n\n"
        "📊 Каждый день в 10:00 МСК ты получаешь отчёт автоматически.\n\n"
        "Команды:\n"
        "/report — получить отчёт прямо сейчас"
    )
 
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = await update.message.reply_text("⏳ Собираю данные по BTC и XAUT... (10-30 сек)")
    try:
        report = await asyncio.get_event_loop().run_in_executor(None, generate_report)
        await status.delete()
        for i in range(0, len(report), 4096):
            await update.message.reply_text(report[i:i+4096], parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка:\n{e}")
 
 
# ── Запуск ────────────────────────────────────────────────────────────────────
 
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
 
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("report", cmd_report))
 
    # Планировщик: каждый день в 07:00 UTC (= 10:00 МСК)
    app.job_queue.run_daily(
        send_daily_report,
        time=time(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        name="daily_report",
    )
 
    logger.info(f"🤖 Бот запущен. Отчёт каждый день в {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} UTC (10:00 МСК).")
    app.run_polling()
 
 
if __name__ == "__main__":
    main()
