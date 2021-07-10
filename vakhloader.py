from __future__ import unicode_literals
from requests.api import get
import youtube_dl
import sys
import logging
import re

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
        'outtmpl': f"{storagePath}/vakhmurky_{episodeNumber}.%(ext)s",
        'retries': 3,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([videoURL])


def main():
    if len(sys.argv) < 2:
        raise Exception('Missing command line parameters')
    
    logging.basicConfig(level = logging.INFO)
    lastVideoInfo = getLastVideoInfo(apiKey = sys.argv[1], channelId = sys.argv[2])
    getAudioFromYoutubeVideo(lastVideoInfo['title'], f"https://www.youtube.com/watch?v={lastVideoInfo['id']}", storagePath = sys.argv[3])

if __name__ == "__main__":
    main()