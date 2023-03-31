import re

from fastapi import FastAPI
import yt_dlp
from deta import Deta

EXPIRE_AT_REGEXP = re.compile(
  r"https://.*/videoplayback\?expire=(?P<expireAt>[0-9]{10}).*"
)
VAILD_URL_REGEXP = re.compile(
  r"""(?x)^
      (
          (?:https?://|//)                                    # http(s):// or protocol-independent URL
          (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\.com|
            (?:www\.)?deturl\.com/www\.youtube\.com|
            (?:www\.)?pwnyoutube\.com|
            (?:www\.)?hooktube\.com|
            (?:www\.)?yourepeat\.com|
            tube\.majestyc\.net|
            %(invidious)s|
            youtube\.googleapis\.com)/                        # the various hostnames, with wildcard subdomains
          (?:.*?\#/)?                                          # handle anchor (#/) redirect urls
          (?:                                                  # the various things that can precede the ID:
              (?:(?:v|embed|e|shorts|live)/(?!videoseries|live_stream))  # v/ or embed/ or e/ or shorts/
              |(?:                                             # or the v= param in all its forms
                  (?:(?:watch|movie)(?:_popup)?(?:\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)
                  (?:\?|\#!?)                                  # the params delimiter ? or # or #!
                  (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or ?s=tuff&amp;v=V36LpHqtcDY)
                  v=
              )
          ))
          |(?:
            youtu\.be|                                        # just youtu.be/xxxx
            vid\.plus|                                        # or vid.plus/xxxx
            zwearz\.com/watch|                                # or zwearz.com/watch/xxxx
            %(invidious)s
          )/
          |(?:www\.)?cleanvideosearch\.com/media/action/yt/watch\?videoId=
          )
      )?                                                       # all until now is optional -> you can pass the naked ID
      (?P<id>[0-9A-Za-z_-]{11})                                # here is it! the YouTube video ID
      (?(1).+)?                                                # if we found the ID, everything can follow
      (?:\#|$)"""
)

deta = Deta()
db = deta.Base("playback_data_cache")
app = FastAPI()

@app.get("/v1")
def root():
  return {
    "version": "1.0.0",
    "source_code": "https://github.com/NightFeather0615/Classroom-Jukebox-API",
    "powered_by": "https://deta.space/"
  }

@app.get("/v1/playback-data")
def read_item(source: str):
  try:
    video_id = VAILD_URL_REGEXP.match(source).group("id")
  except:
    return {
      "status": "failed",
      "msg": "Invaild YouTube source URL."
    }
  
  if (cache_data := db.get(video_id)) is not None:
    del cache_data["__expires"]
    del cache_data["key"]
    cache_data["status"] = "success"
    return cache_data
  
  try:
    with yt_dlp.YoutubeDL() as dlp:
      info = dlp.extract_info(source, download = False)
    
    playback_url = next(
      filter(
        lambda x: x["resolution"] == "audio only",
        info["requested_formats"]
      )
    )["url"]
    playback_data = {
      "video_id": info["id"],
      "thumbnail": info["thumbnail"],
      "title": info["fulltitle"],
      "channel": info["channel"],
      "duration": info["duration"],
      "original_url": info["original_url"],
      "audio_source": playback_url
    }
  except:
    return {
      "status": "failed",
      "msg": "Unknown error occurred while getting playback data."
    }
  
  db.put(
    playback_data,
    key = video_id,
    expire_at = int(EXPIRE_AT_REGEXP.match(playback_url).group("expireAt"))
  )
  
  playback_data["status"] = "success"
  return playback_data
