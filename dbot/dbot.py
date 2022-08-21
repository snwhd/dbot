#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
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

from dbot.action import (
    BotAction,
    ActionState,
    GrindTarget,
)
from dbot.common import (
    Direction,
    PlayerData,
    UIPositions,
)
from dbot.chat_commands import (
    CommandHandler,
)
from dbot.uistate import UIState
from dbot.retrosocket import RetroSocket


class DBot:

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

        self.ui = UIState()
        self.command_handler = CommandHandler(self, 'dbots')
        self.command_handler.add_default_commands()

        self.max_errors = 0

        self.logging_out = False

        self._socket: Optional[RetroSocket] = None

        self.current_action = BotAction.none
        self.current_state = ActionState.none

        self.last_map  = ''
        self.current_map = ''
        self.players_in_map: Set[str] = set()
        self.logged_in_players: Dict[str, Any] = {}

        # state: party up
        self.invites_sent: Dict[str, float] = {}
        self.current_party: List[str] = []
        self.target_party: List[str] = []
        self.in_party = False

        self.player_select_open = False
        self.player_selected = ''
        self.party_request_open = False
        self.party_request_from = ''

        self.last_action_at = 0.0

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

    @property
    def socket(self) -> RetroSocket:
        if self._socket is None:
            raise RuntimeError('not connected')
        return self._socket

    @property
    def me(self) -> Dict[str, Any]:
        return self.logged_in_players[self.name]

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

    def identify_party(
        self,
        exclude: Optional[List[str]] = [],
    ) -> List[str]:
        friends = self.logged_in_friends(include_self=True)
        for f in exclude or []:
            if f in friends:
                friends.remove(f)

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
        assert self.current_map == ''
        self.current_map = e.map_name

    def handle_leaveMap(
        self,
        e: events.LeaveMap,
    ) -> None:
        self.last_map = self.current_map
        self.current_map = ''

    def handle_playerLeftMap(
        self,
        e: events.PlayerLeftMap,
    ) -> None:
        if e.username in self.players_in_map:
            self.players_in_map.remove(e.username)

    def handle_playerUpdate(
        self,
        e: events.PlayerUpdate,
    ) -> None:
        player = self.logged_in_players.get(e.username)
        if player is None:
            logging.warning(f'missing player moved: {e.username}')
        else:
            if e.username != self.name:
                self.players_in_map.add(e.username)
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

    def handle_update(
        self,
        e: events.Update,
    ) -> None:
        me = self.logged_in_players[self.name]
        me[e.key] = e.value
        if e.key == 'partyPromptedPlayerUsername':
            self.party_request_from = str(e.value)
            self.party_request_open = True

    def handle_message(
        self,
        e: events.Message,
    ) -> None:
        try:
            self.command_handler.handle(e)
        except Exception as e:
            logging.warning(f'exception parsing command: {e}')

    def handle_selectPlayer(
        self,
        e: events.SelectPlayer,
    ) -> None:
        self.player_select_open = True
        self.player_selected = e.username

    def handle_party(
        self,
        e: events.Party,
    ) -> None:
        logging.debug(f'handle_party: {e.party}')
        self.in_party = len(e.party) > 0
        self.current_party = e.party

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
        if self.current_action == BotAction.party_up:
            if self.is_party_leader():
                self.action_party_up_leader()
            else:
                self.action_party_up()
        else:
            pass

    def action_party_up_leader(self) -> None:
        now = time.time()
        logging.debug(f'party_up (leader) - {self.current_state.value}')

        if self.current_state == ActionState.none:
            self.current_state = ActionState.waiting_for_players

        if len(self.current_party) == len(self.target_party):
            logging.debug(f'party complete: {self.current_party} == {self.target_party}')
            self.current_state = ActionState.joined_party
        elif self.current_state == ActionState.waiting_for_players:
            for name in self.target_party:
                if name == self.name:
                    continue
                me = self.logged_in_players[self.name]
                player = self.logged_in_players[name]
                player_x = player['coords']['x']
                player_y = player['coords']['y']
                if (
                    abs(player_x - me['coords']['x']) <= 1 and
                    abs(player_y - me['coords']['y']) <= 1
                ):
                    sent_at = self.invites_sent.get(name)
                    if sent_at is None or (now - sent_at) > 3.5:
                        logging.debug(f'sending invite to: {name}')
                        self.invites_sent[name] = now
                        self.click_at_tile(player_x, player_y)
                        self.current_state = ActionState.selecting_player
                        self.last_action_at = now
                        return
                else:
                    logging.debug(f'{name} too far away ({player_x}, {player_y})')
        elif self.current_state == ActionState.selecting_player:
            if self.player_select_open:
                if self.player_selected in self.target_party:
                    self.socket.send_click(*UIPositions.PARTY_INVITE)
                    logging.debug(f'sent invite to {self.player_selected}')
                else:
                    logging.info(f'click wrong player ({self.player_selected})')
                    self.socket.send_click(*UIPositions.PLAYER_SELECT_EXIT)
                self.player_selected = ''
                self.player_select_open = False
                self.current_state = ActionState.waiting_for_players
                self.last_action_at = now
            elif now - self.last_action_at > 0.5:
                logging.info('player select didnt pop up')
                self.current_state = ActionState.waiting_for_players
                self.last_action_at = now

    def action_party_up(self) -> None:
        logging.debug(f'party_up (follower) - {self.current_state.value}')

        if self.current_state == ActionState.none:
            self.current_state = ActionState.moving_to_leader
            return
        elif self.current_state == ActionState.moving_to_leader:
            leader_name = self.party_leader()
            assert leader_name is not None
            leader = self.logged_in_players[leader_name]
            me = self.logged_in_players[self.name]
            if (
                self.target_position is None and
                abs(leader['coords']['x'] - me['coords']['x']) <= 1 and
                abs(leader['coords']['y'] - me['coords']['y']) <= 1
            ):
                self.current_state = ActionState.awaiting_invite
                return
        elif self.current_state == ActionState.awaiting_invite:
            if self.party_request_open:
                if self.party_request_from == self.party_leader():
                    self.socket.send_click(*UIPositions.ACCEPT_INVITE)
                    self.current_state = ActionState.accepted_party
                else:
                    self.socket.send_click(*UIPositions.DECLINE_INVITE)
                    self.current_state = ActionState.awaiting_invite
        elif self.current_state == ActionState.accepted_party:
            if self.in_party:
                self.current_stae = ActionState.joined_party

    def say(
        self,
        message: str,
        channel = 'say',
    ) -> None:
        self.socket.send_message(channel, message)

    def goto(
        self,
        x: int,
        y: int,
    ) -> None:
        self.target_position = (x, y)
        self.bonked = [False, False]

    def logout(self) -> None:
        self.socket.send_logout()
        self.logging_out = True

    def join_party(
        self,
        party: List[str],
    ) -> None:
        self.target_party = party
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
            self.goto(target_x, target_y)

    def click_at_tile(
        self,
        x: int,
        y: int,
    ) -> None:
        me = self.logged_in_players[self.name]
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
