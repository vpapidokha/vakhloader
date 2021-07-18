from __future__ import unicode_literals
from requests import api
from requests.api import get
from paramiko import SSHClient, RSAKey, AutoAddPolicy
from scp import SCPClient

import youtube_dl
import sys
import logging
import re
import argparse
import json

def getEpisodeNumberByTitle(videoTitle):
    normalizedTitle = re.search(r'\d+', videoTitle).group()
    return normalizedTitle

def getChannelPlaylistIdByName(apiKey, channelId, playlistName):
    apiURL = 'https://www.googleapis.com/youtube/v3/channels'
    apiParams = {'key':apiKey, 'id':channelId, 'part':'contentDetails', 'order':'date', 'maxResults':1}

    request = get(url = apiURL, params = apiParams)
    data = request.json()
    logging.debug(f"Channel data response:\n {json.dumps(data, indent=4, sort_keys=True)}")
    playlistId = data['items'][0]['contentDetails']['relatedPlaylists'][playlistName]
    logging.debug(f"Playlist ID: {playlistId}")

    return playlistId

def getVideosListByPlaylistId(apiKey, channelId, playlistId):
    videos = []
    nextPageToken = None
    apiURL = 'https://www.googleapis.com/youtube/v3/playlistItems'

    while 1:
        apiParams = {'key':apiKey, 'playlistId':playlistId, 'part':'snippet', 'order':'date', 'maxResults':50, 'pageToken': nextPageToken}

        request = get(url=apiURL, params=apiParams)
        data = request.json()
        logging.debug(f"Channel data response:\n {json.dumps(data, indent=4, sort_keys=True)}")

        videos += data['items']
        if ('nextPageToken' in data):
            break
        else:
            nextPageToken = data['nextPageToken']
            logging.debug(f"Next page token:\n {nextPageToken}")

    logging.debug(f"Videos list: \n{json.dumps(videos, indent=4, sort_keys=True)}")
    return videos

def getVideoInfoByEpisodeNumber(apiKey, channelId, episodeNumber):
    playlistId = getChannelPlaylistIdByName(apiKey, channelId, 'uploads')
    playlistVideos = getVideosListByPlaylistId(apiKey, channelId, playlistId)

    for video in playlistVideos:
        if (int(getEpisodeNumberByTitle(video['snippet']['title'])) == episodeNumber):
            videoInfo = {
                'id': video['snippet']['resourceId']['videoId'],
                'title': video['snippet']['title'],
                'channelTitle': video['snippet']['channelTitle'],
                'episodeNumber': getEpisodeNumberByTitle(video['snippet']['title'])
            }

            break

    try:
        logging.debug(f"Target video title is: {videoInfo['title']}")
    except NameError:      
        logging.error("No video found with such an episode number.")
        exit()

    return videoInfo

def getLastVideoInfo(apiKey, channelId):
    apiURL = 'https://www.googleapis.com/youtube/v3/search'
    apiParams = {'key':apiKey, 'id':channelId, 'part':'id,snippet', 'order':'date', 'maxResults':1}
    logging.debug(f"Send request to {apiURL} with params: {apiParams}")

    request = get(url = apiURL, params = apiParams)
    data = request.json()
    logging.debug(f"Response data: {data}")

    lastVideoInfo = {
        'id': data['items'][0]['id']['videoId'],
        'title': data['items'][0]['snippet']['title'],
        'channelTitle': data['items'][0]['snippet']['channelTitle'],
        'episodeNumber': getEpisodeNumberByTitle(data['items'][0]['snippet']['title'])
    }

    logging.info(f"Last video on {lastVideoInfo['channelTitle']} is '{lastVideoInfo['title']}' with url https://www.youtube.com/watch?v={lastVideoInfo['id']}")
    return lastVideoInfo

def getAudioFromYoutubeVideo(videoTitle, videoURL, storagePath):
    logging.info(f"Start video downloading from {videoURL}...")

    episodeNumber = getEpisodeNumberByTitle(videoTitle)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{storagePath}/{episodeNumber}.mp3",
        'retries': 3,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([videoURL])

def progressForScp(filename, size, sent):
    sys.stdout.write("%s's progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

def sendFileToTargetServer(targetServer, pathToKeyFile, sourcePath, targetPath, fileName):
    sshKey = RSAKey.from_private_key_file(pathToKeyFile)
    sshConnection = SSHClient()
    sshConnection.set_missing_host_key_policy(AutoAddPolicy())

    logging.info(f"Connecting to the {targetServer} server...")
    sshConnection.connect(hostname = targetServer, username = "root", pkey = sshKey)
    logging.info(f"Connected")

    scp = SCPClient(sshConnection.get_transport(), progress=progressForScp)
    logging.info(f"Sending {fileName} to the {targetServer} server...")
    scp.put(f"{sourcePath}/{fileName}", f"{targetPath}/{fileName}")
    logging.info(f"Sent")

    scp.close()

def main():
    parser = argparse.ArgumentParser(description = 'Download and upload audio track from youtube video.')
    parser.add_argument('-k', '--api-key', type=str)
    parser.add_argument('-i', '--channel-id', type=str)
    parser.add_argument('--local-storage-path', type=str)
    parser.add_argument('--target-storage-path', type=str)
    parser.add_argument('--target-server', type=str)
    parser.add_argument('--ssh-key', type=str, help='Path to private ssh key')
    parser.add_argument('-e', '--episode-number', type=int)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    if (args.verbose):
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)

    if (args.episode_number != None):
        videoInfo = getVideoInfoByEpisodeNumber(args.api_key, args.channel_id, args.episode_number)
    else:
        videoInfo = getLastVideoInfo(args.api_key, args.channel_id)

    getAudioFromYoutubeVideo(videoInfo['title'], f"https://www.youtube.com/watch?v={videoInfo['id']}", args.local_storage_path)
    if (args.target_server != None):
        sendFileToTargetServer(args.target_server, args.ssh_key, args.local_storage_path, args.target_storage_path, f"{videoInfo['episodeNumber']}.mp3")

if __name__ == "__main__":
    main()