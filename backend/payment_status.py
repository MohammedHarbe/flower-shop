from enum import Enum


class PaymentStatus(str, Enum):
    awaiting_payment = "awaiting_payment"
    unpaid = "unpaid"
    paid = "paid"
