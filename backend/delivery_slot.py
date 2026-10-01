from enum import Enum


class DeliverySlot(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
