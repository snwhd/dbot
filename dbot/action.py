import enum


class BotAction(enum.Enum):
    none = 'none'
    party_up = 'party up'
    grind = 'grind'


class ActionState(enum.Enum):
    none = 'none'

    # party up
    waiting_for_players = 'waiting for players'
    selecting_player = 'selecting player'
    inviting_player = 'inviting player'
    moving_to_leader = 'moving to leader'
    awaiting_invite = 'awaiting invite'
    accepted_party = 'accepted party'
    joined_party = 'joined party'


class GrindTarget(enum.Enum):
    none = 'none'
    field1 = 'field1'
    field2 = 'field2'
    cave1 = 'cave1'
    cave2 = 'cave2'
    gobble = 'gobble'
    bday_cave = 'bday cave'
    bday_rush = 'bday rush'

