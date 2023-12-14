import os
import sys
import urllib.parse as urlparse
from datetime import datetime
import xbmcgui
import xbmcplugin
import xbmc
import now_playing

xbmc.log(level=xbmc.LOGINFO, msg=str(sys.argv))


def set_file_constant(file):
    file_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(file_path, "resources", file)


MONITOR = xbmc.Monitor()
BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
FANART = set_file_constant("fanart.jpg")
ICON = set_file_constant("icon.png")
PLAYER = xbmc.Player()
ID = "plugin.audio.cbcradio"

PROGRAM = None
PROGRAM_SCHEDULE = None
TRACK = None
PLAYLOG = None
KEY = None
LOCATION = None

xbmcplugin.setPluginFanart(ADDON_HANDLE, FANART)
xbmcplugin.setContent(ADDON_HANDLE, "audio")


def build_url(query):
    return BASE_URL + "?" + urlparse.urlencode(query)


def list_stations():
    stations = now_playing.get_station_names()
    for station in stations:
        url = build_url({"mode": "folder", "foldername": station})
        li = xbmcgui.ListItem(station)
        li.setArt({"icon": ICON, "fanart": FANART})
        xbmcplugin.addDirectoryItem(
            handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True
        )
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def list_streams(stn):
    station = now_playing.get_stations()[stn]
    for stream in station.streams:
        station_and_title = f"{station.name} - {stream.title}"
        url = build_url(
            {
                "mode": "stream",
                "url": stream.url,
                "title": station_and_title,
                "key": station.key,
                "location": stream.location
            }
        )
        li = xbmcgui.ListItem(station_and_title)
        li.setProperty("IsPlayable", "true")
        li.setArt({"icon": ICON, "fanart": FANART})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def set_program_art(program, play_item=None):
    if not play_item:
        try:
            play_item = PLAYER.getPlayingItem()
        except RuntimeError:
            xbmc.log(level=xbmc.LOGINFO, msg="RuntimeError: Could not get PlayingItem.")
            return
    if program is not None:
        current_art = play_item.getArt('fanart')
        if current_art == program.artwork_url:
            xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Program art already set.")
            return
        try:
            play_item.setArt({'fanart': program.artwork_url})
            xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Set 'fanart': {program.artwork_url}")
        except Exception:
            xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Could not fetch fanart: {program.artwork_url} Using default.")
            play_item.setArt({'fanart': FANART})
    else:
        play_item.setArt({'fanart': FANART})
        xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Set 'fanart': FANART")
    try:
        PLAYER.updateInfoTag(play_item)
    except RuntimeError:
        pass

def news_break():
    xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: News break.")
    play_item = PLAYER.getPlayingItem()
    play_item.setArt({'fanart': FANART, 'thumb': ICON})
    xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Set 'fanart': FANART")
    tag = play_item.getMusicInfoTag()
    tag.setAlbum(None)
    tag.setArtist(None)
    tag.setTitle("CBC News")
    tag.setComment(None)
    PLAYER.updateInfoTag(play_item)


def calc_minutes():
    time_now = datetime.now().strftime("%M")
    mins = int(time_now)
    return mins


def chill(length):
    MONITOR.waitForAbort(length)
    if MONITOR.abortRequested():
        PLAYER.stop()


def get_current():
    global PROGRAM
    global PROGRAM_SCHEDULE
    global TRACK
    global PLAYLOG
    program_schedule = now_playing.get_program_schedule(KEY, LOCATION)
    program = now_playing.get_current_program(program_schedule)
    playlog = now_playing.get_playlog(program, LOCATION)
    track = now_playing.get_current_track(playlog)
    if track == TRACK:
        return False
    xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::get_current(): updating track: {TRACK} to {track}")
    PROGRAM = None
    PROGRAM_SCHEDULE = None
    TRACK = None
    PLAYLOG = None
    PROGRAM_SCHEDULE = program_schedule
    PROGRAM = program
    PLAYLOG = playlog
    TRACK = track
    #xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::get_current(): updating track: {TRACK} to {track}")
    return True
    #xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::get_current(): {PROGRAM} {PROGRAM_SCHEDULE} {TRACK} {PLAYLOG} {KEY} {LOCATION}")


def update_play_item():
    global PROGRAM
    global PROGRAM_SCHEDULE
    global TRACK
    global PLAYLOG
    update = get_current()
    try:
        play_item = PLAYER.getPlayingItem()
        tag = PLAYER.getMusicInfoTag()
        #xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::update_play_item(): {tag.getTitle()}")
    except RuntimeError:
        xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::update_play_item(): creating new ListItem")
        play_item = xbmcgui.ListItem()
        tag = xbmc.InfoTagMusic()
        update = True
    if not PLAYLOG:
        info_labels = {
            'artist': PROGRAM.host,
            'title': PROGRAM.title
            }
        play_item.setArt({'thumb': ICON})
    else:
        info_labels = {
            'album': TRACK.album,
            'artist': TRACK.artist,
            'title': TRACK.title
            }
        play_item.setArt({'thumb': TRACK.cover_url})
    current_art = play_item.getArt('fanart')
    if current_art == PROGRAM.artwork_url:
        pass
    else:
        play_item.setArt({'fanart': PROGRAM.artwork_url})
        update = True
        xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: Set 'fanart': {PROGRAM.artwork_url}")
    try:
        if update:
            #play_item.setArt({'thumb': TRACK.cover_url})
            play_item.setInfo('music', info_labels)
            PLAYER.updateInfoTag(play_item)
            #xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::update_play_item(): {tag.getTitle()}")
        return play_item
    except RuntimeError:
        return play_item


def check_for_news():
    if calc_minutes() in [00, 1, 2, 3, 4, 5]:
        news_break()
        while calc_minutes() in [00, 1, 2, 3, 4, 5]:
            chill(1)
        try:
            play_item = PLAYER.getPlayingItem()
            play_item.setArt({'thumb': None})
            PLAYER.updateInfoTag(play_item)  # so album art doesn't hang around if next track has none
        except:
            pass


def initialize(url):
    play_item = update_play_item()
    play_item.setPath(url)
    play_item.setProperty('IsPlayable', 'true')
    play_item.addStreamInfo('audio', {'codec': 'aac', 'channels': 2})
    if PLAYER.isPlaying():
        PLAYER.stop()
        chill(1)
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)
    while not PLAYER.isPlaying() or xbmc.getCondVisibility('Window.IsActive(BusyDialog)'):
        chill(1)
        xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: sleep for fullscreen")
    xbmc.executebuiltin('Action(FullScreen)')
    xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}: fullscreen")



def play_stream(url):
    initialize(url)
    while not MONITOR.abortRequested():
        if KEY == 2:
            check_for_news()
        update_play_item()
        chill(5)
        if not PLAYER.isPlaying():
            sys.exit(0)


def main():
    args = urlparse.parse_qs(sys.argv[2][1:])
    mode = args.get("mode", None)

    if mode is None:
        list_stations()

    elif mode[0] == "folder":
        station = args["foldername"][0]
        list_streams(station)

    elif mode[0] == "stream":
        url = args["url"][0]
        global KEY
        KEY = int(args["key"][0])
        global LOCATION
        LOCATION = args["location"][0]
        play_stream(url)
        sys.exit(0)
