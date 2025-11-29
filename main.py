import os
import re
import random
import webbrowser
import pvporcupine
from pyowm import OWM
import simpleaudio as sa
from pvrecorder import PvRecorder
from rich import print
import vosk
import pyttsx3
import sys
import queue
import requests
import json
import struct
import config
from fuzzywuzzy import fuzz
import tts
import datetime
from num2words import num2words
import time
import customtkinter
import tkinter as tk
import wikipedia as wiki

from gpytranslate import SyncTranslator
CDIR = os.getcwd()

# init translator
t = SyncTranslator()

# init AI API keys
# openai.api_key=config.OPENAI_TOKEN


# wikipedia settings
wiki.set_lang("ru")

#
engine = pyttsx3.init()

# PORCUPINE
porcupine = pvporcupine.create(
    access_key=config.PICOVOICE_TOKEN,
    keywords=['computer'],
    sensitivities=[1]
)
print(pvporcupine.KEYWORDS)

#gui variables
button_on_top = False


# VOSK
model = vosk.Model("model_small")
samplerate = 16000
device = config.MICROPHONE_INDEX
kaldi_rec = vosk.KaldiRecognizer(model, samplerate)
q = queue.Queue()

def talk(text):
    global engine
    print(text)
    engine.say(text)
    engine.runAndWait()
    ####
    engine.stop()

def gpt_answer(message):
    API_KEY = "AIzaSyACQpp-9_6kd0BZeSqBqCXjXei-2N0u6pQ"
    MODEL_NAME = "gemini-2.5-flash"  # Or another Gemini model

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": f"Ты должен ответить в форме гида для туризма мой вопрос (всё в рамках азербайджана, ответ должен быть меньше чем 900 символов, но старайся дать максимально короткий ответ): '{message}'"}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        return (result['candidates'][0]['content']['parts'][0]['text'])
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
    except KeyError as e:
        print(f"Error parsing API response: {e}")


# play(f'{CDIR}\\sound\\ok{random.choice([1, 2, 3, 4])}.wav')
def play(phrase, wait_done=True):
    global recorder
    filename = f"{CDIR}\\sound\\"

    if phrase == "greet": # for py 3.8
        filename += f"greet{random.choice([1, 2, 3])}.wav"
    elif phrase == "greet1":
        filename += f"greet1.wav"
    elif phrase == "greet1,3":
        filename += f"greet{random.choice([1,3])}.wav"
    elif phrase == "ok1,3":
        filename += f"ok{random.choice([1,3])}.wav"
    elif phrase == "ok":
        filename += f"ok{random.choice([1, 2, 3])}.wav"
    elif phrase == "thanks":
        filename += "thanks.wav"
    elif phrase == "hello":
        filename += "run.wav"

    if wait_done:
        recorder.stop()

    wave_obj = sa.WaveObject.from_wave_file(filename)
    wave_obj.play()

    if wait_done:
        # play_obj.wait_done()
        # time.sleep((len(wave_obj.audio_data) / wave_obj.sample_rate) + 0.5)
        # print("END")
        time.sleep(0.9)
        recorder.start()

def replace_numbers(text):

    replaced_text = re.sub(r'\d+', lambda match: num2words(int(match.group()), lang='ru'), text)

    return replaced_text

def q_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def quite():

    porcupine.delete()
    exit(0)

def geobraceletaway():
    tts.va_speak("Вы вернули браслет обратно, просим перейти к оплате")

def geobraceletgive():
    tts.va_speak("На сколько часов вы хотите взять браслет")
    time = listen()

    with open('TODO_LIST.txt', 'a') as file:
        file.write(f'{time}\n')

    tts.va_speak(f"Вы арендовали браслет на {time}. По окончанию вашего похода требуется вернуть браслет на одну из Т В А станций")

