import json
import os
import re
import shutil
import sqlite3
import time

import xbmc
import xbmcvfs

import statuses

PROPERTIES_FULL = [
    'title', 'originaltitle', 'sorttitle', 'plot', 'year', 'premiered',
    'art', 'thumbnail', 'fanart', 'rating', 'votes', 'mpaa', 'genre',
    'tag', 'studio', 'uniqueid', 'imdbnumber', 'watchedepisodes',
    'lastplayed', 'dateadded', 'playcount', 'trailer', 'runtime',
]

PROPERTIES_MINIMAL = [
    'title', 'plot', 'year', 'premiered', 'art', 'thumbnail', 'fanart',
    'rating', 'votes', 'genre', 'uniqueid', 'imdbnumber', 'watchedepisodes',
]

PROPERTIES_BASIC = [
    'title', 'year', 'premiered', 'art', 'thumbnail', 'fanart',
    'rating', 'votes', 'uniqueid',
]

_CACHE_TTL = 60
_cache = {'ts': 0.0, 'data': None}


def get_library():
    now = time.time()
    if _cache['data'] is not None and now - _cache['ts'] < _CACHE_TTL:
        return _cache['data']
    shows = _fetch_tvshows()
    status_map = _read_status_map()
    _attach_status(shows, status_map)
    shows.sort(key=lambda s: (s.get('title') or '').lower())
    _cache['ts'] = now
    _cache['data'] = shows
    return shows


def invalidate_cache():
    _cache['ts'] = 0.0
    _cache['data'] = None


def _rpc(payload):
    return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))


def _fetch_tvshows():
    tiers = (PROPERTIES_FULL, PROPERTIES_MINIMAL, PROPERTIES_BASIC)
    tier_index = 0
    properties = tiers[0]
    start = 0
    page = 500
    shows = []
    total = None
    while True:
        try:
            result = _rpc({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetTVShows',
                'params': {
                    'properties': properties,
                    'limits': {'start': start, 'end': start + page - 1},
                },
                'id': 1,
            })
        except Exception:
            result = None
        if not isinstance(result, dict) or 'error' in result:
            tier_index += 1
            if tier_index < len(tiers):
                properties = tiers[tier_index]
                start = 0
                shows = []
                total = None
                continue
            return []
        data = result.get('result') or {}
        batch = data.get('tvshows') or []
        shows.extend(batch)
        lim = data.get('limits') or {}
        if isinstance(lim.get('total'), int):
            total = lim['total']
        if not batch or len(batch) < page or (total is not None and len(shows) >= total):
            break
        start += page
        if total is not None and start >= total:
            break
    return shows


def _find_video_db():
    candidates = ['special://database', 'special://profile/Database', 'special://home/Database']
    for special in candidates:
        try:
            dirs, files = xbmcvfs.listdir(special)
        except Exception:
            continue
        best_ver = -1
        best = None
        for name in files:
            match = re.fullmatch(r'MyVideos(\d+)\.db', name)
            if match and int(match.group(1)) > best_ver:
                best_ver = int(match.group(1))
                best = name
        if best:
            return os.path.join(xbmcvfs.translatePath(special), best)
    return None


def _open_db(path):
    uri = 'file:' + path.replace(os.sep, '/') + '?mode=ro'
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        conn.execute('PRAGMA query_only = ON')
        return conn
    except sqlite3.Error:
        pass
    try:
        conn = sqlite3.connect(path, timeout=10)
        conn.execute('PRAGMA query_only = ON')
        return conn
    except sqlite3.Error:
        return None


def _copy_db_to_temp(db_path):
    try:
        tmpdir = xbmcvfs.translatePath('special://temp')
        base = os.path.basename(db_path)
        dest = os.path.join(tmpdir, 'tvstatus_' + base)
        shutil.copy2(db_path, dest)
        for suffix in ('-wal', '-shm'):
            src = db_path + suffix
            if os.path.exists(src):
                shutil.copy2(src, dest + suffix)
        return dest
    except Exception:
        return None


def _read_status_map():
    db_path = _find_video_db()
    if not db_path:
        return {}
    conn = _open_db(db_path)
    if conn is None:
        tmp = _copy_db_to_temp(db_path)
        if tmp:
            conn = _open_db(tmp)
    if conn is None:
        return {}
    try:
        rows = conn.execute('SELECT idShow, c02 FROM tvshow').fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    result = {}
    for row in rows:
        try:
            result[int(row[0])] = row[1] or ''
        except (TypeError, ValueError):
            continue
    return result


def _attach_status(shows, status_map):
    for show in shows:
        sid = _as_int(show.get('tvshowid'))
        raw = status_map.get(sid, '') if sid is not None else ''
        show['status'] = raw
        show['status_group'] = statuses.normalize(raw)
        show['title'] = show.get('title') or show.get('label') or ''
        show['year'] = _as_int(show.get('year'))
        show['tvshowid'] = sid


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def uniqueid(show, provider):
    uid = show.get('uniqueid')
    if isinstance(uid, dict):
        val = uid.get(provider)
        if isinstance(val, dict):
            val = val.get('value')
        if val:
            return str(val).strip()
    return ''


def imdb_id(show):
    val = show.get('imdbnumber') or uniqueid(show, 'imdb')
    val = str(val or '').strip()
    return val or None


def set_tvshow_status(tvshowid, status):
    try:
        tvshowid = int(tvshowid)
    except (TypeError, ValueError):
        return False
    payload = {
        'jsonrpc': '2.0',
        'method': 'VideoLibrary.SetTVShowDetails',
        'params': {'tvshowid': tvshowid, 'status': status},
        'id': 1,
    }
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
        return isinstance(result, dict) and 'error' not in result
    except Exception:
        return False
