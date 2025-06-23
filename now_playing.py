import json
import time
import os
import sys
from urllib.request import Request, urlopen
import urllib.error
from datetime import datetime
from dataclasses import dataclass
import xbmc

DISCOGS_TOKEN = "DsUoNrgSoegmaQgKqAnYbcalRpeJQArbnUxcHpQa"

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(file_path, "lib"))

import discogs_client


API_URL = "https://www.cbc.ca/listen/api/v1"
LIVE_STATIONS = "/live-radio/getLiveRadioStations"


@dataclass
class Station:
    name: str
    key: int
    streams: list


@dataclass
class Program:
    title: str
    slug_title: str
    host: str
    time_start: int
    time_end: int
    artwork_url: str
    id: int
    network_id: int


@dataclass
class Stream:
    title: str
    location: str
    network: str
    url: str
    station_key: int
    id: int


@dataclass
class Track:
    title: str
    artist: int
    album: str
    cover_url: str


class NowPlayingClient:
    """Client for accessing CBC now playing data."""

    def __init__(self):
        self.discogs = discogs_client.Client(
            "plugin.audio.cbcradio/2.05", user_token=DISCOGS_TOKEN
        )

    @staticmethod
    def get_json_api(url):
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) "
                    "Gecko/20100101 Firefox/61.0"
                )
            }
            req = Request(url)
            for k, v in headers.items():
                req.add_header(k, v)
            response = urlopen(req)
        except urllib.error.URLError:
            return None
        return json.loads(response.read().decode("UTF-8"))

    def get_station_names(self):
        names = []
        data = self.get_json_api(API_URL + LIVE_STATIONS)
        stations = data["data"]
        for station in stations:
            names.append(station["liveTitle"])
        return names

    def get_stations(self):
        formatted = {}
        data = self.get_json_api(API_URL + LIVE_STATIONS)["data"]
        for station in data:
            name = station["liveTitle"]
            key = int(station["key"])
            streams = self.get_streams(station)
            formatted[name] = Station(name, key, streams)
        return formatted

    @staticmethod
    def get_streams(station):
        streams = []
        for s in station["streams"]:
            streams.append(
                Stream(
                    s["title"],
                    s["programGuideLocationKey"],
                    s["programGuideNetworkKey"],
                    s["streamURL"],
                    station["networkID"],
                    s["id"],
                )
            )
        return streams

    def get_program_schedule(self, key, location):
        url = f"{API_URL}/program-queue/{key}/{location}"
        program_schedule = []
        data = self.get_json_api(url)["data"]
        for program in data:
            new_image = program["programImage"].replace("${width}", "2160").replace(
                "${ratio}", "16x9"
            )
            program["programImage"] = new_image
            program_schedule.append(program)
        return program_schedule

    @staticmethod
    def get_current_program(program_schedule):
        now = time.time() * 1000
        for program in program_schedule:
            time_start = program["epochStart"]
            time_end = program["epochEnd"]
            started = time_start < now
            ended = time_end <= now
            if started and not ended:
                return Program(
                    program["showTitle"],
                    program["showSlugTitle"],
                    program["hostName"],
                    program["epochStart"],
                    program["epochEnd"],
                    program["programImage"],
                    program["showID"],
                    program["networkID"],
                )

    def get_playlog(self, program, location):
        now = datetime.now()
        playlog = []
        try:
            playlog_url = (
                f"https://www.cbc.ca/listen/api/v1/shows/{program.network_id}/"
                f"{program.id}/playlogs/day/{now.strftime('%Y%m%d')}?withWebURL=true&"
                f"locationKey={location}&xcountry=INT"
            )
            playlog = self.get_json_api(playlog_url)["data"]["tracks"]
        except Exception:
            return playlog
        if not playlog:
            xbmc.log(level=xbmc.LOGINFO, msg="plugin.audio.cbcradio: No playlog received from CBC.")
        return playlog

    def get_current_track(self, playlog, current_track=None):
        now = time.time() * 1000
        now_playing = None
        if not playlog:
            xbmc.log(level=xbmc.LOGINFO, msg="plugin.audio.cbcradio: Empty playlog.")
            return Track(None, None, None, None)
        for item in playlog:
            time_started = item["broadcastedTime"]
            if now > time_started:
                now_playing = item
        try:
            if current_track and current_track.title == now_playing["title"]:
                now_playing["cover_url"] = current_track.cover_url
            else:
                now_playing["cover_url"] = self.get_album_cover(
                    now_playing["artists"], now_playing["album"]
                )
            return Track(
                now_playing["title"],
                now_playing["artists"],
                now_playing["album"],
                now_playing["cover_url"],
            )
        except TypeError:
            return Track(None, None, None, None)

    def get_album_cover(self, artist, album):
        artists = artist.split(",")
        for art in artists:
            try:
                results = self.discogs.search(album, artist=artist, type="release")
                if results.count != 0:
                    break
            except Exception:
                return None
        try:
            if results.count != 0:
                xbmc.log(
                    level=xbmc.LOGINFO,
                    msg=(
                        "plugin.audio.cbcradio: get_album_cover::found "
                        f"{results[0].images[0]['uri']}"
                    ),
                )
                return results[0].images[0]["uri"]
        except Exception:
            pass
        return None
