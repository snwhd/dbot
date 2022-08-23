from __future__ import annotations
from typing import (
    List,
    Optional,
)

import json
import pathlib

from dbot.type_help import *


class BotConfig:

    def __init__(
        self,
        name: str,
        email: str,
        password: str,
        *,
        friends: Optional[List[str]] = None,
        admins: Optional[List[str]] = None,
        command_prompt = 'dbots',
        max_errors = 0,
    ) -> None:
        self.command_prompt = command_prompt
        self.max_errors = max_errors
        self.friends = friends or []
        self.admins = admins or []
        self.password = password
        self.email = email
        self.name = name

    @classmethod
    def from_file(
        cls,
        filename: str,
        botname: str,
    ) -> BotConfig:
        path = pathlib.Path(filename)
        if path.exists() and path.is_file():
            with path.open() as f:
                config = json.load(f)
        bots = expect_dict_in(config, 'bots')
        botconfig = expect_dict_in(bots, botname)

        email = expect_str_in(botconfig, 'email')
        password = expect_str_in(botconfig, 'password')

        friends = list(bots.keys())
        friends.remove(botname)
        admins = config.get('admins', [])

        # parse configs and filter out nulls
        configs: Dict[str, Any] = {
            k: v for k, v in dict(
                command_prompt = try_str_in(config, 'command_prompt'),
                max_errors = try_int_in(config, 'max_errors'),
                friends = friends,
                admins = admins,
            ).items() if v is not None
        }
        return cls(
            botname,
            email,
            password,
            **configs,
        )
