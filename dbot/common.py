from typing import (
    Optional,
)
import enum


class Direction(enum.Enum):

    up = 'up'
    down = 'down'
    left = 'left'
    right = 'right'


class PlayerData:

    def __init__(
        self,
        cierra: bool,
        monthsSubscribed: Optional[int],
        permissions: int,
        subscriber: bool,
        username: str,
    ) -> None:
        self.cierra = cierra
        self.monthsSubscribed = monthsSubscribed
        self.permissions = permissions
        self.subscriber = subscriber
        self.username = username


class UIPositions:

    START = (200.0, 200.0)
    CHARACTER_ONE = (130.0, 80.0)

    BANK_WITHDRAW_100G = (117.0, 90.0)
    BANK_WITHDRAW = (106.0, 158.0)
    BANK_DONE = (183.0, 189.0)

    PARTY_INVITE = (157.0, 185.0)
    BATTLE_INVITE = (102.0, 185.0)
    TRADE_INVITE = (195.0, 185.0)
    PLAYER_SELECT_EXIT = (245.0, 145.0)

    ACCEPT_INVITE = (123.0, 185.0)
    DECLINE_INVITE = (185.0, 185.0)
