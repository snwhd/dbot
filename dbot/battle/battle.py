from __future__ import annotations
import enum
import logging

from dbot.common.type_help import *


class BattleEventType(enum.Enum):

    ...


class Targetable:

    def __init__(
        self,
        typ_: str,
        group: str,
        index: int,
    ) -> None:
        self.type = typ_
        self.group = group
        self.index = index


class BattleEvent:

    def __init__(
        self,
        typ_: str,
        *args,
        **kwargs,
    ) -> None:
        self.type = typ_
        self.values = kwargs

    # TODO: typing for events

    #
    # decoding
    #

    @classmethod
    def decode_from(
        cls,
        data: Dict[str, Any],
    ) -> BattleEvent:
        typ_ = expect_str_in(data, 'type')
        if typ_ == 'start':
            return cls.decode_start(data)
        if typ_ == 'ability':
            return cls.decode_ability(data)
        if typ_ == 'damage':
            return cls.decode_damage(data)
        if typ_ == 'death':
            return cls.decode_death(data)
        if typ_ == 'victory':
            return cls.decode_victory(data)
        if typ_ == 'gold':
            return cls.decode_gold(data)
        if typ_ == 'experience':
            return cls.decode_experience(data)
        logging.warning(f'did not decode battle event: {data}')
        return BattleEvent(typ_)

    @classmethod
    def decode_start(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'start',
            start=expect_int_in(data, 'start'),
        )

    @classmethod
    def decode_ability(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'ability',
            caster=cls.decode_targetable(data['caster']),
            target=cls.decode_targetable(data['target']),
            ability=expect_str_in(data, 'ability'),
            new_mp=expect_int_in(data, 'newMP'),
            caster_name=expect_str_in(data, 'casterName'),
            target_name=expect_str_in(data, 'targetName'),
        )

    @classmethod
    def decode_damage(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'damage',
            amount=expect_int_in(data, 'amount'),
            guarded=expect_bool_in(data, 'guarded'),
            recipient=cls.decode_targetable(data['recipient']),
            recipient_name=expect_str_in(data, 'recipientName'),
        )

    @classmethod
    def decode_death(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'death',
            recipient=cls.decode_targetable(data['recipient']),
            recipient_name=expect_str_in(data, 'recipientName'),
        )

    @classmethod
    def decode_victory(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'start',
            escaped=expect_bool_in(data, 'escaped'),
        )

    @classmethod
    def decode_gold(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'gold',
            gold=expect_int_in(data, 'gold'),
        )

    @classmethod
    def decode_experience(
        cls,
        data: Dict[str, Any],
     ) -> BattleEvent:
        return BattleEvent(
            'experience',
            escaped=expect_int_in(data, 'experience'),
        )

    @classmethod
    def decode_targetable(
        cls,
        data: Dict[str, Any],
    ) -> Targetable:
        return Targetable(
            expect_str_in(data, 'type'),
            expect_str_in(data, 'group'),
            expect_int_in(data, 'index'),
        )


class Battle:

    def __init__(
        self,
    ) -> None:
        ...
