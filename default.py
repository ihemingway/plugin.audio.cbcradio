import os
import sys
import time
import urllib.parse as urlparse
from datetime import datetime
import xbmcgui
import xbmcplugin
import xbmc
import now_playing

xbmc.log(level=xbmc.LOGDEBUG, msg=str(sys.argv))

def set_file_constant(file):
    file_path = os.path.dirname(os.path.realpath(__file__))
    file = os.path.join(file_path, "resources", file)
    return file


MONITOR = xbmc.Monitor()
BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
FANART = set_file_constant("fanart.jpg")
ICON = set_file_constant("icon.jpg")

xbmcplugin.setPluginFanart(ADDON_HANDLE, FANART)
xbmcplugin.setContent(ADDON_HANDLE, "audio")

def build_url(query):
    return BASE_URL + "?" + urlparse.urlencode(query)


def list_stations():
    stations = now_playing.get_station_names()
    for station in stations:
        url = build_url({"mode": "folder", "foldername": station})
        li = xbmcgui.ListItem(station)
        li.setArt({"icon": "DefaultFolder.png", "fanart": FANART})
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


def create_play_item(track):
    info_labels = {
        'album': track.album,
        'artist': track.artist,
        'title': track.title
        }
    play_item = xbmcgui.ListItem()
    xbmc.log(level=xbmc.LOGDEBUG, msg=f"plugin.audio.cbcradio: play_item.setInfo('music', {info_labels})")
    play_item.setInfo('music', info_labels)
    return play_item


def set_program_art(program):
    #if xbmc.Player().isPlaying():
    player = xbmc.Player()
    play_item = player.getPlayingItem()
    if program is not None:
        play_item.setArt({'fanart': program.artwork_url})
        xbmc.log(level=xbmc.LOGDEBUG, msg=f"plugin.audio.cbcradio: Set 'fanart': {program.artwork_url}")
    else:
        play_item.setArt({'fanart': FANART})
        xbmc.log(level=xbmc.LOGDEBUG, msg=f"plugin.audio.cbcradio: Set 'fanart': FANART")
    player.updateInfoTag(play_item)


def news_break():
    xbmc.log(level=xbmc.LOGDEBUG, msg="plugin.audio.cbcradio: News break.")
    player = xbmc.Player()
    play_item = player.getPlayingItem()
    play_item.setArt({'fanart': FANART})
    xbmc.log(level=xbmc.LOGDEBUG, msg="plugin.audio.cbcradio: Set 'fanart': FANART")
    tag = play_item.getMusicInfoTag()
    tag.setAlbum(None)
    tag.setArtist(None)
    tag.setTitle("CBC News")
    tag.setComment(None)
    player.updateInfoTag(play_item)


def calc_minutes():
    time_now = datetime.now().strftime("%M")
    mins = int(time_now)
    return mins


def initialize(key, location, url):
    program_schedule = now_playing.get_program_schedule(key, location)
    program = now_playing.get_current_program(program_schedule)
    playlog = now_playing.get_playlog(program, location)
    last_track = now_playing.get_current_track(playlog)
    play_item = create_play_item(last_track)
    play_item.setPath(url)
    play_item.setProperty('IsPlayable', 'true')
    play_item.addStreamInfo('audio', {'codec': 'aac', 'channels': 2})
    if xbmc.Player().isPlaying():
        xbmc.Player().stop()
        xbmc.sleep(1000)
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)
    while not xbmc.Player().isPlaying():
        xbmc.sleep(1000)
    while xbmc.getCondVisibility('Window.IsActive(BusyDialog)'):
        xbmc.sleep(1000)
        xbmc.log(level=xbmc.LOGDEBUG, msg="plugin.audio.cbcradio: sleep for fullscreen")
    set_program_art(program)
    xbmc.executebuiltin('Action(FullScreen)')
    xbmc.log(level=xbmc.LOGDEBUG, msg="plugin.audio.cbcradio: fullscreen")
    return program_schedule, program, playlog, last_track, play_item


def play_stream(key, location, url):
    program_schedule, program, playlog, last_track, play_item = initialize(key, location, url)
    c = -1
    while not MONITOR.abortRequested():
        now = time.time() * 1000
        if calc_minutes() in [00, 1, 2, 3, 4, 5] and key == 2:
        # cbc music has 5 min news breaks at the top of the hour
            news_break()
            while calc_minutes() in [00, 1, 2, 3, 4, 5]:
                xbmc.sleep(10000)
            now = time.time() * 1000
            program.time_end = now - 10000  # make sure program gets changed
        if program.time_end < now:
            try:
                program = now_playing.get_current_program(program_schedule)
                playlog = now_playing.get_playlog(program, location)
                set_program_art(program)
            except Exception:
                pass
        if c == 12 and playlog == []:  # if there's no playlog, check every min
            try:
                playlog = now_playing.get_playlog(program, location)
            except Exception:
                pass
            finally:
                c = 0
        if playlog != []:  # if there is a playlog, get which track should be playing
            track = now_playing.get_current_track(playlog)
            if track != last_track:  # if it's a new track, update 'now playing'
                last_track = track
                player = xbmc.Player()
                play_item = player.getPlayingItem()
                tag = play_item.getMusicInfoTag()
                tag.setAlbum(track.album)
                tag.setArtist(track.artist)
                tag.setTitle(track.title)
                tag.setComment(f"{program.title} with {program.host}")
                player.updateInfoTag(play_item)
                '''play_item = xbmcgui.ListItem()
                play_item.setPath(player.getPlayingFile())
                play_item.setInfo('music', {'album': track.album, 'artist': track.artist, 'title': track.title})
                player.updateInfoTag(play_item)'''
                xbmc.log(level=xbmc.LOGDEBUG, msg="plugin.audio.cbcradio: track updated")
        elif program.time_end < now or c == -1:  # if program over or plugin just started
            player = xbmc.Player()
            play_item = player.getPlayingItem()
            tag = play_item.getMusicInfoTag()
            title = tag.getTitle()
            # if there is no playlog, we're going to set the info displayed to
            # the program name and host. this is mainly for CBC One as most of
            # the shows do not have playlogs. CBC Music, usually does, but
            # they can take awhile to be posted. this will display the show/host
            # until the playlog is available.
            if title == program.title:
                pass
            else:
                tag.setAlbum(None)
                tag.setArtist(program.host)
                tag.setTitle(program.title)
                tag.setComment(None)
                player.updateInfoTag(play_item)
        MONITOR.waitForAbort(5)
        if MONITOR.abortRequested():
            set_program_art(None)
            xbmc.Player().stop()
        c += 1
        if not xbmc.Player().isPlaying():
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
        key = int(args["key"][0])
        location = args["location"][0]
        play_stream(key, location, url)
        sys.exit(0)


if __name__ == "__main__":
    main()
