from __future__ import annotations
from typing import (
    Callable,
    Dict,
    List,
)
import logging
import random
import shlex
import pprint

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.dbot import DBot

import dbot.events as events
from dbot.pathfinding import TownPathfinder


HELLO_MESSAGES = [
    'hey :)',
    'hello!',
    '\\o',
    'greetings',
    'howdy!',
]


CommandFunction = Callable[[List[str], str, str, bool], None]


class CommandConfig:

    def __init__(
        self,
        command: str,
        handler: CommandFunction,
        admin_only = True,
    ) -> None:
        self.command = command
        self.handler = handler
        self.admin_only = admin_only


class CommandHandler:

    def __init__(
        self,
        bot: DBot,
        prompt: str,
        allow_direct=True,
    ) -> None:
        self.bot = bot
        self.prompt = prompt
        self.allow_direct = allow_direct
        self.commands: Dict[str, CommandConfig] = {}

    def add_default_commands(self) -> None:
        self.add_command(CommandConfig(
            'say',
            self.command_say,
            admin_only=False,
        ))
        self.add_command(CommandConfig(
            'where',
            self.command_where,
            admin_only=False,
        ))
        self.add_command(CommandConfig(
            'debug',
            self.command_debug,
        ))
        self.add_command(CommandConfig(
            'goto',
            self.command_goto,
        ))
        self.add_command(CommandConfig(
            'grind',
            self.command_grind,
        ))
        self.add_command(CommandConfig(
            'party',
            self.command_party,
        ))
        self.add_command(CommandConfig(
            'logout',
            self.command_logout,
        ))

    def add_command(
        self,
        config: CommandConfig,
    ) -> None:
        if config.command in self.commands:
            raise ValueError(f'duplicate commands: {config.command}')
        self.commands[config.command] = config

    def should_handle(
        self,
        prompt: str,
    ) -> bool:
        if prompt == self.prompt:
            return True
        elif self.allow_direct:
            return prompt in {self.bot.name, f'@{self.bot.name}'}
        else:
            return False

    def is_admin(
        self,
        name: str,
    ) -> bool:
        return name in self.bot.admins or name in self.bot.friends

    def handle(
        self,
        e: events.Message,
    ) -> None:
        try:
            parts = shlex.split(e.contents)
        except ValueError:
            return

        if len(parts) < 2:
            return

        prompt = parts.pop(0)
        if not self.should_handle(prompt):
            return

        command = parts.pop(0)
        direct = prompt == self.bot.name

        config = self.commands.get(command)
        if config is None:
            logging.info(f'no such command: {command}')
            return

        if config.admin_only and not self.is_admin(e.username):
            logging.info('ignoring "{command}" from non-admin')
            if self.bot.is_leader():
                self.bot.socket.send_message(
                    e.channel,
                    f'sorry {e.username}, we only obey d.',
                )
            return

        # finally, we can trigger the command
        config.handler(parts, e.username, e.channel, direct)

    #
    # commands
    #

    def command_say(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        if len(parts) < 1 or parts[0] != 'hi':
            return
        message = random.choice(HELLO_MESSAGES)
        self.bot.say(message, channel)

    def command_where(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        if parts == ['are', 'you']:
            gmap = self.bot.state.map()
            pos = (self.bot.me['coords']['x'], self.bot.me['coords']['y'])
            message = f"I'm at {gmap} {pos}"
            self.bot.say(message, channel)

    def command_debug(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        print('--- debug command ---')
        print('#   players   #')
        pprint.pprint(self.bot.state.players)
        print('---------------------')

    def command_grind(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        self.bot.grind()

    def command_party(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        # TODO: party up with specific bots
        if len(parts) < 1 or parts.pop(0) != 'up':
            # expect the command for 'party up'
            return
        
        # self.target_party = self.identify_party(exclude=[source])
        target_party = self.bot.party.identify_party(exclude=[source])
        logging.debug(f'party: {target_party}')
        assert len(target_party) > 0
        if len(target_party) == 1:
            self.bot.say("I'm solo", channel)
            return

        self.bot.join_party(target_party)

    def command_goto(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        if self.bot.party.in_party and not self.bot.party.leader_is_me:
            # can't control the party
            return
        elif len(parts) < 2:
            return

        if parts[0] == 'the':
            # handling a keyword
            src = (self.bot.me['coords']['x'], self.bot.me['coords']['y'])
            path = TownPathfinder.path_to(src, parts[1])
            self.bot.goto(path)
        elif len(parts) == 2:
            # a direct point
            try:
                x = int(parts[0])
                y = int(parts[1])
                self.bot.goto([(x, y)])
            except ValueError as e:
                self.bot.say("I can't go there", channel)
                return
        else:
            logging.warning(f'invalid goto command: {parts}')

    def command_logout(
        self,
        parts: List[str],
        source: str,
        channel: str,
        direct: bool,
    ) -> None:
        self.bot.logout()