def weather():
    place = config.place
    country = config.country  # Переменная для записи страны/кода страны
    country_and_place = place + ", " + country  # Запись города и страны в одну переменную через запятую
    owm = OWM('5439fa4e5062640c388b9802ffa444aa')  # Ваш ключ с сайта open weather map
    mgr = owm.weather_manager()  # Инициализация owm.weather_manager()
    observation = mgr.weather_at_place(country_and_place)
    # Инициализация mgr.weather_at_place() И передача в качестве параметра туда страну и город
    placen = None

    if place == 'Baku':
        placen = 'Баку'
    w = observation.weather

    status = w.detailed_status  # Узнаём статус погоды в городе и записываем в переменную status
    w.wind()  # Узнаем скорость ветра
    humidity = w.humidity  # Узнаём Влажность и записываем её в переменную humidity
    temp = w.temperature('celsius')['temp']  # Узнаём температуру в градусах по цельсию и записываем в переменную temp
    tts.va_speak("В городе " + str(placen) + " сейчас " + str(status) +  # Выводим город и статус погоды в нём
              "\nТемпература " + num2words(round(temp), lang='ru') + " градусов по цельсию" +  # Выводим температуру с округлением в ближайшую сторону
              "\nВлажность составляет " + num2words(humidity, lang='ru') + "процента" +  # Выводим влажность в виде строки
              "\nСкорость ветра " + num2words(w.wind()['speed'], lang='ru') + " метров в секунду")  # Узнаём и выводим скорость ветра

def va_respond(voice: str):
    global recorder
    print(f"Распознано: {voice}")

    cmd = recognize_cmd(filter_cmd(voice))

    print(cmd)

    if len(cmd['cmd'].strip()) <= 0:
        return False
    elif cmd['percent'] < 70 or cmd['cmd'] not in config.VA_CMD_LIST.keys():
        # play("not_found")
        # tts.va_speak("Что?")
        if voice.startswith("вопрос"):
            gpt_result = gpt_answer(voice)
            recorder.stop()
            print(gpt_result)
            tts.va_speak(gpt_result)
            time.sleep(1)
            recorder.start()
            return False
        elif voice.startswith(('скажи','кто такой', 'что такое', 'вики', 'найди в вики', 'найди в wiki', 'найди в вике','найди в википедии')):
            words = ['кто такой', 'что такое', 'вики', 'найди в вики', 'найди в wiki', 'найди в вике',
                     'найди в википедии']
            remove = ["пожалуйста", "ладно", "давай", "скажи"]
            for i in words:
                voice = voice.replace(i, '')
                for j in remove:
                    voice = voice.replace(j, '')
                    voice = voice.strip()
            try:
                n = wiki.summary({voice}, sentences = 4)
                try:
                    tts.va_speak(replace_numbers(n))
                except:
                    tts.va_speak(
                        "Слишком много текста. Я не могу его произнести. Лучше прочитайте текст который я вам составил")
                # talk(replace_numbers(n))
                print(n)
            except:
                tts.va_speak("Извините не могу найти запрос на вашу тему")
            return True

        elif voice.startswith(('открой гугл', 'гугл', 'запусти гугл', 'загугли', 'найди в интернете', 'найти в интернете', 'ищи в интернете', 'за гугле')):
            words = ['открой гугл', 'гугл', 'запусти гугл', 'загугли', 'найди в интернете', 'ищи в интернете',
                     'за гугле']
            remove = ["пожалуйста", "ладно", "давай", "сейчас", 'открой гугл', 'запусти гугл', 'загугли',
                      'найди в интернете', 'ищи в интернете', 'за гугле']
            for i in words:
                voice =  voice.replace(i, '')
                for j in remove:
                    voice = voice.replace(j, '')
                    voice = voice.strip()
            webbrowser.open(f'https://www.google.com/search?q={voice}')
            play("ok")
            return True
        else:
            time.sleep(1)
            va_respond(listen())
        return False
    else:
        execute_cmd(cmd['cmd'], voice)
        return True


def filter_cmd(raw_voice: str):
    cmd = raw_voice

    for x in config.VA_ALIAS:
        cmd = cmd.replace(x, "").strip()

    for x in config.VA_TBR:
        cmd = cmd.replace(x, "").strip()

    return cmd


