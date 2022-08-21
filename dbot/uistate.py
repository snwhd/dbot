import enum
import logging

import dbot.events as events
from dbot.retrosocket import RetroSocket



class UIScreen(enum.Enum):
    none = 'none'

    bank = 'bank'
    bank_storage = 'bank storage'
    bank_inventory = 'bank inventory'
    inv_inventory = 'inv inventory'
    inv_equipment = 'inv equipment'
    inv_cosmetics = 'inv cosmetics'

    player_select = 'player select'
    battle_invite = 'battle_invite'
    battle_prompt = 'battle_prompt'
    party_invite = 'party_invite'
    party_prompt = 'party_prompt'
    trade_invite = 'trade_invite'
    trade_prompt = 'trade_prompt'
    trade_items = 'trade items'
    trade_gold = 'trade gold'

    inn_prompt = 'inn prompt'
    npc_dialog = 'npc dialog'
    shop_shop = 'shop shop'
    shop_inventory = 'shop inventory'
    not_enough_gold = 'not enough gold'


class UIState:

    def __init__(self) -> None:
        self.screen = UIScreen.none
        self.source = ''
        self.target = ''
        self.page = 0

    def check_event(
        self,
        e: events.GameEvent,
    ) -> None:
        if isinstance(e, events.SelectPlayer):
            # Clicking on a player
            self.screen = UIScreen.player_select
            self.target = e.username
        if any([
            isinstance(e, events.ChallengePlayer),
            isinstance(e, events.InvitePlayer),
            isinstance(e, events.RequestPlayer),
        ]):
            # These are selected from UIScreen.player_select, and
            # each closes the select window.
            self.screen = UIScreen.none
        elif isinstance(e, events.OpenBank):
            # Bank always starts on the main screen
            self.screen = UIScreen.bank
        elif isinstance(e, events.CloseBank):
            # This is sent when bank is closed, not matter if it's the
            # bank screen or storage screen.
            self.screen = UIScreen.none
        elif isinstance(e, events.StartTrade):
            self.screen = UIScreen.trade_items
        elif isinstance(e, events.LeaveTrade):
            self.screen = UIScreen.none
        elif isinstance(e, events.Update):
            value = e.value
            key = e.key
            #
            # banking
            #
            if key == 'storageTab':
                # When vieweing bank storage, storageTab is what decides
                # if we are looking at storage or inventory. The storagePrompted
                # and inventoryPrompted can be ignored.
                if value == 'storage':
                    self.screen = UIScreen.bank_storage
                elif value == 'inventory':
                    self.screen = UIScreen.bank_inventory
            elif key == 'storagePage':
                self.page = int(value)
            elif key == 'bankPrompted' and value:
                # bankPrompted == True means we swapped back from
                # one of the bank storage screens.
                self.screen = UIScreen.bank
            #
            # trading
            #
            elif key == 'tradingTab':
                if value == 'items':
                    self.screen = UIScreen.trade_items
                elif value == 'gold':
                    self.screen = UIScreen.trade_gold
            #
            # shop
            #
            elif key == 'shopTab':
                if value == 'shop':
                    self.screen = UIScreen.shop_shop
                elif value == 'inventory':
                    self.screen = UIScreen.shop_inventory
            elif key == 'shopPrompted':
                if not value:
                    # False here means we exited completely, ignore True
                    # because it just conflicts with shopTab changes.
                    self.screen = UIScreen.none
            #
            # inn
            #
            elif key == 'shopPrompted':
                if value:
                    self.screen = UIScreen.inn_prompt
                else:
                    self.screen = UIScreen.none
            elif key == 'notEnoughGoldPrompted':
                if value:
                    self.screen = UIScreen.not_enough_gold
                else:
                    self.screen = UIScreen.none
            #
            # players
            #
            elif key == 'battlePromptedPlayerUsername':
                if value is None:
                    if self.screen == UIScreen.battle_prompt:
                        # The menu was closed, make sure we are switching
                        # from the expected menu to avoid race condition when
                        # accepting.
                        self.screen = UIScreen.none
                else:
                    # Somone is requesting a battle
                    self.screen = UIScreen.battle_prompt
                    self.source = str(value)
            elif key == 'partyPromptedPlayerUsername':
                if value is None:
                    if self.screen == UIScreen.party_prompt:
                        # The menu was closed, make sure we are switching
                        # from the expected menu to avoid race condition when
                        # accepting.
                        self.screen = UIScreen.none
                else:
                    # Somone is requesting a party
                    self.screen = UIScreen.party_prompt
                    self.source = str(value)
            elif key == 'tradePromptedPlayerUsername':
                if value is None:
                    if self.screen == UIScreen.trade_prompt:
                        # The menu was closed, make sure we are switching
                        # from the expected menu to avoid race condition when
                        # accepting.
                        self.screen = UIScreen.none
                else:
                    # Somone is requesting a trade
                    self.screen = UIScreen.trade_prompt
                    self.source = str(value)
