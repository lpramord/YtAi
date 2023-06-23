from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import os
import openai

import requests

import json

import pyttsx3

from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip

from PIL import Image, ImageDraw, ImageFont

from datetime import date

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import httplib2
from google.oauth2 import credentials as google_credentials

openai.api_key = os.getenv("APIKEY")

def create_story(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1500,
        temperature=0.5,
        n=1,
        stop=None,
    )
    return response.choices[0].text.strip()

prompt = "A Children story which contain more than 1000 words"
story = create_story(prompt)

def separate_paragraphs(text):
    paragraphs = text.split("\n\n")
    paragraphs = [paragraph.strip() for paragraph in paragraphs]
    return paragraphs

paragraphs = separate_paragraphs(story)

def keywordCheck(paragraph):
    phw = paragraph.split()
    keywords = open('./keywords.txt','r').read().split('\n')
    skw = []
    for item in phw:
        if item in keywords:
            skw.append(item)
    for word1 in keywords:
        for word2 in phw:
            if word1.lower() == word2.lower():
                skw.append(word2)
    return skw

for i, paragraph in enumerate(paragraphs):
    sw = keywordCheck(paragraph)
    if sw:
        if len(sw)==1:
            words = sw[0]
        else:
            words = '+'.join(str(element) for element in sw)
        url = 'https://pixabay.com/api/videos/?key='+str(os.getenv('KEY'))+'&q='+words
        resonce = requests.get(url).content.decode('utf-8')
        jsonArray = json.loads(resonce)
        if jsonArray['total']!= 0:
            video = requests.get(jsonArray['hits'][0]['videos']['medium']['url'])
            name = './rawVideos/'+str(sw[0])+'.mp4'
            with open(name, 'wb') as file:
                file.write(video.content)

audioPath = './rawAudio/story.mp3'

def narrate_story(story_text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150) 
    engine.setProperty('volume', 0.8)
    engine.setProperty('voice', 'en-us')

    engine.save_to_file(story_text,audioPath)
    engine.runAndWait()

narrate_story(story)

audio = AudioFileClip(audioPath)

directory = "./rawVideos"

file_list = [os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]
video_paths = sorted(file_list, key=lambda x: os.path.getmtime(x))

output_path = "./update/"+str(date.today())+".mp4"

video_clips = [VideoFileClip(path) for path in video_paths]
final_clip = concatenate_videoclips(video_clips)
video = final_clip.set_audio(audio)
video.write_videofile(output_path)

video.close()
final_clip.close()
for video in video_clips:
    video.close()
audio.close()

for video in video_paths:
    os.remove(video)
os.remove(audioPath)

prompt = story + 'give me a super simple title for it'
tittle = create_story(prompt)

prompt = story + 'give me a simple discription for it'
discription = create_story(prompt)

words = tittle.split(' ')
words1 = '+'.join(str(element) for element in words)

name = './rwaPhoto/'+str(date.today())+'.png'

ict = 0

def getImage(search):
    global ict,words1,words,name
    url = 'https://pixabay.com/api/?key='+str(os.getenv('KEY'))+'&q='+search+'&orientation=horizontal'
    resonce = requests.get(url).content.decode('utf-8')
    jsonArray = json.loads(resonce)
    if jsonArray['total']!= 0:
        image = requests.get(jsonArray['hits'][0]['largeImageURL'])
        with open(name, 'wb') as file:
            file.write(image.content)
    else:
        ict= ict+1
        if ict <= len(words):
            getImage(words[ict-1])
        else:
            ict = 0
            prompt = story + 'give me a other super simple title for it'
            tittle1 = create_story(prompt)
            words = tittle1.split(' ')
            words1 = '+'.join(str(element) for element in words)
            getImage(words1)

getImage(words1)

image = Image.open(name)
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('./fonts/RubikIso-Regular.ttf', size=40)

text_box = draw.textbbox((0, 0), tittle, font=font)

text_width = text_box[2] - text_box[0]
text_height = text_box[3] - text_box[1]

background_color = (255, 255, 255, 128)

center_x = (image.width - text_width) // 2
center_y = (image.height - text_height) // 2

x1 = center_x - 10
y1 = center_y - 10
x2 = center_x + text_width + 10
y2 = center_y + text_height + 10

draw.rectangle([(x1, y1), (x2, y2)], fill=background_color)

text_position = (center_x, center_y)

text_color = (0, 0, 0)

draw.text(text_position, tittle, font=font, fill=text_color)

thumblocation = "./thumbnails/"+str(date.today())+".png"

image.save(thumblocation)

image.close()

os.remove(name)

client_secrets_file = "./client_secret.json"
scopes = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes=scopes)
credentials = flow.run_local_server(port=8080)

refresh_token = credentials.refresh_token

data = {
    "refresh_token": refresh_token
}

youtube = build("youtube", "v3", credentials=credentials)

request_body = {
    "snippet": {
        "title": tittle,
        "description": discription,
        "tags": words,
        "categoryId": "22",
        "thumbnails": {
            "default": {
                "url": thumblocation
            }
        }
    },
    "status": {
        "privacyStatus": "public"
    }
}

request1 = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=output_path
)

with open('refresh_token.json', 'w') as file:
    json.dump(data, file)

timeout=3600
http = httplib2.Http(timeout=timeout)
response = request1.execute(http=http)
print("Video uploaded successfully! Video ID:", response["id"])