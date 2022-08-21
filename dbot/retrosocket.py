#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import logging
import pprint
import socketio
import queue
import time
import traceback

import dbot.events as events
from dbot.common import (
    Direction,
    PlayerData,
)


#
# First, some helper functions for typing socket messages
#


T = TypeVar('T')


def assert_type(o: Any, t: Type[T]) -> T:
    assert isinstance(o, t)
    return o


def try_type(o: Any, t: Type[T]) -> Optional[T]:
    if isinstance(o, t):
        return o
    return None


def expect_int(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> int:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], int)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], int)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_str(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> str:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], str)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], str)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_list(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> list:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], list)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], list)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_bool(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> bool:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], bool)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], bool)
    raise ValueError(f'unsupported data type: {type(d)}')


def require_args(d: Union[List, Dict], l: int) -> None:
    if len(d) < l:
        raise ValueError('not enough data')


class GlobalNamespace(socketio.ClientNamespace):
    """ A ClientNamespace for handling all websocket messages.

        `trigger_event` is overriding socketio.ClientNamespace to provide
        handler lookup and logging unhandled events and exceptions.

        Each message type filters into an `on_*` handler method, which is
        responsible for creating an events.GameEvent object from the message
        and placing it into the event queue (to be processed by DBot).
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.event_queue = event_queue

    def trigger_event(self, event, *args):
        """ overrididing ClientNamespace """
        handler_name = f'on_{event}'
        if not hasattr(self, handler_name):
            logging.info(f'not handled: {event} ({args})')
            return

        handler = getattr(self, handler_name)

        try:
            handler(*args)
        except Exception as e:
            logging.error('\n'.join([
                f'\n\n--- exception handling {event} ---',
                pprint.pformat(args),
                ' - - - - - - - - - - - - - - - - -',
                traceback.format_exc(),
                '----------------------------------\n\n',
            ]))

    #
    # helper methods
    #

    def load_player(
        self,
        data: Dict[str, object],
    ) -> PlayerData:
        months = try_type(data['monthsSubscribed'], int) or 0
        permissions = expect_int(data, 'permissions')
        subscriber = expect_bool(data, 'subscriber')
        username = expect_str(data, 'username')
        cierra = expect_bool(data, 'cierra')
        return PlayerData(
            cierra,
            months,
            permissions,
            subscriber,
            username,
        )

    #
    # message handling
    #   These map 1:1 with GameEvent classes, except for on_disconnect. Message
    #   types are documented in events.py.
    #

    #
    # general
    #

    def on_connect(self):
        self.event_queue.put(
            events.Connected()
        )

    def on_disconnect(self):
        logging.info('disconnected')

    def on_signedIn(self, data):
        uuid = assert_type(data, str)
        self.event_queue.put(
            events.SignedIn(uuid)
        )

    def on_playerSignedIn(self, data):
        player = self.load_player(data)
        self.event_queue.put(
            events.PlayerSignedIn(player)
        )

    def on_playerPreviouslySignedIn(self, data):
        players = list(map(self.load_player, data))
        self.event_queue.put(
            events.PlayerPreviouslySignedIn(players)
        )

    def on_startCharacterSelect(self, data):
        self.event_queue.put(
            events.StartCharacterSelect()
        )

    def on_update(self, data):
        key = expect_str(data, 'key')
        value = data['value']
        self.event_queue.put(
            events.Update(
                key,
                value,
            )
        )

    #
    # movement
    #

    def on_movePlayer(self, data):
        direction = Direction(expect_str(data, 'direction'))
        username = expect_str(data, 'username')
        self.event_queue.put(
            events.MovePlayer(
                direction,
                username,
            )
        )

    def on_bonk(self, data):
        self.event_queue.put(events.Bonk())

    def on_transport(self, data):
        x = expect_float(data, 'x')
        y = expect_float(data, 'y')
        self.event_queue.put(
            events.Transport(x, y)
        )

    def on_joinMap(self, data):
        map_name = assert_type(data, str)
        self.event_queue.put(
            events.JoinMap(map_name)
        )

    def on_leaveMap(self, data):
        self.event_queue.put(
            events.LeaveMap()
        )

    def on_playerLeftMap(self, data):
        username = assert_type(data, str)
        self.event_queue.put(
            events.PlayerLeftMap(username)
        )

    #
    # players
    #

    def on_playerUpdate(self, data):
        username = expect_str(data, 'username')
        key = expect_str(data, 'key')
        value = data['value']
        self.event_queue.put(
            events.PlayerUpdate(
                username,
                key,
                value,
            )
        )

    def on_selectPlayer(self, data):
        require_args(data, 1)
        username = assert_type(data, str)
        self.event_queue.put(
            events.SelectPlayer(username)
        )

    #
    # parties
    #

    def on_invitePlayer(self, data):
        require_args(data, 1)
        username = assert_type(data, str)
        self.event_queue.put(
            events.InvitePlayer(username)
        )

    def on_party(self, data):
        party = expect_list(data, 'party')
        pid = expect_int(data, 'partyID')
        self.event_queue.put(
            events.Party(
                party,
                pid,
            )
        )

    #
    # pvp battles
    #

    # TODO: battle
    # def on_challengePlayer(self, data):

    #
    # monster battles
    #

    def on_startBattle(self, data):
        self.event_queue.put(
            events.StartBattle()
        )

    def on_leaveBattle(self, data):
        self.event_queue.put(
            events.LeaveBattle()
        )

    # TODO update(enemyMonsters=[isDead, monster])
    # TODO playerUpdate(selectedAbility)
    # TODO playerUpdate(selectedTarget)
    def on_battleEvents(self, data):
        # [
        #     {
        #         'ability': 'fireball',
        #         'caster': {'group': 'team', 'index': 0, 'type': 'player'},
        #         'casterName': 'bbot',
        #         'endDuration': 3000,
        #         'newMP': 16,
        #         'startDuration': 0,
        #         'target': {'group': 'enemies', 'index': 0, 'type': 'monster'},
        #         'targetName': 'Spider',
        #         'type': 'ability'
        #     },
        #     {
        #         'amount': 18,
        #         'endDuration': 3000,
        #         'guarded': False,
        #         'newHP': 0,
        #         'recipient': {'group': 'enemies', 'index': 0, 'type': 'monster'},
        #         'recipientName': 'Spider',
        #         'startDuration': 1500,
        #         'type': 'damage'
        #     },
        #     {
        #       'endDuration': 4500,
        #         'recipient': {'group': 'enemies', 'index': 0, 'type': 'monster'},
        #         'recipientName': 'Spider',
        #         'startDuration': 3000,
        #         'type': 'death'
        #     }
        # ]
        #...
        # [
        #  {'endDuration': 3000, 'escaped': False, 'startDuration': 0, 'type': 'victory'},
        #  {'endDuration': 6000, 'gold': 2, 'startDuration': 3000, 'type': 'gold'},
        #  {'endDuration': 6000,
        #   'experience': 3,
        #   'startDuration': 4500,
        #   'type': 'experience'}]

        ...

    #
    # trades
    #

    # TODO: trade
    # def on_requestPlayer(self, data):
    # def on_startTrade(self, data):
    # def on_leaveTrade(self, data):

    #
    # chat
    #

    def on_message(self, data):
        months = try_type(data['monthsSubscribed'], int) or 0
        permissions = expect_int(data, 'permissions')
        subscriber = expect_bool(data, 'subscriber')
        username = expect_str(data, 'username')
        contents = expect_str(data, 'contents')
        warning = expect_bool(data, 'warning')
        channel = expect_str(data, 'channel')
        cierra = expect_bool(data, 'cierra')
        mid = expect_int(data, 'id')
        self.event_queue.put(
            events.Message(
                channel,
                cierra,
                contents,
                mid,
                months,
                permissions,
                subscriber,
                username,
                warning,
            )
        )

    #
    # NPCs
    #

    # TODO: NPC
    # def on_npcUpdate(self, data):


class RetroSocket:
    """ websocket wrapper for retrommo """

    def __init__(
        self,
        host = 'retrommo-bots.herokuapp.com',
        port = 443,
    ) -> None:
        self.connected = False
        self.host = host
        self.port = port

        self.event_queue: queue.Queue = queue.Queue()
        self.socket = socketio.Client()
        self.socket.register_namespace(
            GlobalNamespace(self.event_queue, '/')
        )

    def __enter__(self) -> RetroSocket:
        self.connect()
        return self

    def __exit__(self, typ_, value, tb) -> None:
        self.disconnect()
        return

    def connect(self) -> None:
        if self.connected:
            raise RuntimeError('already connected')
        self.socket.connect(f'https://{self.host}:{self.port}')
        self.connected = True

    def disconnect(self) -> None:
        if self.connected:
            self.socket.disconnect()
            self.connected = False

    #
    # send wrappers
    #

    def send_message(
        self,
        channel: str,
        contents: str,
    ) -> None:
        """ send a chat message """
        self.socket.emit('message', {
            'channel': channel,
            'contents': contents,
        })

    def send_click(
        self,
        x: float,
        y: float,
    ) -> None:
        """ send a click at x,y coords """
        self.socket.emit('click', {
            'down': {
                'x': x,
                'y': y,
            },
            'up': {
                'x': x,
                'y': y,
            },
        })

    def send_keyup(
        self,
        key: str,
    ) -> None:
        """ send keyup (released) message """
        self.socket.emit('keyup', key)
        logging.debug(f'keyup: {key}')

    def send_keydown(
        self,
        key: str,
    ) -> None:
        """ send a keydown (pressed) message """
        self.socket.emit('keydown', key)
        logging.debug(f'keydown: {key}')

    def send_logout(self) -> None:
        """ logout from retrommo """
        logging.info('logging out')
        self.socket.emit('logOut')

