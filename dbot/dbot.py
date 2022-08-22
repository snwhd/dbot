#!/usr/bin/env python4
from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import json
import logging
import pathlib
import time
import traceback

import dbot.events as events

from dbot.common import (
    Direction,
    PlayerData,
    UIPositions,
)
from dbot.chat_commands import (
    CommandHandler,
)
from dbot.pathfinding import (
    Point,
    TownPathfinder,
)

from dbot.action import Action
from dbot.battle import Battle
from dbot.party import Party
from dbot.party_action import PartyAction
from dbot.retrosocket import RetroSocket
from dbot.state import GameState
from dbot.uistate import UIState


class DBot:

    def __init__(
        self,
        name: str,
        email: str,
        password: str,
        friends: List[str] = [],
        admins: List[str] = [],
    ) -> None:
        self.password = password
        self.friends = friends
        self.admins = admins
        self.email = email
        self.name = name

        # commands + actions
        self.command_handler = CommandHandler(self, 'dbots')
        self.command_handler.add_default_commands()
        # TODO: queue of actions
        self.current_action: Optional[Action] = None

        # network / socket
        self._socket: Optional[RetroSocket] = None
        self.logging_out = False
        self.max_errors = 0

        # game state
        self.battle: Optional[Battle] = None
        self.party = Party(self, [self.name])
        self.state = GameState()
        self.ui = UIState()

        # movement
        # TODO: move stuff into a MovementController class
        self.movement_queue: List[Point] = []
        self.target_position: Optional[Tuple[int, int]] = None
        self.moving = {
            Direction.up: False,
            Direction.down: False,
            Direction.left: False,
            Direction.right: False,
        }
        self.bonked = [False, False]
        self.move_ready = True

    @property
    def socket(self) -> RetroSocket:
        if self._socket is None:
            raise RuntimeError('not connected')
        return self._socket

    @property
    def me(self) -> Dict[str, Any]:
        return self.state.players[self.name]

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
            if friend in self.state.players:
                logged_in_bots.append(friend)
        if include_self:
            logged_in_bots.append(self.name)
        return list(sorted(logged_in_bots))

    def is_leader(self) -> bool:
        friends = self.logged_in_friends(include_self=True)
        return len(friends) == 0 or friends[0] == self.name

    def run_forever(self) -> None:
        n_errors = 0
        with RetroSocket() as s:
            try:
                try:
                    self._socket = s
                    last_action = 0.0
                    action_threshold = 0.5
                    while not self.logging_out:
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
        if username in self.state.players:
            logging.warning(f'player already logged in? {username}')
        self.state.players[username] = {
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
        self.target_position = None
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
        self.state.join_map(e.map_name)

    def handle_leaveMap(
        self,
        e: events.LeaveMap,
    ) -> None:
        if self.target_position is not None:
            logging.info('abandoning goto, left map')
            self.stop_moving()
        self.state.left_map()

    def handle_playerLeftMap(
        self,
        e: events.PlayerLeftMap,
    ) -> None:
        if e.username in self.state.players_in_map:
            self.state.players_in_map.remove(e.username)

    def handle_playerUpdate(
        self,
        e: events.PlayerUpdate,
    ) -> None:
        player = self.state.players.get(e.username)
        if player is None:
            logging.warning(f'missing player moved: {e.username}')
        else:
            if e.username != self.name:
                self.state.players_in_map.add(e.username)
            player[e.key] = e.value

    def handle_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        player = self.state.players.get(e.username)
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

    def handle_update(
        self,
        e: events.Update,
    ) -> None:
        # TODO: why isn't this used in UIState?
        # if e.key == 'partyPromptedPlayerUsername':
        ...

    def handle_message(
        self,
        e: events.Message,
    ) -> None:
        try:
            self.command_handler.handle(e)
        except Exception as e:
            logging.warning(f'exception parsing command: {e}')
            traceback.print_exc()

    def handle_selectPlayer(
        self,
        e: events.SelectPlayer,
    ) -> None:
        ...

    def handle_party(
        self,
        e: events.Party,
    ) -> None:
        logging.debug(f'handle_party: {e.party}')
        self.party.update_party(e.party)

    def step(
        self,
        do_actions: bool,
    ) -> None:
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
    ) -> None:
        self.ui.check_event(event)
        handler = getattr(self, f'handle_{event.event_name}', None)
        if handler is not None:
            handler(event)
        else:
            print(f'event with no handler: {event.event_name}')

    def movement(self) -> None:
        if self.target_position is None:
            if len(self.movement_queue) == 0:
                # done with movement
                return
            # pop a new destination!
            self.target_position = self.movement_queue.pop(0)

        tx, ty = self.target_position
        player = self.state.players[self.name]
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
        if self.current_action is not None:
            self.current_action.step()

    #
    # helper methods for command implementation
    #

    def say(
        self,
        message: str,
        channel = 'say',
    ) -> None:
        self.socket.send_message(channel, message)

    def goto(
        self,
        path: List[Point],
    ) -> None:
        logging.info(f'new path: {path}')
        self.movement_queue = path
        # if x == self.me['coords']['x'] and y == self.me['coords']['y']:
        #     return
        self.target_position = None
        self.bonked = [False, False]

    def logout(self) -> None:
        self.socket.send_logout()
        self.logging_out = True

    def join_party(
        self,
        party: List[str],
    ) -> None:
        self.party.set_target(party)
        self.current_action = PartyAction(self)

    def click_at_tile(
        self,
        x: int,
        y: int,
    ) -> None:
        me = self.state.players[self.name]
        screen_x = 150 - (me['coords']['x'] - x) * 16
        screen_y = 120 - (me['coords']['y'] - y) * 16
        self.socket.send_click(screen_x, screen_y)


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
