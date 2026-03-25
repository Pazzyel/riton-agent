from enum import Enum


class ChatSessionStatueEnum(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"