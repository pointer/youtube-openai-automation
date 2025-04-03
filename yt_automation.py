import os
import os.path
import random
import sys
import time
import pickle
import http.client as httplib
import argparse
import icecream as ic
from typing import List
# import rich
import traceback

from openai import OpenAI
import re
import httplib2
import requests
import json
import ssl
import certifi
import pathlib

# from apiclient import discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pytubefix import YouTube
from pytube import request
# from sheetfu import Table, SpreadsheetApp
from google.oauth2 import service_account
import pygsheets
import numpy as np
from pygsheets import Spreadsheet
from pygsheets import Worksheet
from pygsheets import Cell

# Set a custom User-Agent header
request.default_range_size = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


# Set a custom User-Agent header
# request.default_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
# 1037804191460-qvlskh7r3t1umvk9sij76gmmf55qh3bk.apps.googleusercontent.com
# Set up OAuth 2.0 credentials
# CLIENT_SECRETS_FILE = "./client-secret/client_secret_googleusercontent.json"  # Download this from Google Cloud Console
CLIENT_SECRETS_FILE = "./mirabelle-project-6c703ae64cb7.json"
# "./client-secret/client_secret_1037804191460-qvlskh7r3t1umvk9sij76gmmf55qh3bk.apps.googleusercontent.com"
# CLIENT_SECRETS_FILE = "client-secret/client_secret_1037804191460-qvlskh7r3t1umvk9sij76gmmf55qh3bk.apps.googleusercontent.com copy.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.download",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
    
]


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# /Users/Kateb/Documents/_dev/yt-automation/yt_search.py

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
DOWNLOAD_DIR = "./downloaded_videos"
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


# Set a custom User-Agent header
request.default_range_size = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# /Users/Kateb/Documents/_dev/yt-automation/yt_search.py

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

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

parsed_json = dict(
    # snippet=dict(
    #     title="",
    #     description="",
    #     tags=[],
    #     categoryId=22
    # ),
    # status=dict(
    #     privacyStatus="public"
    # )
)

def get_youtube_oauth_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds


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

def get_openai_api_key() -> str:
    if os.path.exists("./client-secret/openai-api-key.json"):
        with open("./client-secret/openai-api-key.json", "r") as openai_api_key_file:
            openai_api_key_handle = json.load(openai_api_key_file)
            OPENAI_API_KEY = openai_api_key_handle['openai']['api_key']
            return OPENAI_API_KEY
    return ""

def initialize_upload(youtube, file_path, body=dict()):
    try:
        # Ensure the body has the correct structure
        video_body = {
            "snippet": {
                "title": body.get("snippet", {}).get("title", "Default Title"),
                "description": body.get("snippet", {}).get("description", ""),
                "tags": body.get("snippet", {}).get("tags", []),
                "categoryId": "26"
            },
            "status": {
                "privacyStatus": body.get("status", {}).get("privacyStatus", "private"),
                "selfDeclaredMadeForKids": False
            }
        }

        insert_request = youtube.videos().insert(
            part=",".join(video_body.keys()),
            body=video_body,
            media_body=MediaFileUpload(
                file_path,
                mimetype='video/mp4',
                chunksize=-1,
                resumable=True
            )
        )
        resumable_upload(insert_request)
        
    except HttpError as e:
        if e.resp.status == 403:
            print("Access Forbidden: Check API permissions")
            print(f"Error details: {e.content}")
        else:
            print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

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
          print(f'Video id {response["id"]} was successfully uploaded.')	
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

def upload_video(file_path, body=dict()) -> bool:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=authenticate())
    try:
        initialize_upload(youtube, file_path, body)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Upload complete")
    return True
 
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
            file_name = re.sub(r"[^\w\s]", "", video_title).replace(" ", "-").lower() + ".mp4"
            # file_path = os.path.join(DOWNLOAD_DIR, filename)
            file_path = pathlib.Path(DOWNLOAD_DIR) / file_name
            if not file_path.exists():
                stream.download(output_path=DOWNLOAD_DIR, filename=file_name)
                print(f"Download complete: {video_title}\n")
        else:
            print(f"No downloadable stream found for: {video_title}\n")
    except Exception as e:
        print(f"Error downloading {video_title}: {e}\n")

def search_videos(query): #, max_results=5):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=authenticate())
    # request = youtube.search().list(
    #     q=query,
    #     part="snippet",
    #     publishedBefore="2024-01-01T00:00:00Z",
    #     maxResults=1, #max_results,
    #     type="video"
    # )
    # response = request.execute()
    # # ic(response)
    # for item in response["items"]:
    #     video_title = item["snippet"]["title"]
    #     video_id = item["id"]["videoId"]
    #     download_video(video_id, video_title)
    #     sleep_seconds = random.random() * 10
#       print(f'Sleeping {sleep_seconds} seconds and then retrying...')
        # time.sleep(sleep_seconds)

        # filename = re.sub(r"[^\w\s]", "", video_title).replace(" ", "-").lower() + ".mp4"
        # file_path = f"{DOWNLOAD_DIR}/{filename}"
  
        # body = {
        #     "snippet": {
        #         "title": video_title,
        #         "description": item["snippet"]["description"],
        #         "tags": ["makeup tutorial", "beauty tips", "cosmetics", "makeup basics", "beauty tutorial"],
        #     },
        #     "status": {
        #         "privacyStatus": "public"  # Can be "private", "public", or "unlisted"
        #     }
        # }           
        # upload_video(file_path, body)
       
