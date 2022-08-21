from typing import (
    Callable,
    List,
)

import enum
import logging

import dbot.events as events
from dbot.retrosocket import RetroSocket



class UIScreen(enum.Enum):
    none = 'none'

    main_menu = 'main menu'
    character_select = 'characte select'

    bank = 'bank'
    bank_storage = 'bank storage'
    bank_inventory = 'bank inventory'
    inv_inventory = 'inv inventory'
    inv_equipment = 'inv equipment'
    inv_cosmetics = 'inv cosmetics'

    player_select = 'player select'
    battle_invite = 'battle invite'
    battle_prompt = 'battle prompt'
    party_invite = 'party invite'
    party_prompt = 'party prompt'
    trade_invite = 'trade invite'
    trade_prompt = 'trade prompt'
    trade_items = 'trade items'
    trade_gold = 'trade gold'

    inn_prompt = 'inn prompt'
    npc_dialog = 'npc dialog'
    shop_shop = 'shop shop'
    shop_inventory = 'shop inventory'
    not_enough_gold = 'not enough gold'


class UIState:

    def __init__(self) -> None:
        self._screen = UIScreen.none
        self.source = ''
        self.target = ''
        self.page = 0

        # A list of methods that check an event.GameEvent for ui
        # state changes / transitions.
        self.state_changes: List[Callable[[events.GameEvent], bool]] = [
            self.check_bank,
            self.check_battle_prompt,
            self.check_inn_prompt,
            self.check_party_prompt,
            self.check_player_select,
            self.check_shop,
            self.check_trade,
        ]

    @property
    def screen(self) -> UIScreen:
        return self._screen

    @screen.setter
    def screen(self, s: UIScreen) -> None:
        logging.info(f'new UI screen: {s.value}')
        self._screen = s

    def in_bank(self) -> bool:
        return self.screen in {
            UIScreen.bank,
            UIScreen.bank_storage,
            UIScreen.bank_inventory,
        }

    def in_trade(self) -> bool:
        return self.screen in {
            UIScreen.trade_prompt,
            UIScreen.trade_items,
            UIScreen.trade_gold,
        }

    def in_shop(self) -> bool:
        return self.screen in {
            UIScreen.shop_shop,
            UIScreen.shop_inventory,
        }

    def in_inventory(self) -> bool:
        return self.screen in {
            UIScreen.inv_inventory,
            UIScreen.inv_equipment,
            UIScreen.inv_cosmetics,
        }

    def check_event(
        self,
        e: events.GameEvent,
    ) -> None:
        """ entry point for checking an event for any ui state change """
        for function in self.state_changes:
            if function(e):
                # we should only trigger one state change at a time, ever
                # TODO: add a debug mode to verify this
                break

    #
    # player select
    #

    def check_player_select(
        self,
        e: events.GameEvent,
    ) -> bool:
        if isinstance(e, events.SelectPlayer):
            # Clicking on a player
            self.screen = UIScreen.player_select
            self.target = e.username
            return True
        elif any([
            isinstance(e, events.ChallengePlayer),
            isinstance(e, events.InvitePlayer),
            isinstance(e, events.RequestPlayer),
        ]):
            # These are selected from UIScreen.player_select, and
            # each closes the select window.
            self.screen = UIScreen.none
            return True
        return False

    #
    # bank
    #

    def check_bank(
        self,
        e: events.GameEvent,
    ) -> bool:
        if isinstance(e, events.OpenBank):
            # Bank always starts on the main screen
            self.screen = UIScreen.bank
            return True
        elif isinstance(e, events.CloseBank):
            # This is sent when bank is closed, not matter if it's the
            # bank screen or storage screen.
            self.screen = UIScreen.none
            return True
        elif isinstance(e, events.Update) and self.in_bank():
            return self.check_bank_update(e)
        return False

    def check_bank_update(
        self,
        e: events.Update,
    ) -> bool:
        key = e.key
        value = e.value
        if key == 'storageTab':
            # When vieweing bank storage, storageTab is what decides
            # if we are looking at storage or inventory. The storagePrompted
            # and inventoryPrompted can be ignored.
            if value == 'storage':
                self.screen = UIScreen.bank_storage
                return True
            elif value == 'inventory':
                self.screen = UIScreen.bank_inventory
                return True
        elif key == 'storagePage':
            self.page = int(value)
            return True
        elif key == 'bankPrompted' and value:
            # bankPrompted == True means we swapped back from
            # one of the bank storage screens.
            self.screen = UIScreen.bank
            return True
        return False

    #
    # trade
    #

    def check_trade(
        self,
        e: events.GameEvent,
    ) -> bool:
        if isinstance(e, events.StartTrade):
            self.screen = UIScreen.trade_items
            return True
        elif isinstance(e, events.LeaveTrade):
            self.screen = UIScreen.none
            return True
        elif isinstance(e, events.Update) and self.in_trade():
            return self.check_trade_update(e)
        return False

    def check_trade_update(
        self,
        e: events.Update,
    ) -> bool:
        key = e.key
        value = e.value
        if key == 'tradingTab':
            if value == 'items':
                self.screen = UIScreen.trade_items
                return True
            elif value == 'gold':
                self.screen = UIScreen.trade_gold
                return True
        return False

    def check_trade_prompt(
        self,
        e: events.GameEvent,
    ) -> bool:
        """ check if we are opening / changing trade prompt """
        if isinstance(e, events.Update):
            return self.check_trade_update(e)
        return False

    def check_trade_prompt_update(
        self,
        e: events.Update,
    ) -> bool:
        """ check if update changes trade state """
        key = e.key
        value = e.value
        if key == 'tradePromptedPlayerUsername':
            if value is None:
                if self.screen == UIScreen.trade_prompt:
                    # The menu was closed, make sure we are switching
                    # from the expected menu to avoid race condition when
                    # accepting.
                    self.screen = UIScreen.none
                    return True
            else:
                # Somone is requesting a trade
                self.screen = UIScreen.trade_prompt
                self.source = str(value)
                return True
        return False

    #
    # shop
    #

    def check_shop(
        self,
        e: events.GameEvent,
    ) -> bool:
        """ check if we are opening / changing shop state """
        if isinstance(e, events.Update):
            return self.check_shop_update(e)
        return False

    def check_shop_update(
        self,
        e: events.Update,
    ) -> bool:
        """ check if update changes shop state """
        key = e.key
        value = e.value
        if key == 'shopTab':
            if value == 'shop':
                self.screen = UIScreen.shop_shop
                return True
            elif value == 'inventory':
                self.screen = UIScreen.shop_inventory
                return True
        elif key == 'shopPrompted':
            if not value:
                # False here means we exited completely, ignore True
                # because it just conflicts with shopTab changes.
                self.screen = UIScreen.none
                return True
        return False

    #
    # inn - prompt only
    #

    def check_inn_prompt(
        self,
        e: events.GameEvent,
    ) -> bool:
        """ check if we are opening / changing inn prompt """
        if isinstance(e, events.Update):
            return self.check_inn_prompt_update(e)
        return False

    def check_inn_prompt_update(
        self,
        e: events.Update,
    ) -> bool:
        """ check if update changes inn state """
        key = e.key
        value = e.value
        if key == 'innPrompted':
            if value:
                self.screen = UIScreen.inn_prompt
                return True
            else:
                self.screen = UIScreen.none
                return True
        elif key == 'notEnoughGoldPrompted':
            if value:
                self.screen = UIScreen.not_enough_gold
                return True
            else:
                self.screen = UIScreen.none
                return True
        return False

    #
    # battle - prompt only
    #

    def check_battle_prompt(
        self,
        e: events.GameEvent,
    ) -> bool:
        """ check if we are opening / changing battle prompt """
        if isinstance(e, events.Update):
            return self.check_battle_prompt_update(e)
        return False

    def check_battle_prompt_update(
        self,
        e: events.Update,
    ) -> bool:
        """ check if update changes battle state """
        key = e.key
        value = e.value
        if key == 'battlePromptedPlayerUsername':
            if value is None:
                if self.screen == UIScreen.battle_prompt:
                    # The menu was closed, make sure we are switching
                    # from the expected menu to avoid race condition when
                    # accepting.
                    self.screen = UIScreen.none
                    return True
            else:
                # Somone is requesting a battle
                self.screen = UIScreen.battle_prompt
                self.source = str(value)
                return True
        return False

    #
    # party - prompt only
    #

    def check_party_prompt(
        self,
        e: events.GameEvent,
    ) -> bool:
        """ check if we are opening / changing party prompt """
        if isinstance(e, events.Update):
            return self.check_party_prompt_update(e)
        return False

    def check_party_prompt_update(
        self,
        e: events.Update,
    ) -> bool:
        """ check if update changes party state """
        key = e.key
        value = e.value
        if key == 'partyPromptedPlayerUsername':
            if value is None:
                if self.screen == UIScreen.party_prompt:
                    # The menu was closed, make sure we are switching
                    # from the expected menu to avoid race condition when
                    # accepting.
                    self.screen = UIScreen.none
                    return True
            else:
                # Somone is requesting a party
                self.screen = UIScreen.party_prompt
                self.source = str(value)
                return True
        return False

