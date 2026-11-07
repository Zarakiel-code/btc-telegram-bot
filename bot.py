import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from api import get_btc_price, get_klines
from indicators import cal_indicators
from datetime import datetime, timezone
from flask import Flask
import threading

"""FIRST_CONFIG"""

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("BOT_TOKEN")
ALERT_INTERVAL = 900

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app_web = Flask(__name__)

@app_web.route('/')
def health_check():
    return "Bot is alive", 200

def run_web():
    app_web.run(host='0.0.0.0', port=8000)

"""BOT_COMMANDS"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("¡Saludos! Desde hoy seré tu informante periódico sobre los precios del bitcoin (BTC). Para más información de mis comandos, visita /help y obtendrás la lista de comamdos completa.\n\n"
    
    "Disclaimer ⚠️: Toda la información que proporcionamos aquí es con fines informativos. No nos responsabilizamos del tipo de uso que los usuarios le den a esta información.")
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
    """ Lista de comandos:
        
/start  - bienvenida + disclaimer
/help - lista de comandos
/btc_price  - precio actual + variación 24h
/indicadores - RSI, SMA20, SMA50, volatilidad
/alerta_on  - activar alertas automáticas
/alerta_off - desactivar alertas automáticas
/estado - diagnóstico (última consulta, alertas activas)"""
    )
    
async def btc_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
    data = await get_btc_price()
    if data is None:
           
           await update.message.reply_text("⚠️ No pude obtener el precio ahora mismo. Intenta de nuevo en un minuto.")
    
    else:
           await update.message.reply_text(
           "AVISO: Los datos que se muestran aquí son meramente informativos!! Por favor, úselos con discreción. No nos responsabilizamos por malas decisiones financieras\n"
           "Datos proporcionados por: CoinGecko\n"
           "https://www.coingecko.com/ \n\n"
        f"📊 *Bitcoin (BTC)*\n\n"
        f"💰 Precio: ${data['price']:,.2f}\n"
        f"📈 Cambio 24h: {data['change_24h']:+.2f}%\n"
        f"🏦 Market Cap: ${data['market_cap']:,.0f}\n"
        f"📊 Volumen 24h: ${data['volume_24h']:,.0f}"
    )
        
async def indicators(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
    d = await get_klines()
    if d is None:
        await update.message.reply_text("⚠️ No pude obtener velas ahora mismo.") 
    else:
        indicators = cal_indicators(d)
        await update.message.reply_text( "AVISO: Los datos que se muestran aquí son meramente informativos!! Por favor, úselos con discreción. No nos responsabilizamos por malas decisiones financieras\n"
        f"📊 *Indicadores BTC*\n"
        f"Precio: ${indicators['precio']:,.2f}\n"
        f"RSI: {indicators['rsi']}\n"
        f"SMA20: ${indicators['sma20']:,.2f}\n"
        f"SMA50: ${indicators['sma50']:,.2f}\n"
        f"Dist. SMA20: {indicators['dist_sma20']:+.2f}%\n"
        f"Dist. SMA50: {indicators['dist_sma50']:+.2f}%\n"
        f"Tendencia: {indicators['tendencia']}",
        parse_mode="Markdown",
    )
    
def _job_name(chat_id: int) -> str:
    return f"alert{chat_id}"
    
async def _alert_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    data = await get_btc_price()
    kl = await get_klines()

    if data is None:
        return
        
    tendencia = "No disponible"
    if kl is not None:
        ind = cal_indicators(kl)
        tendencia = ind['tendencia']

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🚨 *Alerta BTC*\n"
            f"Precio: ${data['price']:,.2f}\n"
            f"Cambio 24h: {data['change_24h']:+.2f}%\n\n"
            f"Tendencia: {tendencia}\n\n"
            f"_Información meramente informativa._"
        ),
        parse_mode="Markdown",
    )
    
async def alert_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
     
     chat_id = update.effective_chat.id
     if context.job_queue.get_jobs_by_name(_job_name(chat_id)):
        await update.message.reply_text("ℹ️ Ya tienes alertas activas. Usa /alerta_off para desactivarlas.")
        return
         
     context.job_queue.run_repeating(
        _alert_job,
        interval=ALERT_INTERVAL,
        first=10,                    # primera ejecución en 10s, no inmediata
        name=_job_name(chat_id),
        chat_id=chat_id,
    )
    
     await update.message.reply_text(f"✅ Alertas activadas. Revisaré cada {ALERT_INTERVAL // 60} min.")
    
async def alert_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(_job_name(chat_id))
    if not jobs:
        await update.message.reply_text("ℹ️ No tienes alertas activas.")
        return
        
    for job in jobs:
        job.schedule_removal()
    context.chat_data.pop("last_alert_ts", None)
    await update.message.reply_text("🔕 Alertas desactivadas.") 
    
async def state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(_job_name(chat_id))
    
    if not jobs:
        await update.message.reply_text("📭 Alertas: inactivas\nUsa /alerta_on para activarlas.")
        return
        
    nxt = jobs[0].next_t
    await update.message.reply_text(
        f"📬 Alertas: activas\n"
        f"⏭ Próxima consulta: {nxt:%H:%M:%S} (UTC)\n"
        f"⚙️ Revisando cada {ALERT_INTERVAL // 60} minutos."
    )
    
async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text_received = update.message.text
        await update.message.reply_text(
        "Lo lamento!! Su mensaje no está registrado en la lista de comandos."
        "Para acceder a nuestros servicios, use el comando /help para obtener la la lista de comandos disponible"
        )
        
def main() -> None:
    
    threading.Thread(target=run_web, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("btc_price", btc_price))
    app.add_handler(CommandHandler("indicadores", indicators))
    app.add_handler(CommandHandler("alerta_on", alert_on))
    app.add_handler(CommandHandler("alerta_off", alert_off))
    app.add_handler(CommandHandler("estado", state))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_message))
    
    app.run_polling()
    
if __name__ == "__main__":
    main()