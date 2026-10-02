import logging
import smtplib
import ssl
from decimal import Decimal
from email.message import EmailMessage
from typing import Any

from sqlalchemy import update

from backend.database import SessionLocal
from backend.logging_utils import log_failure
from backend.models.order import Order
from backend.settings import Settings
from backend.time_utils import cairo_now


logger = logging.getLogger(__name__)

DELIVERY_SLOT_LABELS = {
    "morning": "Morning (10:00 AM - 2:00 PM) / صباحًا (10 ص - 2 م)",
    "afternoon": "Afternoon (2:00 PM - 6:00 PM) / بعد الظهر (2 م - 6 م)",
    "evening": "Evening (6:00 PM - 10:00 PM) / مساءً (6 م - 10 م)",
}
ORDER_STATUS_LABELS = {
    "pending": "Pending availability confirmation / بانتظار تأكيد توفر الزهور",
    "confirmed": "Confirmed / تم التأكيد",
    "preparing": "Preparing / قيد التجهيز",
    "out_for_delivery": "Out for delivery / في الطريق",
    "delivered": "Delivered / تم التوصيل",
    "cancelled": "Cancelled / ملغي",
}
PAYMENT_METHOD_LABELS = {
    "vodafone_cash": "Vodafone Cash / فودافون كاش",
    "cash_on_delivery": "Cash on Delivery / الدفع عند الاستلام",
}
PAYMENT_STATUS_LABELS = {
    "awaiting_payment": "Awaiting payment after availability confirmation / بانتظار الدفع بعد تأكيد التوفر",
    "unpaid": "Unpaid / غير مدفوع",
    "paid": "Paid / مدفوع",
}


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

        subtotal = Decimal(order.get("subtotal", order.get("total_price", "0.00")))
        delivery_fee = Decimal(order.get("delivery_fee", "0.00"))
        total_price = Decimal(order.get("total_price", subtotal + delivery_fee))
        payment_method = order.get("payment_method", "cash_on_delivery")
        payment_status = order.get("payment_status", "unpaid")
        order_status = order.get("status", "pending")
        delivery_slot = str(order.get("delivery_slot", ""))

        body = "\n".join(
            [
                "New ToneFlowers Order",
                "ORDER REQUIRES AVAILABILITY CONFIRMATION",
                "الطلب بانتظار تأكيد توفر الزهور",
                "Do not request Vodafone Cash payment before availability is confirmed.",
                "",
                f"Order ID: {order['id']}",
                f"Order status: {ORDER_STATUS_LABELS.get(str(order_status), 'Pending availability confirmation')}",
                f"Payment preference: {PAYMENT_METHOD_LABELS.get(str(payment_method), 'Payment method not specified')}",
                f"Payment status: {PAYMENT_STATUS_LABELS.get(str(payment_status), 'Payment status unavailable')}",
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
                f"- delivery slot: {DELIVERY_SLOT_LABELS.get(delivery_slot, delivery_slot or 'To be confirmed')}",
                "",
                "Items:",
                *item_lines,
                "",
                f"Subtotal: {subtotal:.2f}",
                f"Delivery fee: {delivery_fee:.2f}",
                f"Total: {total_price:.2f}",
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
    except Exception as error:
        # Notification errors never undo or hide a committed order.
        log_failure(logger, "Failed to send order notification email", error)
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
    except Exception as error:
        log_failure(logger, "Order email was accepted, but notified_at could not be recorded", error)
