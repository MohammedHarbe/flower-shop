import logging
import smtplib
import ssl
from decimal import Decimal
from email.message import EmailMessage
from typing import Any

from sqlalchemy import update

from backend.database import SessionLocal
from backend.models.order import Order
from backend.settings import Settings
from backend.time_utils import cairo_now


logger = logging.getLogger(__name__)


def send_order_notification(order: dict[str, Any]) -> None:
    """Notify the shop using detached data from an already committed order."""
    try:
        settings = Settings()
        recipients = settings.notification_recipients
        if not (
            settings.smtp_username
            and settings.smtp_password.get_secret_value()
            and recipients
        ):
            logger.error("Order notification email is not configured")
            return

        item_lines = []
        for item in order["items"]:
            item_lines.append(
                f"- {item['product_name']}"
                f" | quantity: {item['quantity']}"
                f" | unit price: {Decimal(item['unit_price']):.2f}"
                f" | subtotal: {Decimal(item['subtotal']):.2f}"
            )

        body = "\n".join(
            [
                "New ToneFlowers Order",
                "",
                f"Order ID: {order['id']}",
                f"Order status: {order['status']}",
                f"Created time: {order['created_at']}",
                "",
                "Customer:",
                f"- name: {order['customer_name']}",
                f"- phone: {order['customer_phone']}",
                f"- email: {order['customer_email'] or 'Not provided'}",
                "",
                "Receiver:",
                f"- name: {order['receiver_name']}",
                f"- phone: {order['receiver_phone']}",
                "",
                "Delivery:",
                f"- governorate: {order['governorate']}",
                f"- area: {order['delivery_area']}",
                f"- full address: {order['delivery_address']}",
                f"- delivery date: {order['delivery_date']}",
                f"- delivery slot: {order['delivery_slot']}",
                "",
                "Items:",
                *item_lines,
                "",
                f"Total: {Decimal(order['total_price']):.2f}",
                "",
                f"Card message: {order['card_message'] or 'None'}",
                f"Sender name on card: {order['sender_name_on_card'] or 'None'}",
                f"Customer note: {order['customer_note'] or 'None'}",
            ]
        )

        message = EmailMessage()
        message["Subject"] = f"New ToneFlowers Order #{order['id']}"
        message["From"] = settings.smtp_username
        message["To"] = ", ".join(recipients)
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            refused = smtp.send_message(message, to_addrs=recipients)
            if refused:
                raise RuntimeError("One or more order notification recipients were refused")
    except Exception:
        # Notification errors never undo or hide a committed order.
        logger.exception("Failed to send order notification email")
        return

    try:
        # The request session is closed by now. Record success in a new session.
        with SessionLocal() as db:
            changed = db.execute(
                update(Order)
                .where(Order.id == order["id"], Order.notified_at.is_(None))
                .values(notified_at=cairo_now())
            )
            db.commit()
            if changed.rowcount == 0:
                logger.warning("Notification sent, but order %s was not marked", order["id"])
    except Exception:
        logger.exception("Order email was accepted, but notified_at could not be recorded")
