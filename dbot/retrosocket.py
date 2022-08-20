#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Optional,
)

import socketio
import time

from .event import *


class GlobalNamespace(socketio.ClientNamespace):

    def __init__(
        self,
        event_queue: Queue,
        *args,
        **kwargs,
    ) -> None:
        ...

    def trigger_event(self, event, *args):
        handler_name = f'on_{event}'
        if hasattr(self, handler_name):
            return getattr(self, handler_name)(*args)
        return self.catch_all(event, *args)

    def catch_all(self, event, data):
        print(f'not handled: {event}')

    def on_connect(self):
        print('connected')
        self.emit('signIn', {
        })

    def on_disconnect(self):
        print('disconnected')

    def on_signedIn(self, data):
        print('onSignedIn')


class RetroSocket:

    def __init__(
        self,
        host = 'retrommo-bots.herokuapp.com',
        port = 443,
    ) -> None:
        self.connected = False
        self.host = host
        self.port = port

        namespace = GlobalNamespace('/')
        namespace.

        self.socket = socketio.Client()
        self.socket.register_namespace(GlobalNamespace('/'))

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


if __name__ == '__main__':
    with RetroSocket() as s:
        time.sleep(5)