def generate_video_metadata(topics):
    api_key_ = get_openai_api_key()  
    client = OpenAI(api_key=api_key_)

    completion = client.chat.completions.create(
        model="gpt-4",
        max_tokens=2000,  # Increased token limit for complete responses
        messages=[
            {
                "role": "system", 
                "content": "You are a video content specialist. Provide only valid JSON responses. Keep descriptions under 50 words. Select video in French."
            },
            {
                "role": "user",
                "content": f"""Based on these topics: {topics}, generate:
                1. 3 unique video title ideas that would perform well on YouTube
                2. For each title:
                    - A brief description (max 50 words)
                    - 5 relevant SEO tags
                    - A filename in lowercase with hyphens
                3. Format as valid JSON:
                   {{
                     "videos": [
                       {{
                         "title": "Example Title",
                         "description": "Brief description.",
                         "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
                         "filename": "example-title.mp4"
                       }}
                     ]
                   }}"""
            }
        ],
        temperature=0.5  # Reduced for more consistent outputs
    )

    content = completion.choices[0].message.content
    if content:
        try:
            # Remove whitespace and newlines
            cleaned_content = ' '.join(content.split())
            parsed_json = json.loads(cleaned_content)
            
            if not isinstance(parsed_json, dict) or 'videos' not in parsed_json:
                raise ValueError("Invalid JSON structure")

            for video in parsed_json['videos']:
                video_id = search_videos(video['title'])
                # if not video_id:
                #     raise ValueError(f"Could not find video ID for title: {video['title']}")
                # video['video_id'] = video_id
                
            return parsed_json
            
        except json.JSONDecodeError as e:
            print("Raw content received:")
            print(content)
            print("\nJSON parsing error:", str(e))
            raise ValueError("Invalid JSON received from OpenAI API")
    else:
        raise ValueError("Received None content from OpenAI API")


def get_spreadsheet_data():
    try:
        # Load service account credentials
        # SERVICE_ACCOUNT_FILE = CLIENT_SECRETS_FILE  # Create this file
        # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        # SCOPES = ('https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive')
        # service_account_info = json.loads(secret)
        # my_credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)       
        # credentials = service_account.Credentials.from_service_account_file(
        #     CLIENT_SECRETS_FILE, 
        #     scopes=SCOPES
        # )
        # gc = pygsheets.authorize(service_file=CLIENT_SECRETS_FILE, scopes=SCOPES)

        # key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        gc = pygsheets.authorize(filename="./client_secret.json")

        # with open('./client-secret/config.json', 'r') as config_file:
        #     config = json.load(config_file)
        #     url = config.get('url')

        # if not url:
        #     raise ValueError("URL not found in config.json")

        # sa = SpreadsheetApp(credentials)  # Pass service account credentials
        # spreadsheet = sa.open_by_url(url)
        # sheet1 = spreadsheet.get_sheet_by_name('Youtube')
        # data_range = sheet1.get_data_range()
        # table = Table(data_range, backgrounds=True)
        sh = gc.open('Youtube')
        wks = sh.sheet1
        rng = wks.get_values('A1', 'D31', returnas='range')
        wks.unlink()
        print(rng)
        # table = Table(rng, backgrounds=True)
        
        # for item in table:
        #     title = item.get_field_value('title')
        #     description = item.get_field_value('description')
        #     channel = item.get_field_value('channel')                
        #     url = item.get_field_value('url')        
        #     print(f"Title: {title}")
        #     print(f"Description: {description}")
        #     print(f"Channel: {channel}")
        #     print(f"URL: {url}")
        #     print("-" * 80)
            
    # except Exception as e:
    #     exc_type, exc_obj, exc_tb = sys.exc_info()
    #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1] if exc_tb else "Unknown"
    #     if exc_tb:
    #         print(exc_type, fname, exc_tb.tb_lineno)
    #     else:
    #         print(exc_type, fname, "No traceback available")
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()

        traceback_details = {
                            'filename': exc_traceback.tb_frame.f_code.co_filename if exc_traceback else "Unknown",
                            'lineno'  : exc_traceback.tb_lineno if exc_traceback else "Unknown",
                            'name'    : exc_traceback.tb_frame.f_code.co_name if exc_traceback else "Unknown",
                            'type'    : exc_type.__name__ if exc_type else "Unknown",
                            'message' : str(exc_value),
                            }

        del(exc_type, exc_value, exc_traceback)
        # print(exc_type)
        # print(exc_value)
        # print( exc_traceback)        
        # print()
        print( traceback.format_exc())
        print()
        traceback_template = """
        Traceback (most recent call last):
          File "%(filename)s", line %(lineno)s, in %(name)s
        %(type)s: %(message)s
        """
        print(traceback_template % traceback_details)
        # print(exc_type)
        # print(exc_value)
        # print( exc_traceback)        
        # print()
        print()           
    
if __name__ == "__main__":
    # Define your topics
    beauty_topics = [
        "makeup tutorials",
        "skincare routines",
        "beauty tips",
        "cosmetics reviews",
        "hair styling guides"
    ]
    
    try:
        # Generate video ideas and metadata
        # video_metadata = generate_video_metadata(beauty_topics)
        get_spreadsheet_data()
        # # Print the results in a formatted way
        # for video in video_metadata["videos"]:
        # #     print("\nVideo Idea:")
        # #     print(f"Title: {video['title']}")
        # #     print(f"Filename: {video['filename']}")
        # #     print(f"Description: {video['description']}")
        # #     print(f"Tags: {', '.join(video['tags'])}")
        #     print("-" * 80)
            
    except Exception as e:
        print(f"Error: {str(e)}")
