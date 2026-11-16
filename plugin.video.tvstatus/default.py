import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs

sys.path.insert(0, os.path.join(
    xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')),
    'resources', 'lib'))

import ui

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
ARGS = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?'))) if len(sys.argv) > 2 else {}

ui.setup(HANDLE, BASE_URL)


def router():
    mode = ARGS.get('mode', '')
    if mode == 'shows':
        ui.show_listing(ARGS.get('filter'))
    elif mode == 'filters':
        ui.show_filters()
    elif mode == 'rawfilters':
        ui.show_raw_filters()
    elif mode == 'refresh':
        ui.run_refresh()
    elif mode == 'refreshone':
        try:
            ui.refresh_one(int(ARGS.get('id')))
        except (TypeError, ValueError):
            ui.noop()
    elif mode == 'open':
        try:
            ui.open_show(int(ARGS.get('id')))
        except (TypeError, ValueError):
            ui.noop()
    elif mode == 'settings':
        ui.open_settings()
    else:
        ui.show_root()


if __name__ == '__main__':
    try:
        router()
    except Exception:
        import traceback
        xbmc.log('plugin.video.tvstatus: %s' % traceback.format_exc(), xbmc.LOGERROR)
        try:
            ui.noop()
        except Exception:
            pass
