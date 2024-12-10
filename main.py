import os
import openai
import time
import speech_recognition as sr
from dotenv import load_dotenv
import pyttsx3
import tweepy
import pygame
from geopy.geocoders import Nominatim
import geocoder
import smtplib
from serial import Serial
import threading
import asyncio
import websockets
from flask import Flask, Response
import cv2
import ssl

from helpers import confirmation, listen, listen_respond, play_ding_sound
# ssl._create_default_https_context = ssl._create_unverified_context

from customtypes import *
 
app = Flask(__name__)
camera = cv2.VideoCapture(0)
websocket_thread = None
ding_sound = None
client = None
engine = None
lastTime = None
EMAIL_USER = None
EMAIL_PASSWORD = None
SERVER = None
AUTH = None

r = sr.Recognizer()

def startup():
    global lastTime

    lastTime = time.time()

    load_dotenv()

    init_messages()
    init_LLM()
    init_tts()
    init_twitter()
    init_voice_engine()
    init_buzzer()
    start_flask_thread()


def init_messages():
    global EMAIL_USER, EMAIL_PASSWORD, SERVER, AUTH

    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    AUTH = (EMAIL_USER, EMAIL_PASSWORD)
    SERVER = smtplib.SMTP("smtp.gmail.com", 587)

def init_voice_engine():
    global r
    # Allows for auto fluxution of enery_threshold
    # ie changes what level of volume of speech is detected
    # Used to filter out backround noise
    r.dynamic_energy_threshold = True 
    r.energy_threshold = 500
    # Pause in speech in seconds to signify end of message
    r.pause_threshold = 0.8

    '''
    Possible add-ons:
    .record
    .adjust_for_ambient_noise(source: AudioSource, duration: float = 1) # Maybe run every minute for a few seconds

    '''

def init_LLM():

    openai.api_key = os.getenv('OPEN_API_KEY')
    os.environ['OPENAI_API_KEY'] = openai.api_key

def init_tts():
    global engine
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'english' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break


def init_twitter():

    global client

    client = tweepy.Client(
        consumer_key=os.getenv('CONSUMER_KEY'), consumer_secret=os.getenv('CONSUMER_SECRET'),
        access_token=os.getenv('ACCESS_TOKEN'), access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
    )

def init_buzzer():

    global ding_sound

    pygame.init()
    pygame.mixer.init()
    try:
        ding_sound = pygame.mixer.Sound(os.getenv('BUZZER_PATH'))
    except pygame.error as e:
        print(f"Unable to load sound file: {e}")
        ding_sound = None

def generate_frames():

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Function to run the Flask app in a separate thread
def run_flask_app():
    global app
    app.run(host='0.0.0.0', port=5000)

def start_flask_thread():
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()


def twitter_confirmation(message):

    try:
        response = client.create_tweet(text=message)
    except tweepy.TweepyException as e:
        engine.say("Message Failed to Tweet")
        engine.runAndWait()
        return

    engine.say("Message Tweeted")
    engine.runAndWait()

    return

def twitter(source):

    while True:

        engine.say("What would you like to tweet?")
        engine.runAndWait(),
        play_ding_sound(ding_sound)
        text = listen(r, source)
        time.sleep(1)
        confirm = confirmation(engine, r, source, text, ding_sound)
        if (confirm):
            twitter_confirmation(text)
            break
        elif(confirm == None):
            break
        elif(not confirm):
            pass
    
    return

        

def send_message(MESSAGE = "Your loved one" + str(os.getenv('NAME')) + "had a car get too close to him and he may have been hit."):

    
    CARRIER = "verizon"


    CARRIERS = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtext.com",
    "sprint": "@messaging.sprintpcs.com"
    }


    
    recipient = "5307151598@vtext.com"
    
 
    SERVER.starttls()
    SERVER.login(AUTH[0], AUTH[1])
    SERVER.sendmail(AUTH[0], recipient, MESSAGE)
    SERVER.quit()

