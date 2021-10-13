## Vakhloader — python app for getting audio track from youtube videos

I've created this app for automizing of my podcast creation process.

Vakhloader could get you the last episode (audio track from the last video on the youtube channel) or the chosen one.

### How to use
To get the last episode, use the next command:
```
python vakhloader.py --api-key $your_youtube_api_key --channel-id $your_youtube_channel_id --local-storage-path $target_location_for_the_track
```

To get the chosen episode, use the next command:
```
python vakhloader.py --api-key $your_youtube_api_key --channel-id $your_youtube_channel_id --local-storage-path $target_location_for_the_track --episode-number 25
```