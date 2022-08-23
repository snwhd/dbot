from __future__ import annotations

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.bot import BasicBot


class Action:

    def __init__(
        self,
        bot: BasicBot,
    ) -> None:
        self.bot = bot

    def step(self) -> bool:
        raise NotImplementedError('Action.step should be overridden')
