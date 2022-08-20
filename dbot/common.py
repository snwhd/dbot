from typing import (
    Optional,
)


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
    BANK_DONE = (183, 189)