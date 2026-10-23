# apps/api/nex_api/telegram_notifier.py
import logging
from aiohttp import ClientSession

logger = logging.getLogger("hunter_ksa1.telegram")

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{self.token}/sendMessage" if token else None

    async def send_message(self, text: str) -> bool:
        if not self.url or not self.chat_id:
            return False
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            async with ClientSession() as session:
                async with session.post(self.url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"فشل إرسال إشعار تلغرام: {e}")
            return False

    async def notify_trade(self, symbol: str, side: str, price: float, qty: float, sl: float, tp: float):
        msg = (
            f"🎯 *صفقة جديدة - hunter_ksa1*\n\n"
            f"🔹 *الرمز:* `{symbol}`\n"
            f"🔹 *النوع:* `{side}`\n"
            f"🔹 *السعر:* `{price}`\n"
            f"🔹 *الكمية:* `{qty}`\n"
            f"🛑 *وقف الخسارة:* `{sl}`\n"
            f"🎯 *جني الأرباح:* `{tp}`"
        )
        await self.send_message(msg)
