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
    """ Base for all event types """

    def __init__(
        self,
        name: str,
    ) -> None:
        self.event_name = name

#
# general
#


class Connected(GameEvent):
    """ Websocket connected """

    def __init__(self) -> None:
        super().__init__('connected')


class SignedIn(GameEvent):
    """ This player signed in successfully """

    def __init__(
        self,
        uuid: str,
    ) -> None:
        super().__init__('signedIn')
        self.uuid = uuid


class PlayerSignedIn(GameEvent):
    """ A player has signed in """

    def __init__(
        self,
        player: PlayerData,
    ) -> None:
        super().__init__('playerSignedIn')
        self.player = player


class PlayerPreviouslySignedIn(GameEvent):
    """ List of players already signed in """

    def __init__(
        self,
        players: List[PlayerData],
    ) -> None:
        super().__init__('playerPreviouslySignedIn')
        self.players = players


# class SelectableCharacters
# class TotalCharacters
# class CharacterSelectHasPagination


class StartCharacterSelect(GameEvent):
    """ Display character select screen """

    def __init__(self) -> None:
        super().__init__('startCharacterSelect')


class Update(GameEvent):
    """ Used to update all kinds of client side key-value pairs """

    def __init__(
        self,
        key: str,
        value: Union[int, str],
    ) -> None:
        super().__init__('update')
        self.value = value
        self.key = key


#
# movement
#


class MovePlayer(GameEvent):
    """ Some player moved """

    def __init__(
        self,
        direction: Direction,
        username: str,
    ) -> None:
        super().__init__('movePlayer')
        self.direction = direction
        self.username = username


class Bonk(GameEvent):
    """ Bonked a wall """

    def __init__(self) -> None:
        super().__init__('bonk')


class Transport(GameEvent):
    """ Teleport to coords within map """

    def __init__(
        self,
        x: int,
        y: int,
    ) -> None:
        super().__init__('transport')
        self.x = x
        self.y = y


class JoinMap(GameEvent):
    """ This player has joined the map """

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__('joinMap')
        self.map_name = name


class LeaveMap(GameEvent):
    """ This player has left the current map """

    def __init__(self) -> None:
        super().__init__('leaveMap')


class PlayerLeftMap(GameEvent):
    """ A player left the current map """

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('playerLeftMap')
        self.username = username


#
# players
#


class PlayerUpdate(GameEvent):
    """ Updates player-specific key-value pairs """

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


class SelectPlayer(GameEvent):
    """ A player has been selected -> display menu """

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('selectPlayer')
        self.username = username


#
# parties
#


class InvitePlayer(GameEvent):
    """ A player has been invited to a party """ # TODO

    def __init__(
        self,
        username: str,
    ) -> None:
        super().__init__('invitePlayer')
        self.username = username


class Party(GameEvent):
    """ A new player joines the party """

    def __init__(
        self,
        party: List[str],
        party_id: int,
    ) -> None:
        super().__init__('party')
        self.party_id = party_id
        self.party = party

#
# pvp battles
#


class ChallengePlayer(GameEvent):
    """ A battle request is sent """
    # TODO

    def __init__(self) -> None:
        super().__init__('challengePlayer')


#
# monster battles
#


class StartBattle(GameEvent):

    def __init__(self) -> None:
        super().__init__('startBattle')


class LeaveBattle(GameEvent):

    def __init__(self) -> None:
        super().__init__('leaveBattle')


#
# trades
#


class RequestPlayer(GameEvent):
    """ A trade request is sent """
    # TODO

    def __init__(self) -> None:
        super().__init__('requestPlayer')


class StartTrade(GameEvent):
    """ Trade was accepted, begin trade """

    def __init__(self) -> None:
        super().__init__('startTrade')


class LeaveTrade(GameEvent):
    """ Exit trade for any reason """

    def __init__(self) -> None:
        super().__init__('leaveTrade')


#
# chat
#


class Message(GameEvent):
    """ A chat message """

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


#
# banking
#


class OpenBank(GameEvent):
    """ Bank UI has been opened """

    def __init__(self) -> None:
        super().__init__('openBank')


class CloseBank(GameEvent):
    """ Bank UI has been closed """

    def __init__(self) -> None:
        super().__init__('closeBank')