def back_up_location():

    g = geocoder.ip('me')
    print(g.latlng)
    print(g.city)
    print(g.postal)

    return g.latlng[0] , g.latlng[1]

def get_current_location(mode):
    latlong = LatLong(None,None)
    gpsConnection = True


    geolocator = Nominatim(user_agent = "gps_example")

    try:
        gps_serial = Serial('/dev/ttyUSB0', baudrate = 9600, timeout = 1)
        gps_data = gps_serial.readline().decode('utf-8', errors='ignore').strip()
        fields = gps_data.split(',')
        
        if 'GPGGA' in gps_data or 'GNGGA' in gps_data:
            

            if fields[2][:2] == '':
                
                engine.say("No connection Running backup wifi location")
                engine.runAndWait()
                latlong.latitude, latlong.longitude = back_up_location()
            else:
                latlong.latitude = float(fields[2][:2]) + float(fields[2][2:]) / 60.0
                latlong.longitude = float(fields[4][:3]) + float(fields[4][3:]) / 60.0
                latlong.longitude = -latlong.longitude
        
            if -90 <= latlong.latitude <= 90 and -180 <= latlong.longitude <= 180:
            
                location = geolocator.reverse((latlong.latitude, latlong.longitude), language = 'en')
            
                address = location.address
                city = location.raw.get('address', {}).get('city', 'N/A')
            
                if (mode == "weather"):
                    return address
                engine.say("You are located near" + address)
                engine.runAndWait()
                gps_serial.close()
                return
                
    except Exception as e:
        print("GPS not connected")
        engine.say("No connection Running backup wifi location")
        engine.runAndWait()
        latlong.latitude, latlong.longitude = back_up_location()
        location = geolocator.reverse((latlong.latitude, latlong.longitude), language = 'en')
            
        address = location.address
        city = location.raw.get('address', {}).get('city', 'N/A')
    
        if (mode == "weather"):
            return address
        engine.say("You are located near" + address)
        engine.runAndWait()
        return

def main():
    pass


def smartChat(rest):

    engine.say(rest)
    engine.runAndWait()
    return 

def voiceCalibrate(source):

    global r

    r.adjust_for_ambient_noise(source, 1)
    return

def menu_triggered(source):

    global objclass
    global lastTime
    engine.say("Main Menu")
    engine.runAndWait()

    while True:

        if (time.time() - lastTime >= 180):
            voiceCalibrate(source)
            lastTime = time.time()
        try:

            text  = listen(r, source)
            

            if "hey buddy" in text.lower():
            
                play_ding_sound(ding_sound)
                
                first_word, rest = listen_respond(r, source)

                time.sleep(1)
                
                if first_word == "smartchat":
                    smartChat(rest)

                elif first_word == "location":
                    get_current_location(mode = "location")

                elif first_word == "twitter":
                    twitter(source)
                    
                elif first_word == "weather":
                    address = get_current_location(mode = "weather")


                elif first_word == "car detect on":
                    print("Activating Rear-View Car Detection Camera")
                    engine.say("Activating Car Detection")
                    engine.runAndWait()
                   # behindOn()
                    break
                elif first_word == "car detect off":
                    print("Deactivating Rear-View Car Detection Camera")
                    engine.say("Deactivating Car Detection")
                    engine.runAndWait()
                   # behindOff()
                    break
                elif first_word == "objdetect":
                    pass
        except sr.UnknownValueError or sr.WaitTimeoutError or  Exception:
            print("ERROR")
            continue
    
    websocket_thread.join()

with sr.Microphone() as source:
    startup()
    while True:
        #m#ain_thread = threading.Thread(target=initial(source))
        # object_detection_thread = threading.Thread(target=behind)
        # Thread-safe event object to control execution of the object detection thread
        # object_detection_thread.start()
        # object_detection_event.clear()
        ##main_thread.start()
        menu_triggered(source)
        # main(source)
    