import os
import sys
import urlparse
import urllib
import xbmcgui
import xbmcplugin
import json

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])

xbmcplugin.setContent(addon_handle, "audio")


def build_url(query):
    return base_url + "?" + urllib.urlencode(query)


file_path = os.path.dirname(os.path.realpath(__file__))
file = os.path.join(file_path, "resources", "data", "streaminfo.json")
with open(file) as json_file:
    data = json.load(json_file)


def get_stations():
    return data["Data"].keys()


def get_streams(station):
    return data["Data"][station]["streams"]


def list_stations():
    stations = get_stations()
    for station in stations:
        url = build_url({"mode": "folder", "foldername": station})
        li = xbmcgui.ListItem(station)
        li.setArt({"icon": "DefaultFolder.png"})
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=url, listitem=li, isFolder=True
        )
    xbmcplugin.endOfDirectory(addon_handle)


def list_streams(station):
    streams = get_streams(station)
    for stream in streams:
        title = stream["title"]
        streamURL = stream["streamURL"]
        url = build_url(
            {
                "mode": "stream",
                "url": streamURL,
                "title": "{} - {}".format(station, title),
            }
        )
        li = xbmcgui.ListItem("{} - {}".format(station, title))
        li.setProperty("IsPlayable", "true")
        li.setArt({"icon": "icon.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)


def play_stream(streamURL):
    play_item = xbmcgui.ListItem(path=streamURL)
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)


def main():
    args = urlparse.parse_qs(sys.argv[2][1:])
    mode = args.get("mode", None)

    if mode is None:
        list_stations()

    elif mode[0] == "folder":
        station = args["foldername"][0]
        list_streams(station)

    elif mode[0] == "stream":
        streamURL = args["url"][0]
        play_stream(streamURL)


if __name__ == "__main__":
    main()
