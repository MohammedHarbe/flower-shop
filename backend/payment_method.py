from enum import Enum


class PaymentMethod(str, Enum):
    vodafone_cash = "vodafone_cash"
    cash_on_delivery = "cash_on_delivery"
