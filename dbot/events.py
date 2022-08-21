from typing import (
    List,
    Optional,
    Union,
)

from .common import (
    Direction,
    PlayerData,
)


class GameEvent:

    def __init__(
        self,
        name: str,
    ) -> None:
        self.event_name = name


class Connected(GameEvent):

    def __init__(self) -> None:
        super().__init__('connected')


class SignedIn(GameEvent):

    def __init__(
        self,
        uuid: str,
    ) -> None:
        super().__init__('signedIn')
        self.uuid = uuid


class StartCharacterSelect(GameEvent):

    def __init__(self) -> None:
        super().__init__('startCharacterSelect')


class PlayerSignedIn(GameEvent):

    def __init__(
        self,
        player: PlayerData,
    ) -> None:
        super().__init__('playerSignedIn')
        self.player = player


class PlayerPreviouslySignedIn(GameEvent):

    def __init__(
        self,
        players: List[PlayerData],
    ) -> None:
        super().__init__('playerPreviouslySignedIn')
        self.players = players


# class SelectableCharacters
# class TotalCharacters
# class CharacterSelectHasPagination


class JoinMap(GameEvent):

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__('joinMap')
        self.map_name = name


class PlayerUpdate(GameEvent):

    def __init__(
        self,
        username: str,
        key: str,
        value: Union[int, str],
    ) -> None:
        super().__init__('playerUpdate')
        self.username = username
        self.value = value
        self.key = key


class MovePlayer(GameEvent):

    def __init__(
        self,
        direction: Direction,
        username: str,
    ) -> None:
        super().__init__('movePlayer')
        self.direction = direction
        self.username = username


class Bonk(GameEvent):

    def __init__(self) -> None:
        super().__init__('bonk')


class Update(GameEvent):

    def __init__(
        self,
        key: str,
        value: Union[int, str],
    ) -> None:
        super().__init__('update')
        self.value = value
        self.key = key


class OpenBank(GameEvent):

    def __init__(self) -> None:
        super().__init__('openBank')


class Transport(GameEvent):

    def __init__(
        self,
        x: int,
        y: int,
    ) -> None:
        super().__init__('transport')
        self.x = x
        self.y = y


class PlayerLeftMap(GameEvent):

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('playerLeftMap')
        self.username = username


class LeaveMap(GameEvent):

    def __init__(self) -> None:
        super().__init__('leaveMap')


class SelectPlayer(GameEvent):

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('selectPlayer')
        self.username = username


class InvitePlayer(GameEvent):

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('invitePlayer')
        self.username = username


class Party(GameEvent):

    def __init__(
        self,
        party: List[str],
        party_id: int,
    ) -> None:
        super().__init__('party')
        self.party_id = party_id
        self.party = party


class Message(GameEvent):

    def __init__(
        self,
        channel: str,
        cierra: bool,
        contents: str,
        mid: int,
        months_subscribed: Optional[int],
        permissions: int,
        subscriber: bool,
        username: str,
        warning: bool,
    ) -> None:
        super().__init__('message')
        self.channel = channel
        self.cierra = cierra
        self.contents = contents
        self.mid = mid
        self.months_subscribed = months_subscribed
        self.permissions = permissions
        self.subscriber = subscriber
        self.username = username
        self.warning = warning
