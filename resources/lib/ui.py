import urllib.parse
from collections import Counter

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import kodilibrary
import statuses
import tmdb

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

HANDLE = None
BASE_URL = None


def setup(handle, base_url):
    global HANDLE, BASE_URL
    HANDLE = handle
    BASE_URL = base_url


def _L(string_id):
    return ADDON.getLocalizedString(string_id)


def _url(**params):
    return '%s?%s' % (BASE_URL, urllib.parse.urlencode(params))


def _add_item(label, label2, url, is_folder, icon=None):
    list_item = xbmcgui.ListItem(label=label, label2=label2 or '', path=url, offscreen=True)
    if icon:
        list_item.setArt({'icon': icon})
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)


def _status_display(raw):
    raw = (raw or '').strip()
    if not raw:
        return _L(30024)
    string_id = statuses.status_string_id(raw)
    if string_id:
        return _L(string_id)
    return raw


def _group_label(group):
    string_id = statuses.group_string_id(group)
    return _L(string_id) if string_id else group


def _counts_by_group(shows):
    counts = Counter()
    for show in shows:
        counts[show.get('status_group') or statuses.GROUP_UNKNOWN] += 1
    return counts


def _filter_count(shows, filter_key):
    return sum(1 for show in shows if _match(show, filter_key))


def _match(show, filter_key):
    if not filter_key or filter_key == statuses.GROUP_ALL:
        return True
    if filter_key.startswith('status:'):
        return (show.get('status') or '').strip().lower() == filter_key[len('status:'):].lower()
    return show.get('status_group') == filter_key


def _filter_title(filter_key):
    if filter_key.startswith('status:'):
        return _status_display(filter_key[len('status:'):])
    if filter_key == statuses.GROUP_ALL:
        return _L(30020)
    return _group_label(filter_key)


def _art_dict(show):
    art = show.get('art')
    if not isinstance(art, dict):
        art = {}
    thumb = art.get('thumb') or show.get('thumbnail') or art.get('poster')
    result = {}
    values = {
        'thumb': thumb,
        'fanart': show.get('fanart') or art.get('fanart'),
        'poster': art.get('poster') or thumb,
        'banner': art.get('banner'),
    }
    for key, value in values.items():
        if value:
            result[key] = value
    return result


def _info_dict(show, title):
    info = {'title': title, 'mediatype': 'tvshow'}
    if show.get('plot'):
        info['plot'] = show['plot']
    if show.get('premiered'):
        info['premiered'] = show['premiered']
    if show.get('year'):
        info['year'] = show['year']
    genre = show.get('genre')
    if genre:
        info['genre'] = genre if isinstance(genre, list) else [genre]
    try:
        if show.get('rating'):
            info['rating'] = float(show['rating'])
    except (TypeError, ValueError):
        pass
    if show.get('votes'):
        info['votes'] = show['votes']
    if show.get('mpaa'):
        info['mpaa'] = show['mpaa']
    return info


def _add_show_item(show):
    title = show.get('title') or ''
    has_status = bool((show.get('status') or '').strip())
    status_disp = _status_display(show.get('status'))
    label = title
    if has_status and ADDON.getSettingBool('show_status_suffix'):
        label = '%s [%s]' % (title, status_disp)
    sid = show.get('tvshowid')
    if sid:
        url = 'videodb://tvshows/titles/%d/' % sid
        is_folder = True
    else:
        url = _url(mode='noop')
        is_folder = False
    list_item = xbmcgui.ListItem(label=label, label2=status_disp, path=url, offscreen=True)
    art = _art_dict(show)
    if art:
        list_item.setArt(art)
    list_item.setInfo('video', _info_dict(show, title))
    if sid:
        list_item.addContextMenuItems([(
            _L(30070),
            'RunPlugin(%s)' % _url(mode='refreshone', id=sid),
        )])
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)


def show_root():
    xbmcplugin.setPluginCategory(HANDLE, _L(30001))
    shows = kodilibrary.get_library()
    counts = _counts_by_group(shows)
    total = len(shows)

    if total == 0:
        _add_item(_L(30015), '', _url(mode='noop'), False)

    _add_item(_L(30010), str(counts.get(statuses.GROUP_ENDED, 0)),
              _url(mode='shows', filter=statuses.GROUP_ENDED), True, 'DefaultTVShows.png')

    default_filter = ADDON.getSetting('default_filter') or statuses.GROUP_ALL
    browse_count = total if default_filter == statuses.GROUP_ALL else _filter_count(shows, default_filter)
    _add_item(_L(30011), str(browse_count),
              _url(mode='shows', filter=default_filter), True, 'DefaultTVShows.png')

    _add_item(_L(30012), '', _url(mode='filters'), True, 'DefaultUser.png')
    _add_item(_L(30013), '', _url(mode='refresh'), True, 'DefaultHardDisk.png')
    _add_item(_L(30014), '', _url(mode='settings'), False, 'DefaultUser.png')
    xbmcplugin.endOfDirectory(HANDLE)


