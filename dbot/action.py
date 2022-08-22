from __future__ import annotations

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.dbot import DBot


class Action:

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        self.bot = bot

    def step(self) -> None:
        raise NotImplementedError('Action.step should be overridden')
