import urllib.request, urllib.error, urllib.parse
import json
import time
import re
import logging
import os
import tempfile
from datetime import datetime
from dataclasses import dataclass


API_URL = 'https://www.cbc.ca/listen/api/v1'
URL = 'https://www.cbc.ca/listen/live-radio'
# tz = time.tzname[time.daylight]
logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
LOG = logging.getLogger("plugin.audio.cbcradio")


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
    #program_schedule: list
    station_key: int
    id: int


@dataclass
class Track:
    title: str
    artist: int
    album: str


def get_json(url):
    #  replace w/ https://www.cbc.ca/listen/api/v1/live-radio/getLiveRadioStations
    response = urllib.request.urlopen(url)
    content = response.read().decode('UTF-8')
    content = content.split('\n')
    for line in content:
        if "window.__PRELOADED_STATE__" in line:
            line = line.strip()
            line = line.strip('window.__PRELOADED_STATE__ =')
            line = line.strip()
            a = line
            z = re.sub(r'''\\"''', "'", a)
            y = z.replace("\'", "")
            z = y.replace("\\", "")
            return json.loads(z)


def get_json_api(url):
    response = urllib.request.urlopen(url)
    return json.loads(response.read().decode('UTF-8'))


def get_station_names():
    names = []
    j = get_json_api(API_URL + "/live-radio/getLiveRadioStations")
    stations = j['data']
    for station in stations:
        names.append(station['liveTitle'])
    return names


def get_stations():
    formatted = {}
    j = get_json_api(API_URL + "/live-radio/getLiveRadioStations")
    stations = j['data']
    for station in stations:
        name = station['liveTitle']
        #key = int(station['key']) - 1
        key = int(station['key'])
        streams = get_streams(station)
        station = Station(name, key, streams)
        formatted[name] = station
    return formatted


def get_streams(station):
    streams = []
    strms = station['streams']
    for s in strms:
        streams.append(
            Stream(
                s['title'],
                s['programGuideLocationKey'],
                s['programGuideNetworkKey'],
                s['streamURL'],
                #get_program_schedule(station['key'], s['programGuideLocationKey']),
                station['networkID'],
                s['id']
            )
        )
    return streams


def get_program_schedule(key, location):
    url = API_URL + "/program-queue/" + str(key) + "/" + location
    program_schedule = []
    data = get_json_api(url)['data']
    for program in data:
        new_image = program['programImage'].replace("${width}", "2160").replace("${ratio}", "16x9")
        program['programImage'] = new_image
        program_schedule.append(program)
    return program_schedule


def get_current_program(program_schedule):
    now = time.time() * 1000
    for program in program_schedule:
        time_start = program['epochStart']
        time_end = program['epochEnd']
        LOG.debug(f"title: {program['showTitle']}")
        LOG.debug(f"now: {now}")
        LOG.debug(f"time_start: {time_start}")
        LOG.debug(f"time_end: {time_end}")
        if time_start < now:
            LOG.debug("program started")
            started = True
        else:
            started = False
        if time_end > now:
            ended = False
        else:
            LOG.debug("program ended")
            ended = True
        if started and not ended:
            show = Program(program['showTitle'], program['showSlugTitle'], program['hostName'],
                           program['epochStart'], program['epochEnd'], program['programImage'], program['showID'], program['networkID'])
            return show


def get_playlog(program, location):
    now = datetime.now()
    playlog_url = f"https://www.cbc.ca/listen/api/v1/shows/{program.network_id}/{program.id}/playlogs/day/{now.strftime('%Y%m%d')}?withWebURL=true&locationKey={location}&xcountry=INT"
    playlog = get_json_api(playlog_url)['data']['tracks']
    if playlog == []: LOG.debug("No playlog received from CBC.")
    return playlog


def get_current_track(playlog):
    now = time.time() * 1000
    now_playing = None
    if playlog == []:
        LOG.debug("Empty playlog.")
        return Track(None, None, None)
    for item in playlog:
        time_started = item['broadcastedTime']
        if now > time_started:
            now_playing = item
    track = Track(now_playing['title'], now_playing['artists'], now_playing['album'])
    return track


def run(key, location):
    program_schedule = get_program_schedule(key, location)
    program = get_current_program(program_schedule)
    playlog = get_playlog(program, location)
    track = get_current_track(playlog)
    old_track = None
    while 1:
        now = time.time() * 1000
        if program.time_end < now:
            time.sleep(15)
            program = get_current_program(program_schedule)
            track = get_current_track(playlog)
        if track != old_track:
            old_track = track
            print(f"""
Show: {program.title}
Host: {program.host}
Song: {track.title}
Artist: {track.artist}
Album: {track.album}
==========================
            """)
    time.sleep(5)
