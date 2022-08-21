#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Dict,
    Optional,
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


class GlobalNamespace(socketio.ClientNamespace):

    def __init__(
        self,
        event_queue: queue.Queue,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.event_queue = event_queue

    def trigger_event(self, event, *args):
        handler_name = f'on_{event}'
        if hasattr(self, handler_name):
            logging.debug(f'calling {handler_name}')
            try:
                getattr(self, handler_name)(*args)
            except Exception as e:
                logging.error('\n'.join([
                    '\n\n--- exception during event handling ---',
                    f'    event: {event}',
                    '     data ',
                    pprint.pformat(args),
                    '     exception ',
                    traceback.format_exc(),
                    '---\n\n',
                ]))
            return

        self.catch_all(event, *args)

    def catch_all(self, event, data=None):
        logging.info(f'not handled: {event} ({data})')

    def on_connect(self):
        self.event_queue.put(events.Connected())

    def on_signedIn(self, data):
        if len(data) < 1:
            logging.warning('missing uuid from signedIn')
            uuid = ''
        else:
            uuid = data[0]
        self.event_queue.put(events.SignedIn(uuid))

    def on_startCharacterSelect(self, data):
        self.event_queue.put(events.StartCharacterSelect())

    def on_playerSignedIn(self, data):
        player = self.load_player_data_from(data)
        if player is None:
            logging.warning('login with invalid player data')
            return
        self.event_queue.put(events.PlayerSignedIn(player))

    def on_playerPreviouslySignedIn(self, data):
        if len(data) < 1:
            logging.warning('missing data from playerPreviouslySignedIn')
            return

        players = list(filter(
            lambda p: p is not None,
            map(self.load_player_data_from, data)
        ))
        self.event_queue.put(events.PlayerPreviouslySignedIn(players))

    def on_joinMap(self, data):
        if len(data) < 1:
            logging.warning('missing map name in joinMap')
            return

        map_name = data[0]
        self.event_queue.put(events.JoinMap(map_name))

    def on_playerUpdate(self, data):
        key = data['key']
        value = data['value']
        username = data['username']
        self.event_queue.put(events.PlayerUpdate(
            username,
            key,
            value,
        ))

    def on_movePlayer(self, data):
        direction = Direction(data['direction'])
        username = data['username']
        assert isinstance(username, str)
        self.event_queue.put(events.MovePlayer(
            direction,
            username,
        ))

    def on_bonk(self, data):
        self.event_queue.put(events.Bonk())

    def on_update(self, data):
        key = data['key']
        value = data['value']
        self.event_queue.put(events.Update(
            key,
            value,
        ))

    def on_npcUpdate(self, data):
        # TODO
        ...

    def on_message(self, data):
        channel = data['channel']
        assert isinstance(channel, str), channel

        cierra = data['cierra'] or False
        assert isinstance(cierra, bool)

        contents = data['contents']
        assert isinstance(contents, str)

        mid = data['id']
        assert isinstance(mid, int)

        months = data['monthsSubscribed'] or 0
        assert isinstance(months, int)

        permissions = data['permissions']
        assert isinstance(permissions, int)

        subscriber = data['subscriber']
        assert isinstance(subscriber, bool)

        username = data['username']
        assert isinstance(username, str)

        warning = data['warning']
        assert isinstance(warning, bool)

        self.event_queue.put(events.Message(
            channel,
            cierra,
            contents,
            mid,
            months,
            permissions,
            subscriber,
            username,
            warning,
        ))

    def on_disconnect(self):
        logging.info('disconnected')

    def load_player_data_from(
        self,
        data: Dict[str, object],
    ) -> Optional[PlayerData]:
        cierra = data.get('cierra') or False
        assert isinstance(cierra, bool), cierra

        months = data.get('monthsSubscribed') or 0
        assert isinstance(months, int), months

        permissions = data.get('permissions') or 0
        assert isinstance(permissions, int), permissions

        subscriber = data.get('subscriber') or False
        assert isinstance(subscriber, bool), subscriber

        username = data.get('username')
        if username is None:
            logging.warning('missing username for player data')
            return None
        assert isinstance(username, str), username

        return PlayerData(
            cierra,
            months,
            permissions,
            subscriber,
            username,
        )


class RetroSocket:

    def __init__(
        self,
        host = 'retrommo-bots.herokuapp.com',
        port = 443,
    ) -> None:
        self.connected = False
        self.host = host
        self.port = port

        self.socket = socketio.Client()
        self.event_queue: queue.Queue = queue.Queue()
        self.socket.register_namespace(
            GlobalNamespace(self.event_queue, '/')
        )

        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('playerSignedIn', self.on_playerSignedIn)
        # self.socket.on_event('playerPreviouslySignedIn', self.on_playerPreviouslySignedIn)
        # self.socket.on_event('selectableCharacters', self.on_selectableCharacters)
        # self.socket.on_event('totalCharacters', self.on_totalCharacters)
        # self.socket.on_event('characterSelectHasPagination', self.on_characterSelectHasPagination)
        # self.socket.on_event('joinMap', self.on_joinMap)
        # self.socket.on_event('playerUpdate', self.on_playerUpdate)
        # self.socket.on_event('movePlayer', self.on_movePlayer)
        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('signedIn', self.on_signedIn)
        # self.socket.on_event('signedIn', self.on_signedIn)

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
    #
    #

    def send_message(
        self,
        channel: str,
        contents: str,
    ) -> None:
        self.socket.emit('message', {
            'channel': channel,
            'contents': contents,
        })

    def send_click(
        self,
        x: float,
        y: float,
    ) -> None:
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
        self.socket.emit('keyup', key)
        logging.debug(f'keyup: {key}')

    def send_keydown(
        self,
        key: str,
    ) -> None:
        self.socket.emit('keydown', key)
        logging.debug(f'keydown: {key}')

    def send_logout(self) -> None:
        logging.info('logging out')
        self.socket.emit('logOut')

if __name__ == '__main__':
    with RetroSocket() as s:
        time.sleep(5)
