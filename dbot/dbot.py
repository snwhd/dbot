#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import enum
import json
import logging
import pathlib
import pprint
import random
import shlex
import time
import traceback

import dbot.events as events

from dbot.retrosocket import RetroSocket
from dbot.common import (
    Direction,
    PlayerData,
    UIPositions,
)


class BotAction(enum.Enum):

    none = 'none'
    party_up = 'party up'
    grind = 'grind'


class GrindTarget(enum.Enum):

    none = 'none'
    field1 = 'field1'
    field2 = 'field2'
    cave1 = 'cave1'
    cave2 = 'cave2'
    gobble = 'gobble'
    bday_cave = 'bday cave'
    bday_rush = 'bday rush'


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
        self.max_errors = 0

        self._socket: Optional[RetroSocket] = None

        self.current_action = BotAction.none
        self.logged_in_players: Dict[str, Any] = {}

        # state: party up
        self.target_party: List[str] = []
        self.in_party = False

        # movement state
        self.target_position: Optional[Tuple[int, int]] = None
        self.moving = {
            Direction.up: False,
            Direction.down: False,
            Direction.left: False,
            Direction.right: False,
        }
        self.bonked = [False, False]
        self.move_ready = True

        self.commands = {
            'debug': {
                'handler': self.command_debug,
                'admin': True,
            },
            'say': {
                'handler': self.command_say,
                'admin': False,
            },
            'where': {
                'handler': self.command_where,
                'admin': True,
            },
            'goto': {
                'handler': self.command_goto,
                'admin': True,
            },
            'grind': {
                'handler': self.command_grind,
                'admin': True,
            },
            'party': {
                'handler': self.command_party,
                'admin': True,
            },
            'logout': {
                'handler': self.command_logout,
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

    def logged_in_friends(
        self,
        include_self=False,
    ) -> List[str]:
        logged_in_bots: List[str] = []
        for friend in self.friends:
            if friend in self.logged_in_players:
                logged_in_bots.append(friend)
        if include_self:
            logged_in_bots.append(self.name)
        return list(sorted(logged_in_bots))

    def is_leader(self) -> bool:
        friends = self.logged_in_friends(include_self=True)
        return len(friends) == 0 or friends[0] == self.name

    def identify_party(self) -> List[str]:
        # TODO: exclude source
        friends = self.logged_in_friends(include_self=True)
        logging.debug(f'logged in: {friends}')
        parties = [friends[i:i+3] for i in range(0, len(friends), 3)]
        for party in parties:
            logging.debug(f'group: {party}')
            if self.name in party:
                return party
        return [self.name]

    def party_leader(self) -> Optional[str]:
        if len(self.target_party) > 0:
            return self.target_party[0]
        return None

    def is_party_leader(self) -> bool:
        leader = self.party_leader()
        return leader is None or leader == self.name

    def run_forever(self) -> None:
        n_errors = 0
        with RetroSocket() as s:
            try:
                try:
                    self._socket = s
                    last_action = 0.0
                    action_threshold = 0.5
                    while True:
                        current = time.time()
                        do_action = (current - last_action) > action_threshold
                        self.step(do_action)
                        if do_action:
                            last_action = current
                        time.sleep(0.2)
                except KeyboardInterrupt as e:
                    s.send_logout()
                    time.sleep(1)
                    return
            except Exception as e:
                n_errors += 1
                if n_errors > self.max_errors:
                    logging.error('hit maximum errors')
                    raise e
                else:
                    logging.warning('\n'.join([
                        '--- exception in dbot ---',
                        traceback.format_exc(),
                        '-------------------------',
                    ]))
            finally:
                self._socket = None

    def add_player(
        self,
        player: PlayerData,
    ) -> None:
        username = player.username
        if username in self.logged_in_players:
            logging.warning(f'player already logged in? {username}')
        self.logged_in_players[username] = {
            'username': username,
        }

    def move_up(self, moving=True):
        if moving:
            if self.moving[Direction.up]:
                return
            assert not any(self.moving.values()), self.moving
            self.moving[Direction.up] = True
            self.socket.send_keydown('w')
        else:
            self.moving[Direction.up] = False
            self.socket.send_keyup('w')

    def move_down(self, moving=True):
        if moving:
            if self.moving[Direction.down]:
                return
            assert not any(self.moving.values()), self.moving
            self.moving[Direction.down] = True
            self.socket.send_keydown('s')
        else:
            self.moving[Direction.down] = False
            self.socket.send_keyup('s')

    def move_left(self, moving=True):
        if moving:
            if self.moving[Direction.left]:
                return
            assert not any(self.moving.values()), self.moving
            self.moving[Direction.left] = True
            self.socket.send_keydown('a')
        else:
            self.moving[Direction.left] = False
            self.socket.send_keyup('a')

    def move_right(self, moving=True):
        if moving:
            if self.moving[Direction.right]:
                return
            assert not any(self.moving.values()), self.moving
            self.moving[Direction.right] = True
            self.socket.send_keydown('d')
        else:
            self.moving[Direction.right] = False
            self.socket.send_keyup('d')

    def stop_moving(self) -> None:
        if self.moving[Direction.up]:
            self.move_up(False)
        if self.moving[Direction.down]:
            self.move_down(False)
        if self.moving[Direction.left]:
            self.move_left(False)
        if self.moving[Direction.right]:
            self.move_right(False)

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
        self.add_player(e.player)

    def handle_playerPreviouslySignedIn(
        self,
        e: events.PlayerPreviouslySignedIn,
    ) -> None:
        for player in e.players:
            self.add_player(player)

    def handle_joinMap(
        self,
        e: events.JoinMap,
    ) -> None:
        ...

    def handle_playerUpdate(
        self,
        e: events.PlayerUpdate,
    ) -> None:
        player = self.logged_in_players.get(e.username)
        if player is None:
            logging.warning(f'missing player moved: {e.username}')
            return
        player[e.key] = e.value

    def handle_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        player = self.logged_in_players.get(e.username)
        if player is None:
            logging.warning(f'missing player moved: {e.username}')
            return

        if e.direction == Direction.down:
            player['coords']['y'] += 1
        elif e.direction == Direction.up:
            player['coords']['y'] -= 1
        elif e.direction == Direction.left:
            player['coords']['x'] -= 1
        elif e.direction == Direction.right:
            player['coords']['x'] += 1

        if self.name != e.username:
            return

        # special handling of this bots movement for target position
        if self.target_position is None:
            logging.warning('movePlayer for self, without target?')
            self.stop_moving()
            return

        near_threshold = 4

        if e.direction in (Direction.down, Direction.up):
            diff = abs(player['coords']['y'] - self.target_position[1])
            if diff < near_threshold:
                logging.debug('reaching y')
                if e.direction == Direction.down:
                    self.move_down(False)
                else:
                    self.move_up(False)
        else:
            assert e.direction in (Direction.left, Direction.right)
            diff = abs(player['coords']['x'] - self.target_position[0])
            if diff < near_threshold:
                logging.debug('reaching x')
                if e.direction == Direction.left:
                    self.move_left(False)
                else:
                    self.move_right(False)

        if self.name == e.username:
            logging.debug(f'new pos: {player["coords"]}')

    def handle_bonk(
        self,
        e: events.Bonk,
    ) -> None:
        if self.moving[Direction.up]:
            self.bonked[1] = True
            self.move_up(False)
        elif self.moving[Direction.down]:
            self.bonked[1] = True
            self.move_down(False)
        elif self.moving[Direction.left]:
            self.bonked[0] = True
            self.move_left(False)
        elif self.moving[Direction.right]:
            self.bonked[0] = True
            self.move_right(False)
        else:
            logging.info('bonk when not moving!?')
        # stop_moving()

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
            e.contents.startswith(self.name + ' ')
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

        # TODO: typing for command configs
        command_config['handler'](command, parts, source, channel) # type: ignore

    def command_debug(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        print('--- debug command ---')
        print('#   players   #')
        pprint.pprint(self.logged_in_players)
        print('---------------------')

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
        if len(parts) > 0 and parts[0] == 'up':
            parts.pop(0)
            self.target_party = self.identify_party()
        elif len(parts) > 2:
            friends = self.logged_in_friends()
            bots = list(filter(
                lambda b: b != '_' and b in friends,
                parts[:3]
            ))
            self.target_party = bots
            parts = parts[3:]

        logging.debug(f'party: {self.target_party}')

        if len(self.target_party) == 1:
            self.socket.send_message('wsay', "I'm solo")
            self.current_action = BotAction.none
            return

        self.current_action = BotAction.party_up
        leader_name = self.party_leader()
        assert leader_name is not None
        leader = self.logged_in_players[leader_name]
        party_position = self.target_party.index(self.name)
        if party_position != 0:
            target_x = int(leader['coords']['x'])
            target_y = int(leader['coords']['y'])
            if party_position == 1:
                target_x -= 1
            if party_position == 2:
                target_x += 1
            self.target_position = (target_x, target_y)

        # TODO: pending action
        # if len(parts) > 0 and parts[0] == 'and':
        #     self.do_command(
        #         shlex.join(['dbots'] + parts),
        #         source,
        #         channel,
        #     )

    def command_goto(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        if len(parts) < 2:
            return

        try:
            x = int(parts[0])
            y = int(parts[1])
        except ValueError as e:
            self.socket.send_message(channel, 'I can\'t go there')
            return

        self.target_position = (x, y)
        self.bonked = [False, False]

    def command_logout(
        self,
        command: str,
        parts: List[str],
        source: str,
        channel: str,
    ) -> None:
        self.socket.send_logout()


    def step(
        self,
        do_actions: bool,
    ):
        s = self.socket
        while not self.socket.event_queue.empty():
            event = self.socket.event_queue.get()
            self.handle_event(event)
        if do_actions:
            self.movement()
            self.action()

    def handle_event(
        self,
        event: events.GameEvent,
    ):
        handler = getattr(self, f'handle_{event.event_name}')
        if handler is not None:
            handler(event)
        else:
            print(f'event with no handler: {event.event_name}')

    def movement(self) -> None:
        if self.target_position is None:
            return

        tx, ty = self.target_position
        player = self.logged_in_players[self.name]
        x = player['coords']['x']
        y = player['coords']['y']
        # TODO: smarter pathfinding, need to parse map
        if y != ty and not self.bonked[1]:
            if y > ty:
                self.move_up()
            else:
                self.move_down()
        elif x != tx and not self.bonked[0]:
            if x > tx:
                self.move_left()
            else:
                self.move_right()

        if x == tx and y == ty:
            logging.info('reached destination')
            self.target_position = None
            self.bonked = [False, False]
            self.stop_moving()
        elif self.bonked[0] and self.bonked[1]:
            logging.info('cannot reach destination')
            self.target_position = None
            self.bonked = [False, False]
            self.stop_moving()

    def action(self) -> None:
        ...
            


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('botname')
    parser.add_argument('--config', type=str, default='config.json')
    parser.add_argument('--nerror', type=int, default=0)
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)

    bot = DBot.load_from_config(args.config, args.botname)
    bot.max_errors = args.nerror
    bot.run_forever()
