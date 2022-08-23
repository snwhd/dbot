from __future__ import annotations
from typing import (
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

import logging
import time
import traceback

import dbot.network.events as events
from dbot.network.retrosocket import RetroSocket

from dbot.state.party import Party
from dbot.state.state import GameState
from dbot.state.uistate import UIState

from dbot.chat_commands import CommandHandler

from dbot.battle.battle import Battle
from dbot.battle.battle_controller import (
    BattleController,
    SimpleClericController,
)

from dbot.actions.action import Action
from dbot.actions.map_action import MapAction
from dbot.actions.party_action import PartyAction
from dbot.actions.grind_action import (
    GrindAction,
    GrindTarget,
)

from dbot.config import BotConfig
from dbot.common.type_help import *
from dbot.movement.pathfinding import Point
from dbot.movement.movement import MovementController
from dbot.common.common import (
    Direction,
    Player,
    UIPositions,
)


class BotCore:
    """ The bare essentials of a bot

        All of the necessaru game state, socket setup, event loop, etc
        are created, but has no real in-game functionality.
    """

    def __init__(
        self,
        config: BotConfig,
    ) -> None:
        self.config = config
        self.name = config.name
        self.admins = config.admins
        self.friends = config.friends

        # network
        self._socket: Optional[RetroSocket] = None
        self.logging_out = False

        # gamestate
        self.battle: Optional[Battle] = None
        self.party = Party(self, [self.name])
        self.state = GameState()
        self.ui = UIState()

        # controllers
        self.battler : BattleController = SimpleClericController(self)
        self.mover = MovementController(self)

    #
    # network properties
    #

    @property
    def socket(self) -> RetroSocket:
        if self._socket is not None:
            return self._socket
        raise RuntimeError('not connected')

    #
    # convenience properties
    #

    @property
    def me(self) -> Player:
        p = self.state.get_player(self.name)
        assert p is not None
        return p

    @property
    def position(self) -> Point:
        return (
            int(self.me['coords']['x']),
            int(self.me['coords']['y']),
        )

    @property
    def logged_in_friends(self) -> List[str]:
        logged_in: List[str] = []
        for friend in self.friends:
            assert friend != self.name
            if friend in self.state.players:
                logged_in.append(friend)
        return list(sorted(logged_in))

    @property
    def logged_in_bots(self) -> List[str]:
        return list(sorted(
            [self.name] + self.logged_in_friends
        ))

    @property
    def is_bot_leader(self) -> bool:
        return self.logged_in_bots[0] == self.name

    @property
    def is_in_battle(self) -> bool:
        return self.battle is not None

    #
    # main loop
    #

    def run_forever(self) -> None:

        n_errors = 0
        last_action = 0.0
        loop_timeout = 0.2
        action_timeout = 0.5

        with RetroSocket() as s:
            self._socket = s
            try:
                while not self.logging_out:
                    now = time.time()
                    do_action = (now - last_action) > action_timeout
                    self.do_step(do_action)
                    if do_action:
                        last_action = now
                    time.sleep(loop_timeout)
            except KeyboardInterrupt as e:
                s.send_logout()
                time.sleep(1)
                return
            except Exception as e:
                n_errors += 1
                if n_errors > self.config.max_errors:
                    logging.error('hit max errors')
                    raise e
                else:
                    self.warn_exception(e)
            finally:
                self._socket = None

    def do_step(
        self,
        do_actions: bool,
    ) -> None:
        while not self.socket.event_queue.empty():
            # handle all new events
            event = self.socket.event_queue.get()
            self.handle_event(event)

        if do_actions:
            # then do any actions
            if self.is_in_battle:
                self.battler.step()
            else:
                self.mover.step()
                self.step()

    def step(self) -> None:
        # To be implemented by bots
        ...

    def handle_event(
        self,
        event: events.GameEvent,
    ) -> None:
        handler_name = f'on_{event.event_name}'
        self.dispatch_handlers(handler_name, event)

    def dispatch_handlers(
        self,
        handler_name: str,
        *args,
    ) -> None:
        # always call ui handlers
        self.call_handler(self.ui, handler_name, *args)

        # call either battle or movement events
        if self.is_in_battle:
            self.call_handler(self.battler, handler_name, *args)
        else:
            self.call_handler(self.mover, handler_name, *args)

        # finally check bot handlers
        self.call_handler(self, handler_name, *args)

    def call_handler(
        self,
        obj: object,
        handler_name,
        *args,
    ) -> None:
        handler = getattr(obj, handler_name, None)
        backup = getattr(obj, 'catch_all_handler', None)
        if handler is not None:
            handler(*args)
        elif backup is not None:
            backup(*args)

    #
    # logging
    #

    def warn_exception(
        self,
        e: Exception,
    ) -> None:
        logging.warning('\n'.join([
            '--- exception in dbot ---',
            traceback.format_exc(),
            '-------------------------',
        ]))


class BasicBot(BotCore):
    """ A simple bot that can respond to commands

        GameEvent handlers to keep game state in sync along with
        basic chat command functionality and action queue.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        # actions
        self.commands = CommandHandler(self, config.command_prompt)
        self.commands.add_default_commands()
        self.action_queue: List[Action] = []


        # TODO: put this somewhere?
        self.report_channel = 'wsay'
        self.report_state = 'none'
        self.stopped_at_leave_map = False

    def step(self) -> None:
        if self.current_action is not None:
            complete = self.current_action.step()
            if complete:
                self.current_action.cleanup()
                self.action_queue.pop(0)

    #
    # commands and actions
    #

    @property
    def current_action(self) -> Optional[Action]:
        if len(self.action_queue) > 0:
            return self.action_queue[0]
        return None

    def enqueue_action(
        self,
        action: Action,
    ) -> None:
        self.action_queue.append(action)

    def clear_actions(self) -> None:
        if self.current_action is not None:
            self.current_action.cleanup()
        self.action_queue = []

    #
    # game state update handlers
    #

    def on_update(
        self,
        e: events.Update,
    ) -> None:
        """ core client state updates, passed on to onchange_* methods """
        self.state.vars[e.key] = e.value
        handler_name = f'onupdate_{e.key}'
        self.dispatch_handlers(handler_name, e.value)

    def on_playerUpdate(
        self,
        e: events.PlayerUpdate,
    ) -> None:
        player = self.state.get_player(e.username)
        if player is not None:
            player[e.key] = e.value
            if e.username != self.name:
                self.state.players_in_map.add(e.username)
        else:
            logging.warning(f'missing player moved: {e.username}')

    #
    # login flow
    #

    def on_connected(
        self,
        e: events.Connected,
    ) -> None:
        logging.info('connected, signing in')
        self.socket.emit('signIn', {
            'email': self.config.email,
            'password': self.config.password,
        })

    def on_signedIn(
        self,
        e: events.SignedIn,
    ) -> None:
        self.socket.send_keypress('enter')

    def on_startCharacterSelect(
        self,
        e: events.StartCharacterSelect,
    ) -> None:
        options = self.state.vars.get('selectableCharacters', [])
        if len(options) == 0:
            raise NotImplementedError('character creation')

        index = self.pick_character([
            (str(o['class']), int(o['level']))
            for o in options
        ])
        assert index < len(options)
        # TODO: other char's ui positions
        self.socket.send_click(*UIPositions.CHARACTER_ONE)

    def on_playerSignedIn(
        self,
        e: events.PlayerSignedIn,
    ) -> None:
        self.state.add_player(e.player)

    def on_playerPreviouslySignedIn(
        self,
        e: events.PlayerPreviouslySignedIn,
    ) -> None:
        for player in e.players:
            self.state.add_player(player)

    def on_joinMap(
        self,
        e: events.JoinMap,
    ) -> None:
        self.state.join_map(e.map_name)
        if self.stopped_at_leave_map and self.current_action is None:
            self.say(f'stopped at {e.map_name}', 'wsay')
            self.stopped_at_leave_map = False

    def on_leaveMap(
        self,
        e: events.LeaveMap,
    ) -> None:
        if self.mover.clear_goto():
            self.stopped_at_leave_map = True
        self.state.left_map()

    def on_playerLeftMap(
        self,
        e: events.PlayerLeftMap,
    ) -> None:
        self.state.left_map(e.username)

    #
    # movement
    #

    def on_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        # note: This method only updates player position in game stae,
        #       any logic about how this affects this bots movement is
        #       in movement.MovementController.on_movePlayer
        player = self.state.get_player(e.username)
        if player is None:
            logging.warning(f'missing player moved: ${e.username}')
            return

        if e.direction == Direction.down:
            player['coords']['y'] += 1
        if e.direction == Direction.up:
            player['coords']['y'] -= 1
        if e.direction == Direction.left:
            player['coords']['x'] -= 1
        if e.direction == Direction.right:
            player['coords']['x'] += 1

    #
    # battle
    #

    def on_startBattle(
        self,
        e: events.StartBattle,
    ) -> None:
        self.battle = Battle()
        self.battler.start()

    def on_leaveBattle(
        self,
        e: events.LeaveBattle,
    ) -> None:
        self.battler.leave()
        self.battle = None

    #
    # chat
    #

    def on_message(
        self,
        e: events.Message,
    ) -> None:
        try:
            self.commands.handle(e)
        except Exception as e:
            logging.warning(f'exception parsing command: {e}')
            traceback.print_exc()

    #
    # party
    #

    def on_party(
        self,
        e: events.Party,
    ) -> None:
        # TODO: do verification based on party id?
        if self.name in e.party:
            self.party.update_party(e.party)

    #
    # var updates
    #

    def onupdate_statsPrompted(
        self,
        prompted: bool,
    ) -> None:
        if prompted and self.report_state == 'waiting on stats':
            self.report_state = 'waiting on gold'
            self.socket.send_click(*UIPositions.INVENTORY_BUTTON)

    def onupdate_inventoryPrompted(
        self,
        prompted: bool,
    ) -> None:
        if prompted and self.report_state == 'waiting on gold':
            self.report_state = 'none'
            self.socket.send_click(*UIPositions.INVENTORY_BUTTON)
            self.report()

    #
    # convenience methods
    # and command implementations
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
        self.mover.goto(path)

    def logout(self) -> None:
        self.clear_actions()
        self.socket.send_logout()
        self.logging_out = True

    def report(
        self,
        prompt = '',
    ) -> None:
        gold = sum([
            int(self.state.vars.get('gold', 0)),
            int(self.state.vars.get('bankedGold', 0)),
        ])
        level = str(self.me.get('level', 0))
        self.say(f"I'm {prompt}level {level}, {gold} gold", self.report_channel)
        self.report_state = 'none'

    def check_stats_and_report(
        self,
        channel = 'wsay',
    ) -> None:
        self.report_channel = channel
        if self.is_in_battle:
            self.report('in battle, ')
        elif self.report_state == 'none':
            self.report_state = 'waiting on stats'
            self.socket.send_click(*UIPositions.STATS_BUTTON)

    def join_party(
        self,
        party: List[str],
    ) -> None:
        self.party.set_target(party)
        self.enqueue_action(PartyAction(self))

    def grind(
        self,
        target: GrindTarget,
    ) -> None:
        self.enqueue_action(GrindAction(self, target))

    def start_mapping(self) -> None:
        self.enqueue_action(MapAction(self))

    def stop(self) -> None:
        self.mover.clear_goto()
        self.clear_actions()

    #
    # ui interface
    #

    def click_at_tile(
        self,
        x: int,
        y: int,
    ) -> None:
        me = self.state.players[self.name]
        screen_x = 150 - (me['coords']['x'] - x) * 16
        screen_y = 120 - (me['coords']['y'] - y) * 16
        self.socket.send_click(screen_x, screen_y)

    #
    # for override
    #

    def pick_character(
        self,
        characters: List[Tuple[str, int]],
    ) -> int:
        return 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('botname')
    parser.add_argument('--config', type=str, default='config.json')
    parser.add_argument('--nerror', type=int, default=0)
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)

    config = BotConfig.from_file(args.config, args.botname)
    bot = BasicBot(config)
    bot.run_forever()
