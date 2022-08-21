#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    List,
    Optional,
)

import json
import logging
import pathlib
import random
import shlex
import time
import traceback

import dbot.events as events

from dbot.retrosocket import RetroSocket
from dbot.common import (
    UIPositions,
)


class DBot:

    hello_messages = [
        'hey :)',
        'hello!',
        '\\o',
        'greetings',
        'howdy!',
    ]

    def __init__(
        self,
        name: str,
        email: str,
        password: str,
        friends: List[str] = [],
        admins: List[str] = [],
    ) -> None:
        self.name = name
        self.email = email
        self.password = password
        self.friends = friends
        self.admins = admins

        self._socket: Optional[RetroSocket] = None

        self.logged_in_players: List[str] = []

        self.commands = {
            'say': {
                'handler': self.command_say,
                'type': 'everyone',
                'admin': False,
            },
            'where': {
                'handler': self.command_where,
                'type': 'everyone',
                'admin': True,
            },
            'grind': {
                'handler': self.command_grind,
                'type': 'everyone',
                'admin': True,
            },
            'party': {
                'handler': self.command_party,
                'type': 'everyone',
                'admin': True,
            },
            'logout': {
                'handler': self.command_logout,
                'type': 'everyone',
                'admin': True,
            },
        }

    @property
    def socket(self) -> RetroSocket:
        if self._socket is None:
            raise RuntimeError('not connected')
        return self._socket

    @classmethod
    def load_from_config(
        cls,
        filename: str,
        botname: str,
    ) -> DBot:
        path = pathlib.Path(filename)
        if path.exists() and path.is_file():
            with path.open() as f:
                config = json.load(f)

        bots = config.get('bots')
        if bots is None or not isinstance(bots, dict):
            raise ValueError('invalid "bots" config')

        botconfig = bots.get(botname)
        if botconfig is None or not isinstance(botconfig, dict):
            raise ValueError(f'invalid config for "{botname}"')

        email = botconfig.get('email')
        password = botconfig.get('password')
        if email is None or password is None:
            raise ValueError(f'{botname} config missing email/pass')

        friends = list(bots.keys())
        friends.remove(botname)
        admins = config.get('admins', [])
        return cls(
            botname,
            email,
            password,
            friends=friends,
            admins=admins,
        )

    def is_leader(self) -> bool:
        logged_in_bots: List[str] = []
        for friend in self.friends:
            if friend in self.logged_in_players:
                logged_in_bots.append(friend)
        rank = sorted(logged_in_bots)
        return len(rank) == 0 or rank[0] == self.name

    def run_forever(self) -> None:
        with RetroSocket() as s:
            try:
                self._socket = s
                while True:
                    self.step()
                    time.sleep(1)
            finally:
                self._socket = None

    def handle_connected(
        self,
        e: events.Connected,
    ) -> None:
        logging.info('connected, signing in')
        self.socket.socket.emit('signIn', {
            'email': self.email,
            'password': self.password,
        })

    def handle_signedIn(
        self,
        e: events.SignedIn,
    ) -> None:
        self.socket.send_click(*UIPositions.START)

    def handle_startCharacterSelect(
        self,
        e: events.StartCharacterSelect,
    ) -> None:
        self.socket.send_click(*UIPositions.CHARACTER_ONE)

    def handle_playerSignedIn(
        self,
        e: events.PlayerSignedIn,
    ) -> None:
        ...

    def handle_playerPreviouslySignedIn(
        self,
        e: events.PlayerPreviouslySignedIn,
    ) -> None:
        ...

    def handle_joinMap(
        self,
        e: events.JoinMap,
    ) -> None:
        ...

    def handle_playerUpdate(
        self,
        e: events.PlayerUpdate,
    ) -> None:
        ...

    def handle_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        ...

    def handle_update(
        self,
        e: events.Update,
    ) -> None:
        ...

    def handle_openBank(
        self,
        e: events.OpenBank,
    ) -> None:
        ...

    def handle_transport(
        self,
        e: events.Transport,
    ) -> None:
        ...

    def handle_playerLeftMap(
        self,
        e: events.PlayerLeftMap,
    ) -> None:
        ...

    def handle_leaveMap(
        self,
        e: events.LeaveMap,
    ) -> None:
        ...

    def handle_message(
        self,
        e: events.Message,
    ) -> None:
        print(f'handling message: {e.contents}')
        if (
            e.contents.startswith('dbots ') or
            e.contents.startswith(self.name)
        ):
            self.do_command(e.contents, e.username, e.channel)
        else:
            logging.debug(f'message skipped: {e.contents}')

    def do_command(
        self,
        text: str,
        source: str,
        channel: str,
    ) -> None:
        parts = shlex.split(text)
        logging.debug(f'parsed message: {parts}')
        if len(parts) < 2:
            return

        command = parts.pop(0)
        direct = command == self.name
        if direct:
            logging.debug('command is direct')
            if len(parts) == 0:
                return
        else:
            assert command == 'dbots'
        command = parts.pop(0)

        command_config = self.commands.get(command)
        if command_config is None:
            logging.info(f'no config for command: {command}')
            return

        from_admin = source in self.admins or source in self.friends
        if command_config['admin'] and not from_admin:
            logging.info(f'not handling admin command {command} from {source}')
            if self.is_leader():
                # TODO: return message
                self.socket.send_message(channel, f'sorry {source}, we only obey d.')
            return

        if command_config['type'] == 'leader' and not self.is_leader():
            logging.info(f'command "{command}" for leader only')
            return

        # TODO: typing for command configs
        command_config['handler'](command, parts, source, channel) # type: ignore

    def command_say(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        if len(parts) == 1 and parts[0] == 'hi':
            message = random.choice(self.hello_messages)
            message.format(source)
            self.socket.send_message(channel, message)

    def command_where(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        ...

    def command_grind(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        ...

    def command_party(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        ...

    def command_logout(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        ...


    def step(self):
        s = self.socket
        while not s.event_queue.empty():
            event = s.event_queue.get()
            handler = getattr(self, f'handle_{event.event_name}')
            if handler is not None:
                handler(event)
            else:
                print(f'event with no handler: {event.event_name}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('botname')
    parser.add_argument('--config', type=str, default='config.json')
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)

    try:
        bot = DBot.load_from_config(args.config, args.botname)
        bot.run_forever()
    except KeyboardInterrupt:
        pass
