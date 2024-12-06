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
ssl._create_default_https_context = ssl._create_unverified_context

from customtypes import *
 
app = Flask(__name__)
camera = cv2.VideoCapture(0)
websocket_thread = None
ding_sound = None
client = None
engine = None
lastTime = None

r = sr.Recognizer()
content = {
''' 
Helmet Buddy is a smart helmet interface for bikers. It will enable or disable specific functionalities based on user questions and commands, and for certain genres of questions, will respond with one to two-word trigger phrases that enable functions in a connected Python script. Here are the behavior rules: 

0. If provided a location provide the weather in that location currently 

1. For questions about the user's current location, such as 'Where am I?', 'What city am I in?', or 'What state am I in?', Helmet Buddy will respond with 'location'.  

2. For questions or commands asking to post on Twitter, open Twitter, or use Twitter in any form, Helmet Buddy will respond with 'twitter'. 

3. For questions or commands regarding turning on car detection or asking to look out for cars, Helmet Buddy will respond with 'cardetect'. 

4. For any other questions or comments, If the question makes sense then Helmet Buddy will respond with its own knowledge or look up the answer online if needed, using its built-in tools. It will either directly provide an answer or retrieve real-time information. Helmet Buddy will respond with 'smartchat' as its first word. 

'''
}
def startup():
    global lastTime

    lastTime = time.time()

    load_dotenv()

    init_LLM()
    init_tts()
    init_twitter()
    init_voice_engine()
    init_buzzer()
    start_flask_thread()

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

def play_ding_sound():

    if ding_sound is None:
        print("No sound loaded.")
        return

    ding_sound.play()
    while pygame.mixer.get_busy() == True:
        time.sleep(0.1) # Prevents high CPU usage
    pygame.mixer.stop()

def twitter_confirmation(message):
    try:
        engine.say("Tweeting your message")
        engine.runAndWait()
        response = client.create_tweet(text=message)
    except tweepy.TweepyException as e:
        engine.say("Message Failed to Tweet")
        engine.runAndWait()

            
    engine.say("Message Tweeted")
    engine.runAndWait()

    return
                

def twitter(source):

    engine.say("What would you like to tweet?")
    engine.runAndWait()
    while True:
        play_ding_sound()
        audio = r.listen(source)
        text = r.recognize_google(audio)
        time.sleep(1)
        engine.say(f"You said: {text} , would you like to tweet this? Say yes to tweet your message no to redue yourmessage or cancel to exit")
        engine.runAndWait()
        play_ding_sound()
        audio = r.listen(source)
        text2 = r.recognize_google(audio)
        if "yes" in text2.lower():
            try:
                twitter_confirmation(source,text)
                return
                
            except sr.UnknownValueError:
                print('Silence Detected')
                pass
        elif "cancel" in text2.lower():
            return
        else:
            engine.say("Please repeat your message after the beep.")
            engine.runAndWait()

def send_message(MESSAGE = "Your loved one" + str(os.getenv('NAME')) + "had a car get too close to him and he may have been hit."):

    
    CARRIER = "verizon"



    EMAIL = "helmetbuddy7@gmail.com"
    PASSWORD = "tfdz xmzq tigr katv"

    CARRIERS = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtext.com",
    "sprint": "@messaging.sprintpcs.com"
    }

    recipient = "5307151598@vtext.com"
    auth = (EMAIL, PASSWORD)
 
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
 
    server.sendmail(auth[0], recipient, MESSAGE)

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
                
    except :
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
	
    finally:
        gps_serial.close()
        print("Program terminated by j")
        return

def main():
    pass

def split_first_word(s):

    parts = s.split(maxsplit=1)
    first_word = parts[0] if parts else ''
    rest = parts[1] if len(parts) > 1 else ''
    
    return first_word, rest

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

        if (lastTime - time.time() >= 180):
            voiceCalibrate(source)
        try:
            audio = r.listen(source)
            text = r.recognize_google(audio, language="en-US")
            # text2 = r.recognize_whisper(audio)

            # print("text: " + text)

            if "hey buddy" in text.lower():
            
                play_ding_sound()
                audio = r.listen(source)
                text = r.recognize_google(audio, language="en-US")
                text = text.lower()
                response = openai.chat.completions.create(model = 'gpt-3.5-turbo', messages=[
                    {"role":"system","content": f"{content}"},
                    {"role": "user", "content": f"{text}"}
                    ]) 
                response_text = response.choices[0].message.content
                print(response_text)
                first_word, rest = split_first_word(response_text)
                time.sleep(1)
                
                if first_word == "smartchat":
                    smartChat(rest)

                elif first_word == "location":
                    get_current_location(mode = "location")

                elif first_word == "twitter":
                    twitter()
                    
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
        except sr.UnknownValueError or sr.WaitTimeoutError:
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
    