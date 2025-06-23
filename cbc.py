import os
import sys
import urllib.parse as urlparse
from datetime import datetime
import xbmcgui
import xbmcplugin
import xbmc
from now_playing import NowPlayingClient

xbmc.log(level=xbmc.LOGINFO, msg=str(sys.argv))


class CBCRadioPlayer:
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.base_url = sys.argv[0]
        self.addon_handle = int(sys.argv[1])
        self.fanart = self._set_file_constant("fanart.jpg")
        self.icon = self._set_file_constant("icon.png")
        self.player = xbmc.Player()
        self.id = "plugin.audio.cbcradio"

        self.program = None
        self.program_schedule = None
        self.track = None
        self.playlog = None
        self.key = None
        self.location = None

        xbmcplugin.setPluginFanart(self.addon_handle, self.fanart)
        xbmcplugin.setContent(self.addon_handle, "audio")

        self.now_playing = NowPlayingClient()

    def _set_file_constant(self, file):
        file_path = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(file_path, "resources", file)

    def build_url(self, query):
        return self.base_url + "?" + urlparse.urlencode(query)


    def list_stations(self):
        stations = self.now_playing.get_station_names()
        for station in stations:
            url = self.build_url({"mode": "folder", "foldername": station})
            li = xbmcgui.ListItem(station)
            li.setArt({"icon": self.icon, "fanart": self.fanart})
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True
            )
        xbmcplugin.endOfDirectory(self.addon_handle)


    def list_streams(self, stn):
        station = self.now_playing.get_stations()[stn]
        for stream in station.streams:
            station_and_title = f"{station.name} - {stream.title}"
            url = self.build_url(
                {
                    "mode": "stream",
                    "url": stream.url,
                    "title": station_and_title,
                    "key": station.key,
                    "location": stream.location,
                }
            )
            li = xbmcgui.ListItem(station_and_title)
            li.setProperty("IsPlayable", "true")
            li.setArt({"icon": self.icon, "fanart": self.fanart})
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li
            )
        xbmcplugin.endOfDirectory(self.addon_handle)


    def set_program_art(self, program, play_item=None):
        if not play_item:
            try:
                play_item = self.player.getPlayingItem()
            except RuntimeError:
                xbmc.log(level=xbmc.LOGINFO, msg="RuntimeError: Could not get PlayingItem.")
                return
        if program is not None:
            current_art = play_item.getArt('fanart')
            if current_art == program.artwork_url:
                xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Program art already set.")
                return
            try:
                play_item.setArt({'fanart': program.artwork_url})
                xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Set 'fanart': {program.artwork_url}")
            except Exception:
                xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Could not fetch fanart: {program.artwork_url} Using default.")
                play_item.setArt({'fanart': self.fanart})
        else:
            play_item.setArt({'fanart': self.fanart})
            xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Set 'fanart': FANART")
        try:
            self.player.updateInfoTag(play_item)
        except RuntimeError:
            pass

    def news_break(self):
        xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: News break.")
        play_item = self.player.getPlayingItem()
        play_item.setArt({'fanart': self.fanart, 'thumb': self.icon})
        xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Set 'fanart': FANART")
        tag = play_item.getMusicInfoTag()
        tag.setAlbum(None)
        tag.setArtist(None)
        tag.setTitle("CBC News")
        tag.setComment(None)
        self.player.updateInfoTag(play_item)


    def calc_minutes(self):
        time_now = datetime.now().strftime("%M")
        mins = int(time_now)
        return mins


    def chill(self, length):
        self.monitor.waitForAbort(length)
        if self.monitor.abortRequested():
            self.player.stop()


    def get_current(self):
        program_schedule = self.now_playing.get_program_schedule(self.key, self.location)
        program = self.now_playing.get_current_program(program_schedule)
        playlog = self.now_playing.get_playlog(program, self.location)
        track = self.now_playing.get_current_track(playlog, self.track)
        if track == self.track:
            return False
        xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}::get_current(): updating track: {self.track} to {track}")
        self.program_schedule = program_schedule
        self.program = program
        self.playlog = playlog
        self.track = track
        return True
    #xbmc.log(level=xbmc.LOGINFO, msg=f"{ID}::get_current(): {PROGRAM} {PROGRAM_SCHEDULE} {TRACK} {PLAYLOG} {KEY} {LOCATION}")


    def update_play_item(self):
        update = self.get_current()
        try:
            play_item = self.player.getPlayingItem()
            tag = self.player.getMusicInfoTag()
        except RuntimeError:
            xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}::update_play_item(): creating new ListItem")
            play_item = xbmcgui.ListItem()
            tag = xbmc.InfoTagMusic()
            update = True
        if not self.playlog:
            info_labels = {
                'artist': self.program.host,
                'title': self.program.title
            }
            play_item.setArt({'thumb': self.icon})
        else:
            info_labels = {
                'album': self.track.album,
                'artist': self.track.artist,
                'title': self.track.title
            }
            play_item.setArt({'thumb': self.track.cover_url})
        current_art = play_item.getArt('fanart')
        if current_art != self.program.artwork_url:
            play_item.setArt({'fanart': self.program.artwork_url})
            update = True
            xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: Set 'fanart': {self.program.artwork_url}")
        try:
            if update:
                play_item.setInfo('music', info_labels)
                self.player.updateInfoTag(play_item)
            return play_item
        except RuntimeError:
            return play_item


    def check_for_news(self):
        if self.calc_minutes() in [0, 1, 2, 3, 4, 5]:
            self.news_break()
            while self.calc_minutes() in [0, 1, 2, 3, 4, 5]:
                self.chill(1)
            try:
                play_item = self.player.getPlayingItem()
                play_item.setArt({'thumb': None})
                self.player.updateInfoTag(play_item)
            except Exception:
                pass


    def initialize(self, url):
        play_item = self.update_play_item()
        play_item.setPath(url)
        play_item.setProperty('IsPlayable', 'true')
        play_item.addStreamInfo('audio', {'codec': 'aac', 'channels': 2})
        if self.player.isPlaying():
            self.player.stop()
            self.chill(1)
        xbmcplugin.setResolvedUrl(self.addon_handle, True, listitem=play_item)
        while not self.player.isPlaying() or xbmc.getCondVisibility('Window.IsActive(BusyDialog)'):
            self.chill(1)
            xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: sleep for fullscreen")
        xbmc.executebuiltin('Action(FullScreen)')
        xbmc.log(level=xbmc.LOGINFO, msg=f"{self.id}: fullscreen")



    def play_stream(self, url):
        self.initialize(url)
        while not self.monitor.abortRequested():
            try:
                if self.key == 2:
                    self.check_for_news()
                self.update_play_item()
            except Exception:
                pass
            self.chill(5)
            if not self.player.isPlaying():
                sys.exit(0)


    def main(self):
        args = urlparse.parse_qs(sys.argv[2][1:])
        mode = args.get("mode", None)

        if mode is None:
            self.list_stations()

        elif mode[0] == "folder":
            station = args["foldername"][0]
            self.list_streams(station)

        elif mode[0] == "stream":
            url = args["url"][0]
            self.key = int(args["key"][0])
            self.location = args["location"][0]
            self.play_stream(url)
            sys.exit(0)


def main():
    CBCRadioPlayer().main()
