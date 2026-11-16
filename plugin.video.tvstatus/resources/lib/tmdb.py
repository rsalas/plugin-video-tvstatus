import json
import os
import re
import time
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs

import kodilibrary

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

_SCRAPER_IDS = (
    'metadata.tvshows.themoviedb.org.python',
    'metadata.themoviedb.org.python',
)

_KEY_RE = re.compile(r"TMDB_API_KEY\s*=\s*['\"]([0-9a-fA-F]{32})['\"]")
_API_BASE = 'https://api.themoviedb.org/3'
_REQUEST_DELAY = 0.2
_last_request = [0.0]


def get_api_key():
    key = (ADDON.getSetting('tmdb_api_key') or '').strip()
    if key:
        return key
    try:
        if ADDON.getSettingBool('use_scraper_key'):
            return _scraper_key()
    except RuntimeError:
        pass
    return ''


def _scraper_key():
    for addon_id in _SCRAPER_IDS:
        try:
            if not xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id):
                continue
            path = xbmcvfs.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('path'))
        except Exception:
            continue
        if not path:
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
            for fname in files:
                if not fname.endswith('.py'):
                    continue
                try:
                    with open(os.path.join(root, fname), 'r', encoding='utf-8', errors='ignore') as handle:
                        match = _KEY_RE.search(handle.read())
                except OSError:
                    continue
                if match:
                    return match.group(1)
    return ''


def _throttle():
    elapsed = time.time() - _last_request[0]
    if elapsed < _REQUEST_DELAY:
        time.sleep(_REQUEST_DELAY - elapsed)
    _last_request[0] = time.time()


def _get_json(url):
    _throttle()
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Kodi/%s' % ADDON_ID,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


def _tmdb_id_from_imdb(show, api_key):
    imdb = kodilibrary.imdb_id(show)
    if not imdb:
        return None
    data = _get_json('%s/find/%s?external_source=imdb_id&api_key=%s' % (
        _API_BASE, urllib.parse.quote(imdb), api_key))
    results = data.get('tv_results') or []
    if results and results[0].get('id'):
        return str(results[0]['id'])
    return None


def get_show_status(show, api_key):
    tmdb_id = kodilibrary.uniqueid(show, 'tmdb')
    if not tmdb_id:
        try:
            tmdb_id = _tmdb_id_from_imdb(show, api_key)
        except Exception:
            return {'status': None, 'error': 'request'}
        if not tmdb_id:
            return {'status': None, 'error': 'no_id'}
    try:
        data = _get_json('%s/tv/%s?api_key=%s' % (_API_BASE, tmdb_id, api_key))
    except Exception:
        return {'status': None, 'error': 'request', 'tmdb_id': tmdb_id}
    status = data.get('status')
    if isinstance(status, str) and status.strip():
        return {'status': status.strip(), 'tmdb_id': tmdb_id}
    return {'status': None, 'error': 'empty', 'tmdb_id': tmdb_id}
