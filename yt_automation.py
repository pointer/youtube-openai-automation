import os
import random
import sys
import time
import pickle
import http.client as httplib
import httplib2
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import openai
import requests
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pytubefix import YouTube
from pytube import request

# Set a custom User-Agent header
request.default_range_size = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


# Set a custom User-Agent header
# request.default_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
# 1037804191460-qvlskh7r3t1umvk9sij76gmmf55qh3bk.apps.googleusercontent.com
# Set up OAuth 2.0 credentials
CLIENT_SECRETS_FILE = "./client-secret/client_secret_googleusercontent.json"  # Download this from Google Cloud Console
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
DOWNLOAD_DIR = "./downloaded_videos"



# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
OPENAI_API_KEY = ""

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

video_data = []
def get_openai_api_key():
    if os.path.exists("./client-secret/openai-api-key.json"):
      with open("./client-secret/openai-api-key.json", "r") as openai_api_key_file:
        openai_api_key_handle = json.load(openai_api_key_file)
        OPENAI_API_KEY = openai_api_key_handle['openai']['api_key']
        return OPENAI_API_KEY
        
def get_authenticated_service(args):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", [YOUTUBE_UPLOAD_SCOPE])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, [YOUTUBE_UPLOAD_SCOPE])
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def authenticate():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return creds

def download_video(video_id, video_title):
    try:
        # Create the download directory if it doesn't exist
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        # Construct the YouTube video URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Download the video using Pytube
        yt = YouTube(video_url)
        stream = yt.streams.filter(progressive=True, file_extension="mp4").first()  # Get the highest resolution progressive stream
        if stream:
            print(f"Downloading: {video_title}...")
            stream.download(output_path=DOWNLOAD_DIR, filename=f"{video_title}.mp4")
            print(f"Download complete: {video_title}\n")
        else:
            print(f"No downloadable stream found for: {video_title}\n")
    except Exception as e:
        print(f"Error downloading {video_title}: {e}\n")

def initialize_upload(youtube, file_path, body = dict()):

  # Call the API's videos.insert method to create and upload the video.
    try:
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=authenticate())
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting "chunksize" equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).

            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
      )
        resumable_upload(insert_request)
    except HttpError as e:
        if e.resp.status == 403:
            print("Access Forbidden: Ensure you have the correct permissions and API enabled.")
        else:
            print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print("Uploading file...")
      status, response = insert_request.next_chunk()
      if response is not None:
        if 'id' in response:
          print(f'Video id {response['id']} was successfully uploaded.')	
        else:
          exit("The upload failed with an unexpected response: %s" % response)
    except HttpError as e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = f'A retriable HTTP error {e.resp.status} occurred:\n{e.content}'
      else:
        raise
    except RETRIABLE_EXCEPTIONS as e:
      error = f'A retriable error occurred: {e}'

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print(f'Sleeping {sleep_seconds} seconds and then retrying...')
      time.sleep(sleep_seconds)

def upload_video(file_path, body=dict()):
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=authenticate())
    try:
        initialize_upload(youtube, file_path, body)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Upload complete")
        
def search_videos(query, max_results=5):
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=authenticate())
    request = youtube.search().list(
        q=query,
        part="snippet",
        publishedBefore="2024-01-01T00:00:00Z",
        maxResults=max_results,
        type="video"
    )
    response = request.execute()

    for item in response["items"]:
        video_title = item["snippet"]["title"]
        video_id = item["id"]["videoId"]
        download_video(video_id, video_title)
        sleep_seconds = random.random() * 10
#       print(f'Sleeping {sleep_seconds} seconds and then retrying...')
        time.sleep(sleep_seconds)
        # channel_title = item["snippet"]["channelTitle"]
        # published_at = item["snippet"]["publishedAt"]
        # description = item["snippet"]["description"]
        file_path = f"{DOWNLOAD_DIR}/{video_title}.mp4"
        body=dict(
          kind='youtube#video',
          etag=item["etag"],
          id=dict(
            kind=item["id"]["kind"],
            videoId=item["id"]["videoId"]
          ),
          snippet=dict(
            title=video_title,
            description=item["snippet"]["description"],
            tags="#vanity #makeup #make-up #beauty #cosmetics  #cosmétiques #skincare #soins #haircare  #cheveux  #nails  #ongles  #manucure  #pedicure  #pédicure  #nailart  #nailpolish  #vernis",
            categoryId=12,
            thumbnails=dict(
                default=dict(
                    url=item["snippet"]["thumbnails"]["default"]["url"],
                    width=item["snippet"]["thumbnails"]["default"]["width"],
                    height=item["snippet"]["thumbnails"]["default"]["height"]
                ),
                medium=dict(
                    url=item["snippet"]["thumbnails"]["medium"]["url"],
                    width=item["snippet"]["thumbnails"]["medium"]["width"],
                    height=item["snippet"]["thumbnails"]["medium"]["height"]
                ),
                high=dict(
                    url=item["snippet"]["thumbnails"]["high"]["url"],
                    width=item["snippet"]["thumbnails"]["high"]["width"],
                    height=item["snippet"]["thumbnails"]["high"]["height"]
                )
            ),
            channelTitle=item["snippet"]["channelTitle"],
            liveBroadcastContent="none",	
            publishTime=item["snippet"]["publishedAt"]
          ),
          status=dict(
            privacyStatus="public"
          )
        )        
        upload_video(file_path, body)

if __name__ == "__main__":
    # search_videos("#vanity | #makeup | #make-up | #beauty | #maquillage | #cosmetics | #cosmétiques | #skincare | #soins | #haircare | #cheveux | #nails | #ongles | #manucure | #pedicure | #pédicure | #nailart | #nailpolish | #vernis")
    get_openai_api_key()
    # search_videos("makeup tutorial", max_results=5)    