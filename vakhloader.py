from __future__ import unicode_literals
from requests.api import get
from paramiko import SSHClient, RSAKey, AutoAddPolicy
from scp import SCPClient
import youtube_dl
import sys
import logging
import re
import argparse

def getEpisodeNumber(videoTitle):
    normalizedTitle = re.search(r'\d+', videoTitle).group()
    return normalizedTitle

def getLastVideoInfo(apiKey, channelId):
    apiURL = 'https://www.googleapis.com/youtube/v3/search'
    apiParams = {'key':apiKey, 'channelId':channelId,'part':'id,snippet','order':'date','maxResults':1}
    logging.debug(f"Send request to {apiURL} with params: {apiParams}")

    request = get(url = apiURL, params = apiParams)
    data = request.json()
    logging.debug(f"Response data: {data}")

    lastVideoInfo = {
        'id': data['items'][0]['id']['videoId'],
        'title': data['items'][0]['snippet']['title'],
        'channelTitle': data['items'][0]['snippet']['channelTitle'],
    }

    logging.info(f"Last video on {lastVideoInfo['channelTitle']} is '{lastVideoInfo['title']}' with url https://www.youtube.com/watch?v={lastVideoInfo['id']}")
    return lastVideoInfo

def getAudioFromYoutubeVideo(videoTitle, videoURL, storagePath):
    logging.info(f"Start video downloading from {videoURL}...")

    episodeNumber = getEpisodeNumber(videoTitle)
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

    return episodeNumber

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
    if (args.episode_number != None):
        print("test")
    else:
        if (args.verbose):
            logging.basicConfig(level = logging.INFO)

        lastVideoInfo = getLastVideoInfo(args.api_key, args.channel_id)
        episodeNumber = getAudioFromYoutubeVideo(lastVideoInfo['title'], f"https://www.youtube.com/watch?v={lastVideoInfo['id']}", args.local_storage_path)
        sendFileToTargetServer(args.target_server, args.ssh_key, args.local_storage_path, args.target_storage_path, f"{episodeNumber}.mp3")

if __name__ == "__main__":
    main()