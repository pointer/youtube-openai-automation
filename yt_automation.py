import os
import random
import sys
import time
import pickle
import http.client as httplib
import httplib2
import argparse
from typing import List
import rich
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from openai import OpenAI

import requests
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pytubefix import YouTube
from pytube import request


video_data = []

def get_openai_api_key() -> str:
    if os.path.exists("./client-secret/openai-api-key.json"):
      with open("./client-secret/openai-api-key.json", "r") as openai_api_key_file:
        openai_api_key_handle = json.load(openai_api_key_file)
        OPENAI_API_KEY = openai_api_key_handle['openai']['api_key']
        return OPENAI_API_KEY
    return ""
       
def generate_video_metadata(topics):
    api_key_ = get_openai_api_key()  
    client = OpenAI(api_key=api_key_)

    completion = client.chat.completions.create(
        model="gpt-4",
        max_tokens=2000,  # Increased token limit for complete responses
        messages=[
            {
                "role": "system", 
                "content": "You are a video content specialist. Provide only valid JSON responses. Keep descriptions under 50 words."
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
                
            return parsed_json
            
        except json.JSONDecodeError as e:
            print("Raw content received:")
            print(content)
            print("\nJSON parsing error:", str(e))
            raise ValueError("Invalid JSON received from OpenAI API")
    else:
        raise ValueError("Received None content from OpenAI API")

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
        video_metadata = generate_video_metadata(beauty_topics)
        
        # Print the results in a formatted way
        for video in video_metadata["videos"]:
            print("\nVideo Idea:")
            print(f"Title: {video['title']}")
            print(f"Filename: {video['filename']}")
            print(f"Description: {video['description']}")
            print(f"Tags: {', '.join(video['tags'])}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error: {str(e)}")