def show_listing(filter_key):
    filter_key = filter_key or statuses.GROUP_ALL
    xbmcplugin.setPluginCategory(HANDLE, _filter_title(filter_key))
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.addSortMethod(HANDLE,
                             xbmcplugin.SORT_METHOD_LABEL |
                             xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE |
                             xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    shows = [show for show in kodilibrary.get_library() if _match(show, filter_key)]
    if not shows:
        _add_item(_L(30078), '', _url(mode='noop'), False)
    for show in shows:
        _add_show_item(show)
    xbmcplugin.endOfDirectory(HANDLE)


def show_filters():
    xbmcplugin.setPluginCategory(HANDLE, _L(30012))
    shows = kodilibrary.get_library()
    counts = _counts_by_group(shows)
    _add_item(_L(30020), str(len(shows)), _url(mode='shows', filter=statuses.GROUP_ALL), True)
    for group in statuses.all_groups():
        _add_item(_group_label(group), str(counts.get(group, 0)),
                  _url(mode='shows', filter=group), True)
    _add_item(_L(30026), '', _url(mode='rawfilters'), True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_raw_filters():
    xbmcplugin.setPluginCategory(HANDLE, _L(30026))
    counts = Counter()
    seen = {}
    for show in kodilibrary.get_library():
        raw = (show.get('status') or '').strip()
        if not raw:
            continue
        key = raw.lower()
        counts[key] += 1
        seen.setdefault(key, raw)
    for key, count in sorted(counts.items(), key=lambda item: -item[1]):
        _add_item(_status_display(seen[key]), str(count),
                  _url(mode='shows', filter='status:' + key), True)
    xbmcplugin.endOfDirectory(HANDLE)


def _needs_update(old_status, new_status):
    if not old_status:
        return True
    return statuses.normalize(old_status) != statuses.normalize(new_status)


def _apply_status(show, new_status):
    if kodilibrary.set_tvshow_status(show.get('tvshowid'), new_status):
        show['status'] = new_status
        show['status_group'] = statuses.normalize(new_status)
        return True
    return False


def run_refresh():
    title = _L(30001)
    api_key = tmdb.get_api_key()
    if not api_key:
        xbmcgui.Dialog().ok(title, _L(30074))
        show_root()
        return
    shows = kodilibrary.get_library()
    total = len(shows)
    progress = xbmcgui.DialogProgress()
    progress.create(title, _L(30071) % (0, total))
    updated = unchanged = errors = no_id = 0
    cancelled = False
    try:
        for index, show in enumerate(shows):
            if progress.iscanceled():
                cancelled = True
                break
            progress.update(int(100.0 * index / max(total, 1)),
                            '%s — %s' % (_L(30071) % (index + 1, total), show.get('title') or ''))
            result = tmdb.get_show_status(show, api_key)
            new_status = result.get('status')
            if not new_status:
                if result.get('error') == 'no_id':
                    no_id += 1
                else:
                    errors += 1
                continue
            if not _needs_update(show.get('status'), new_status):
                unchanged += 1
                continue
            if _apply_status(show, new_status):
                updated += 1
            else:
                errors += 1
    finally:
        progress.close()
    kodilibrary.invalidate_cache()
    xbmc.sleep(500)
    if cancelled:
        xbmcgui.Dialog().notification(title, _L(30079), xbmcgui.NOTIFICATION_INFO, 4000)
    elif updated or unchanged or errors or no_id:
        xbmcgui.Dialog().notification(
            title, _L(30072) % (updated, unchanged, errors, no_id),
            xbmcgui.NOTIFICATION_INFO, 6000)
    show_root()


def refresh_one(tvshowid):
    title = _L(30001)
    api_key = tmdb.get_api_key()
    if not api_key:
        xbmcgui.Dialog().ok(title, _L(30074))
        xbmcplugin.endOfDirectory(HANDLE)
        return
    show = next((item for item in kodilibrary.get_library()
                 if item.get('tvshowid') == tvshowid), None)
    if not show:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    result = tmdb.get_show_status(show, api_key)
    new_status = result.get('status')
    if not new_status:
        if result.get('error') == 'no_id':
            xbmcgui.Dialog().notification(title, _L(30074), xbmcgui.NOTIFICATION_ERROR, 4000)
        else:
            xbmcgui.Dialog().notification(title, _L(30077), xbmcgui.NOTIFICATION_ERROR, 4000)
    elif not _needs_update(show.get('status'), new_status):
        xbmcgui.Dialog().notification(title, _L(30076), xbmcgui.NOTIFICATION_INFO, 4000)
    elif _apply_status(show, new_status):
        kodilibrary.invalidate_cache()
        xbmc.executebuiltin('Container.Refresh')
        xbmcgui.Dialog().notification(
            title, '%s: %s' % (show.get('title') or '', _status_display(new_status)),
            xbmcgui.NOTIFICATION_INFO, 4000)
    else:
        xbmcgui.Dialog().notification(title, _L(30080), xbmcgui.NOTIFICATION_ERROR, 4000)
    xbmcplugin.endOfDirectory(HANDLE)


def open_show(tvshowid):
    if tvshowid:
        xbmc.executebuiltin('ActivateWindow(Videos,videodb://tvshows/titles/%d/)' % int(tvshowid))
    xbmcplugin.endOfDirectory(HANDLE)


def noop():
    xbmcplugin.endOfDirectory(HANDLE)


def open_settings():
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % ADDON_ID)
    xbmcplugin.endOfDirectory(HANDLE)
