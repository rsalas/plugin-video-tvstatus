GROUP_ALL = 'all'
GROUP_ENDED = 'ended'
GROUP_CONTINUING = 'continuing'
GROUP_UPCOMING = 'upcoming'
GROUP_UNKNOWN = 'unknown'
GROUP_OTHER = 'other'

_ALL_GROUPS = (GROUP_ENDED, GROUP_CONTINUING, GROUP_UPCOMING, GROUP_UNKNOWN, GROUP_OTHER)

_GROUP_MEMBERS = {
    GROUP_ENDED: {'ended', 'cancelled', 'canceled'},
    GROUP_CONTINUING: {
        'returning series', 'continuing', 'in production',
        'post production', 'on air',
    },
    GROUP_UPCOMING: {'planned', 'pilot', 'rumored', 'in development'},
}

_STATUS_STRING_IDS = {
    'ended': 30030,
    'cancelled': 30031,
    'canceled': 30032,
    'continuing': 30033,
    'returning series': 30034,
    'in production': 30035,
    'post production': 30036,
    'planned': 30037,
    'pilot': 30038,
    'rumored': 30039,
    'in development': 30040,
}

_GROUP_STRING_IDS = {
    GROUP_ALL: 30020,
    GROUP_ENDED: 30021,
    GROUP_CONTINUING: 30022,
    GROUP_UPCOMING: 30023,
    GROUP_UNKNOWN: 30024,
    GROUP_OTHER: 30025,
}


def normalize(status):
    if not status:
        return GROUP_UNKNOWN
    key = str(status).strip().lower()
    if not key:
        return GROUP_UNKNOWN
    for group, members in _GROUP_MEMBERS.items():
        if key in members:
            return group
    return GROUP_OTHER


def status_string_id(status):
    return _STATUS_STRING_IDS.get(str(status or '').strip().lower())


def group_string_id(group):
    return _GROUP_STRING_IDS.get(group)


def all_groups():
    return _ALL_GROUPS
