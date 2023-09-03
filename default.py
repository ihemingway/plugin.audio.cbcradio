import os
import sys
#import json
import time
import logging
import urllib.parse as urlparse
#import urllib.request
#from pathlib import Path
from datetime import datetime
import xbmcgui
import xbmcplugin
import xbmc
import now_playing

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
LOG = logging.getLogger("plugin.audio.cbcradio")
LOG.debug(str(sys.argv))

BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])

def set_fanart():
    file_path = os.path.dirname(os.path.realpath(__file__))
    file = os.path.join(file_path, "resources", "fanart.jpg")
    return file


FANART = set_fanart()

def set_icon():
    file_path = os.path.dirname(os.path.realpath(__file__))
    file = os.path.join(file_path, "resources", "icon.jpg")
    return file


ICON = set_icon()

#file_path = os.path.dirname(os.path.realpath(__file__))
#file = Path("resources/data/streaminfo.json")
#file = os.path.join(file_path, "resources", "data", "streaminfo.json")
#with open(file) as json_file:
#    data = json.load(json_file)

xbmcplugin.setPluginFanart(ADDON_HANDLE, FANART)
xbmcplugin.setContent(ADDON_HANDLE, "audio")

'''
def get_data():
    formatted = {'Data': {}}
    j = now_playing.get_json(URL)
    stations = j['listenLiveHeroCarouselData']
    for station in stations:
        name = station['liveTitle']
        formatted["Data"][name] = station
    return formatted
'''


#STATIONS = now_playing.get_stations()
#for key in STATIONS:
#    LOG.debug(STATIONS[key])
KEY = None

def build_url(query):
    return BASE_URL + "?" + urlparse.urlencode(query)


'''
def get_stations():
    return DATA["Data"].keys()


def get_streams(station):
    return DATA["Data"][station]["streams"]


def get_key(station):
    return int(DATA["Data"][station]["key"]) - 1
'''


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
    LOG.debug(f"play_item.setInfo('music', {info_labels})")
    play_item.setInfo('music', info_labels)
    return play_item


def set_program_art(program):
    player = xbmc.Player()
    play_item = player.getPlayingItem()
    play_item.setArt({'fanart': program.artwork_url})
    LOG.debug(f"Set 'fanart': {program.artwork_url} ")
    player.updateInfoTag(play_item)


def news_break():
    LOG.debug("News break.")
    player = xbmc.Player()
    play_item = player.getPlayingItem()
    play_item.setArt({'fanart': None})
    LOG.debug("Set 'fanart': None")
    tag = play_item.getMusicInfoTag()
    tag.setAlbum(None)
    tag.setArtist(None)
    tag.setTitle("News")
    tag.setComment(None)
    player.updateInfoTag(play_item)
    xbmc.sleep(300000)


def play_stream(key, location, url):
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
    set_program_art(program)
    while xbmc.getCondVisibility('Window.IsActive(BusyDialog)'):
        xbmc.sleep(1000)
        LOG.debug("sleep for fullscreen")
    xbmc.executebuiltin('Action(FullScreen)')
    LOG.debug("fullscreen")
    c = -1
    while True:
        now = time.time() * 1000
        time_now = datetime.now().strftime("%M")
        mins = int(time_now)
        if mins == 0 and key == 2:
            news_break()
        if c == 12 and playlog == []:
            try:
                playlog = now_playing.get_playlog(program, location)
            except:
                pass
            finally:
                c = 0
        if program.time_end < now:
            try:
                program = now_playing.get_current_program(program_schedule)
                playlog = now_playing.get_playlog(program, location)
                set_program_art(program)
            except:
                pass
        if playlog != []:
            track = now_playing.get_current_track(playlog)
            if track != last_track:
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
                LOG.debug("item updated")
        elif program.time_end < now or c == -1:
            player = xbmc.Player()
            play_item = player.getPlayingItem()
            tag = play_item.getMusicInfoTag()
            title = tag.getTitle()
            if title == program.title:
                pass
            else:
                tag.setAlbum(None)
                tag.setArtist(program.host)
                tag.setTitle(program.title)
                tag.setComment(None)
                player.updateInfoTag(play_item)
        time.sleep(5)
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
        #player = CBCPlayer(streamURL, key)
        #player.play(item=player.file, listitem=player.play_item)
        #while player.isPlaying():
        #    player.poll()
        #    if not player.isPlaying():
        #        sys.exit(0)


if __name__ == "__main__":
    main()