def recognize_cmd(cmd: str):
    rc = {'cmd': '', 'percent': 0}
    for c, v in config.VA_CMD_LIST.items():

        for x in v:
            vrt = fuzz.ratio(cmd, x)
            if vrt > rc['percent']:
                rc['cmd'] = c
                rc['percent'] = vrt

    return rc

def listen():
    while time.time() - time.time() <= 10:
        pcm = recorder.read()
        sp = struct.pack("h" * len(pcm), *pcm)

        if kaldi_rec.AcceptWaveform(sp):
            n = json.loads(kaldi_rec.Result())["text"]
            return n


def execute_cmd(cmd: str, voice: str):
    if cmd == 'ctime':
        now = datetime.datetime.now()
        text = "Сейчас " + num2words(now.hour, lang='ru') + " " + num2words(now.minute, lang='ru')
        tts.va_speak(text)

    elif cmd == 'hello':
        play("hello")

    elif cmd == 'weather':
        weather()

    elif cmd == 'stop':
        quit()

    elif cmd == 'restart':
        recorder.stop()
        os.system("python main.py")

    elif cmd == 'thanks':
        play("thanks", False)
        cycle()

    elif cmd == 'off':
        quite()


# `-1` is the default input audio device.

recorder = PvRecorder(device_index=config.MICROPHONE_INDEX, frame_length=porcupine.frame_length)
recorder.start()
print('Using device: %s' % recorder.selected_device)

print(f"Jarvis (v3.0) начал свою работу ...")
time.sleep(0.5)

ltc = time.time() - 1000
# ------------------------------UI---------------------------------------

def button_click():
    global button_on_top

    if not button_on_top:
        # Первое нажатие - перемещаем кнопку наверх
        button.place(relx=0.5, rely=0.1, anchor='center')  # Верх экрана
        button_on_top = True
        cycle()
    else:
        # Второе нажатие - возвращаем кнопку в центр
        button.place(relx=0.5, rely=0.5, anchor='center')  # Центр экрана
        button_on_top = False
        quit()


# Создание главного окна
root = tk.Tk()
root.title("Перемещаемая кнопка")
root.geometry("960x540")
root.resizable(False, False)

# Создание кнопки
button = tk.Button(
    root,
    text="Нажми меня",
    command=button_click,
    width=15,
    height=2,
    font=("Arial", 12)
)

def cycle():
    print("Yes, sir.")
    play("greet1")
    recorder.start()  # prevent self recording
    ltc = time.time()
    while time.time() - ltc <= 10:
        pcm = recorder.read()
        sp = struct.pack("h" * len(pcm), *pcm)

        if kaldi_rec.AcceptWaveform(sp):
            if va_respond(json.loads(kaldi_rec.Result())["text"]):
                ltc = time.time()

                    # -------------------------------
                    # if kaldi_rec.AcceptWaveform(sp):
                    #     n = json.loads(kaldi_rec.Result())["text"]
                    #     return n
        # try:
        #     pcm = recorder.read()
        #     keyword_index = porcupine.process(pcm)
        #
        #
        #     #print(sd.query_devices())
        #
        #     if keyword_index >= 0:
        #         print("Yes, sir.")
        #         play("greet1")
        #         recorder.start()  # prevent self recording
        #         ltc = time.time()
        #         while time.time() - ltc <= 10:
        #             pcm = recorder.read()
        #             sp = struct.pack("h" * len(pcm), *pcm)
        #
        #             if kaldi_rec.AcceptWaveform(sp):
        #                 if va_respond(json.loads(kaldi_rec.Result())["text"]):
        #                     ltc = time.time()
        #
        #             # -------------------------------
        #             # if kaldi_rec.AcceptWaveform(sp):
        #             #     n = json.loads(kaldi_rec.Result())["text"]
        #             #     return n
        #
        # except Exception as err:
        #     print(f"Unexpected {err=}, {type(err)=}")
        #     raise
button.place(relx=0.5, rely=0.5, anchor='center')

# Запуск главного цикла
root.mainloop()