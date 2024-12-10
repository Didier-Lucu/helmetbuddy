import openai
import speech_recognition as sr

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

def split_first_word(s):

    parts = s.split(maxsplit=1)
    first_word = parts[0] if parts else ''
    rest = parts[1] if len(parts) > 1 else ''
    
    return first_word, rest

def listen(r, source):

    audio = r.listen(source)
    text = r.recognize_google(audio, language="en-US")

    return text


def listen_respond(r, source):

    text = listen(r, source)

    return response(text) # returns first_word , rest




def response(text):

    response = openai.chat.completions.create(model = 'gpt-3.5-turbo', messages=[
                        {"role":"system","content": f"{content}"},
                        {"role": "user", "content": f"{text}"}
                        ]) 
    

    first_word, rest = split_first_word(response.choices[0].message.content)
    return first_word, rest