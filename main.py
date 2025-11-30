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
import string
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
import threading
import qrcodegen
from PIL import Image
import customtkinter
import wikipedia as wiki

from gpytranslate import SyncTranslator
CDIR = os.getcwd()

# init translator
t = SyncTranslator()

global aianswer
aianswer = ""
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

# ------------------------------UI-------------------------------

# --- applic config ---
customtkinter.set_appearance_mode("Dark")
# Цветовая схема: "dark-blue" хорошо сочетается с горами, но мы добавим свои цвета
customtkinter.set_default_color_theme("dark-blue")

app = customtkinter.CTk()
app.title("TourVoice Assistant")
app.geometry("1024x700")

# Глобальное состояние
app_state = {
    "is_processing": False,
    "qr_window_open": False
}

# Шрифты (Крупные для удобства чтения)
FONT_HEADER = ("Roboto", 28, "bold")
FONT_MENU = ("Roboto", 24, "bold")
FONT_BODY = ("Roboto", 18)
FONT_BUTTON = ("Roboto", 18, "bold")
FONT_SMALL = ("Roboto", 14)


# Загрузка FAQ из JSON
FAQ_FILE = os.path.join(os.path.dirname(__file__), "faq.json")

def load_faq():
    try:
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке FAQ: {e}")
        return []


def show_faq():
    faq_window = customtkinter.CTkToplevel(app)
    faq_window.title("❓ ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ")
    faq_window.geometry("700x600")
    faq_window.attributes("-topmost", True)

    # Сетка окна
    faq_window.grid_columnconfigure(0, weight=1)
    faq_window.grid_rowconfigure(0, weight=1)
    faq_window.grid_rowconfigure(1, weight=10)

    # Заголовок
    header_label = customtkinter.CTkLabel(
        faq_window,
        text="❓ ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ",
        font=FONT_HEADER,
        text_color="#4CB8F5"
    )
    header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

    faq_frame = customtkinter.CTkScrollableFrame(faq_window, fg_color="transparent")
    faq_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
    faqs = load_faq()

    # showing Q&A pear
    for idx, faq_item in enumerate(faqs):
        # question (bold, blue)
        q_label = customtkinter.CTkLabel(
            faq_frame,
            text=faq_item["q"],
            font=FONT_BUTTON,
            text_color="#4CB8F5",
            wraplength=600,
            justify="left"
        )
        q_label.pack(anchor="w", padx=10, pady=(15, 5))

        # Ответ (обычный текст)
        a_label = customtkinter.CTkLabel(
            faq_frame,
            text=faq_item["a"],
            font=FONT_BODY,
            text_color="gray",
            wraplength=600,
            justify="left"
        )
        a_label.pack(anchor="w", padx=20, pady=(0, 10))

    close_button = customtkinter.CTkButton(
        faq_window,
        text="Закрыть",
        font=FONT_BUTTON,
        fg_color="#555555",
        command=faq_window.destroy
    )
    close_button.grid(row=2, column=0, padx=20, pady=(0, 20))


def generate_gps_bracelet():
    if app_state["qr_window_open"]:
        return

    app_state["qr_window_open"] = True

    issue_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    bracelet_key = generate_bracelet_key()
    bracelet_id = f"ALP-{bracelet_key}-GPS"

    contact_info = config.helptelnum
    qr_data = f"https://tourvoiceassistant.netlify.app/sample?id={bracelet_key}"

    qr_window = customtkinter.CTkToplevel(app)
    qr_window.title("Выдача GPS-трекера")
    qr_window.geometry("800x450")
    qr_window.attributes("-topmost", True)

    def on_close():
        app_state["qr_window_open"] = False
        qr_window.destroy()

    qr_window.protocol("WM_DELETE_WINDOW", on_close)

    qr_window.grid_columnconfigure(0, weight=1)
    qr_window.grid_columnconfigure(1, weight=1)
    qr_window.grid_rowconfigure(0, weight=1)


    # left corner
    info_frame = customtkinter.CTkFrame(qr_window, fg_color="transparent")
    info_frame.grid(row=0, column=0, padx=30, pady=30, sticky="nswe")

    customtkinter.CTkLabel(info_frame, text="🏔️ АКТИВАЦИЯ БРАСЛЕТА", font=FONT_HEADER, text_color="#4CB8F5").pack(
        anchor="w", pady=(0, 20))

    # Helper for some good looking labels
    def add_info_row(label, value):
        customtkinter.CTkLabel(info_frame, text=label, font=("Roboto", 14, "bold"), text_color="gray").pack(anchor="w")
        customtkinter.CTkLabel(info_frame, text=value, font=("Roboto", 22), text_color="white").pack(anchor="w",
                                                                                                     pady=(0, 15))

    add_info_row("ДАТА ВЫДАЧИ:", issue_date)
    add_info_row("ID УСТРОЙСТВА:", bracelet_id)
    add_info_row("КЛЮЧ ДОСТУПА:", bracelet_key)
    add_info_row("ЭКСТРЕННАЯ СВЯЗЬ:", contact_info)

    customtkinter.CTkLabel(info_frame, text="ℹ️ Сканируйте QR для проверки статуса", font=FONT_SMALL,
                           text_color="gray").pack(side="bottom", anchor="w")

    # first part qrcode
    qr_frame = customtkinter.CTkFrame(qr_window, fg_color="#FFFFFF", corner_radius=20)  # Белый фон для QR
    qr_frame.grid(row=0, column=1, padx=30, pady=30)

    # gen qrcode
    qr_frame = customtkinter.CTkFrame(qr_window, fg_color="#FFFFFF", corner_radius=20)  # Белый фон для QR
    qr_frame.grid(row=0, column=1, padx=30, pady=30)

    # gen qrcode с использованием qrcodegen
    qr = qrcodegen.QrCode.encode_text(qr_data, qrcodegen.QrCode.Ecc.MEDIUM)

    # convert to PIL
    border = 2
    scale = 10
    size = (qr.get_size() + border * 2) * scale
    img = Image.new('RGB', (size, size), 'white')
    pixels = img.load()

    for y in range(qr.get_size()):
        for x in range(qr.get_size()):
            if qr.get_module(x, y):
                for dy in range(scale):
                    for dx in range(scale):
                        px = (x + border) * scale + dx
                        py = (y + border) * scale + dy
                        pixels[px, py] = (0, 0, 0)  # Черный цвет

    # convert for CTk
    ctk_qr_image = customtkinter.CTkImage(light_image=img, size=(250, 250))

    img_label = customtkinter.CTkLabel(qr_frame, text="", image=ctk_qr_image)
    img_label.pack(padx=20, pady=20)


def listen_and_respond_for_ui():
    global aianswer
    aianswer = ""
    print("Начинаю слушать...")
    recorder.start()

    start_time = time.time()
    timeout = 10

    while time.time() - start_time <= timeout:
        pcm = recorder.read()
        sp = struct.pack("h" * len(pcm), *pcm)

        if kaldi_rec.AcceptWaveform(sp):
            voice_text = json.loads(kaldi_rec.Result())["text"]
            print(f"Распознано из UI: {voice_text}")

            if voice_text and len(voice_text.strip()) > 0:
                recorder.stop()
                va_respond(voice_text)

                # Выходим из цикла
                break

    # Останавливаем recorder
    try:
        recorder.stop()
    except:
        pass

    return aianswer


def heavy_function_placeholder():
    global aianswer

    def run_listen_in_thread():
        global aianswer
        aianswer = ""
        answer_to_speak = ""

        try:
            # Вызываем специальную функцию для UI
            result_text = listen_and_respond_for_ui()

            print(f"DEBUG: aianswer после listen_and_respond = '{aianswer}'")

            # Сохраняем текст для озвучивания
            if aianswer and len(aianswer.strip()) > 0:
                answer_to_speak = aianswer

        except Exception as e:
            print(f"Ошибка в listen_and_respond_for_ui(): {e}")
            aianswer = f"Произошла ошибка: {str(e)}"
            answer_to_speak = aianswer

        # Формируем результат для UI
        if aianswer and len(aianswer.strip()) > 0:
            result = (
                "🏔️ ОТВЕТ ПОЛУЧЕН\n\n"
                f"{aianswer}"
            )
        else:
            result = (
                "⏱️ ВРЕМЯ ВЫШЛО\n\n"
                "Не удалось распознать команду.\n"
                "Попробуйте еще раз."
            )

        print(f"DEBUG: Финальный result = '{result[:100]}...'")

        # update UI
        app.after(0, finish_process, result)

        # Ждем немного чтобы UI успел отобразиться
        time.sleep(0.3)

        # only then start to speaks
        if answer_to_speak:
            try:
                # Deleting emojis
                speech_text = answer_to_speak.replace("🌤️", "").replace("🏔️", "").replace("✅", "").replace("❌",
                                                                                                             "").replace(
                    "⏱️", "")

                # Заменяем переносы строк на паузы
                speech_text = speech_text.replace("\n\n", ". ").replace("\n", ". ")

                # Убираем лишние пробелы
                speech_text = " ".join(speech_text.split())

                print(f"DEBUG: Озвучиваю текст: '{speech_text[:100]}...'")

                # Озвучиваем очищенный текст
                tts.va_speak(speech_text)
            except Exception as e:
                print(f"Ошибка при озвучивании: {e}")

    # Запускаем в отдельном потоке
    thread = threading.Thread(target=run_listen_in_thread, daemon=True)
    thread.start()


def animate_button_pulse(step=0):
    if not app_state["is_processing"]:
        action_button.configure(border_width=0)
        return
    # Анимация "Горный пульс" (сине-белые тона)
    border_colors = ["#FFFFFF", "#89CFF0", "#4CB8F5", "#1E90FF"]
    color = border_colors[step % len(border_colors)]
    action_button.configure(border_width=5, border_color=color)
    app.after(200, animate_button_pulse, step + 1)


def start_process():
    if app_state["is_processing"]:
        return

    app_state["is_processing"] = True
    action_button.configure(state="disabled", text="🎤 СЛУШАЮ...", fg_color="#555555")
    animate_button_pulse()

    # Запускаем асинхронную обработку
    heavy_function_placeholder()


def finish_process(result_text):
    app_state["is_processing"] = False

    # Возврат кнопки в исходное состояние (но меньше)
    action_button.configure(
        state="normal", text="СПРОСИТЬ ЕЩЁ", height=50, width=250,
        font=FONT_BUTTON, fg_color="transparent", border_width=2, border_color="#FFFFFF"
    )

    # Анимация сдвига вверх
    main_frame.grid_rowconfigure(0, weight=0)
    main_frame.grid_rowconfigure(1, weight=0)
    main_frame.grid_rowconfigure(2, weight=0)
    main_frame.grid_rowconfigure(3, weight=1)

    action_button.grid(row=0, column=0, pady=(50, 30))

    # Показ результата
    result_textbox.configure(state="normal")
    result_textbox.delete("0.0", "end")
    result_textbox.insert("0.0", result_text)
    result_textbox.configure(state="disabled")
    result_textbox.grid(row=1, column=0, padx=40, pady=10)

# --- СОЗДАНИЕ ИНТЕРФЕЙСА (Layout) ---

app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# 1. ЛЕВАЯ ПАНЕЛЬ (SIDEBAR) - Стиль "Камень и Снег"
sidebar_frame = customtkinter.CTkFrame(app, width=240, corner_radius=0, fg_color="#2B2B2B")
sidebar_frame.grid(row=0, column=0, sticky="nsew")
sidebar_frame.grid_rowconfigure(10, weight=1) # Распорка снизу

# Логотип
customtkinter.CTkLabel(sidebar_frame, text="🏔️ TourVoice\nAssistant",
                       font=("Arial Black", 20), text_color="white").grid(row=0, column=0, padx=15, pady=(40, 30), sticky="w")

# Кнопка GPS (Акцентная)
btn_gps = customtkinter.CTkButton(
    sidebar_frame,
    text="📡 ВЫДАТЬ GPS\nБРАСЛЕТ",
    font=FONT_BUTTON,
    height=80, # Большая кнопка
    fg_color="#D9534F", # Красноватый цвет (Rescue/Safety)
    hover_color="#C9302C",
    command=generate_gps_bracelet
)
btn_gps.grid(row=1, column=0, padx=15, pady=15, sticky="ew")

# Кнопка FAQ
btn_faq = customtkinter.CTkButton(
    sidebar_frame,
    text="❓ ПОМОЩЬ",
    font=FONT_BUTTON,
    height=50,
    fg_color="#555555",
    command=show_faq
)
btn_faq.grid(row=2, column=0, padx=15, pady=10, sticky="ew")

# Переключатель темы (внизу) - Большой Switch без текста, с адаптивными цветами
theme_label = customtkinter.CTkLabel(sidebar_frame, text="Выбор темы:", font=FONT_SMALL)
theme_label.grid(row=11, column=0, padx=15, pady=(15, 8), sticky="w")

theme_frame = customtkinter.CTkFrame(sidebar_frame, fg_color="transparent")
theme_frame.grid(row=12, column=0, padx=15, pady=(0, 20), sticky="w")

def toggle_theme():
    current = customtkinter.get_appearance_mode()
    mode = "Dark" if current == "Light" else "Light"
    customtkinter.set_appearance_mode(mode)
    # Обновить цвет фона переключателя после смены темы
    update_switch_colors()

def update_switch_colors():
    """Обновить цвета переключателя в зависимости от темы"""
    is_light = customtkinter.get_appearance_mode() == "Light"
    # Для Light режима: фон белый, для Dark: фон чёрный
    bg_color = "#FFFFFF" if is_light else "#000000"
    theme_switch.configure(fg_color=(bg_color, bg_color))

theme_switch = customtkinter.CTkSwitch(
    theme_frame,
    text="",  # Без текста
    command=toggle_theme,
    width=200,  # Увеличено в два раза (было 70)
    height=100   # Увеличено в два раза (было 35)
)
theme_switch.pack(side="left")
theme_switch.select() if customtkinter.get_appearance_mode() == "Light" else theme_switch.deselect()
update_switch_colors()


# 2. ЦЕНТРАЛЬНАЯ ПАНЕЛЬ - Фон с оттенком
main_frame = customtkinter.CTkFrame(app, fg_color="transparent")
main_frame.grid(row=0, column=1, sticky="nsew")

# Сетка центра
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_rowconfigure(1, weight=0)
main_frame.grid_rowconfigure(2, weight=0)
main_frame.grid_rowconfigure(3, weight=1)

# Главная КНОПКА (Стиль "Свежий снег")
action_button = customtkinter.CTkButton(
    main_frame,
    text="🎙️ НАЖМИ ЧТОБЫ ГОВОРИТЬ",
    font=("Roboto", 32, "bold"),
    height=120, # Очень большая для 35+
    width=400,
    corner_radius=60,
    fg_color="#1E90FF", # Яркий синий (цвет неба в горах)
    hover_color="#104E8B",
    command=start_process
)
action_button.grid(row=1, column=0, pady=20)

# Подпись для кнопки
lbl_hint = customtkinter.CTkLabel(main_frame, text="Узнать погоду, маршруты, вызвать помощь",
                                  font=FONT_SMALL, text_color="gray")
lbl_hint.grid(row=2, column=0, pady=5) # Будет под кнопкой

# ТЕКСТОВОЕ ПОЛЕ РЕЗУЛЬТАТА
result_textbox = customtkinter.CTkTextbox(
    main_frame,
    width=600,
    height=250,
    corner_radius=15,
    font=("Roboto", 22), # Крупный шрифт
    fg_color="#1A1A1A",
    text_color="#E0E0E0"
)
# ---------------------------------------------------------------


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
    API_KEY = "AIzaSyDhWK1tmXAz_daWljYfmee-8Q6RvDYwsRc"
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


def geobraceletgiving():
    global aianswer
    print("DEBUG: geobraceletgive вызвана")

    # Генерируем ключ для отображения
    bracelet_key = generate_bracelet_key()

    app.after(0, generate_gps_bracelet)

    # Форматируем ключ для произношения (по символам)
    key_spoken = " ".join(bracelet_key)

    aianswer = (
        f"✅ GPS БРАСЛЕТ ВЫДАН\n\n"
        f"Браслет успешно активирован.\n"
        f"Ключ доступа: {bracelet_key}\n\n"
        f"Пожалуйста, отсканируйте QR-код для получения информации.\n\n"
        f"Не забудьте вернуть браслет после завершения похода на любую Т.В.А станцию."
    )

    print(f"DEBUG: aianswer установлен = '{aianswer[:50]}...'")
    print(f"DEBUG: Сгенерированный ключ = '{bracelet_key}'")


def generate_bracelet_key():
    key = []
    for i in range(1, 9):
        if i in [2, 4, 5, 7]:
            key.append(random.choice(string.ascii_uppercase))
        else:
            key.append(str(random.randint(0, 9)))

    return ''.join(key)

def weather():
    global aianswer

    place = config.place
    country = config.country
    country_and_place = place + ", " + country

    try:
        owm = OWM('5439fa4e5062640c388b9802ffa444aa')
        mgr = owm.weather_manager()
        observation = mgr.weather_at_place(country_and_place)

        placen = "Баку" if place == 'Baku' else place

        w = observation.weather
        status_en = w.detailed_status  # Английское состояние
        humidity = w.humidity
        temp = w.temperature('celsius')['temp']
        wind_speed = w.wind()['speed']

        # ← ДОБАВЛЕНО: Словарь для перевода состояния погоды
        weather_translations = {
            'clear sky': 'ясное небо',
            'few clouds': 'малооблачно',
            'scattered clouds': 'переменная облачность',
            'broken clouds': 'облачно с прояснениями',
            'overcast clouds': 'пасмурно',
            'shower rain': 'ливневый дождь',
            'rain': 'дождь',
            'light rain': 'небольшой дождь',
            'moderate rain': 'умеренный дождь',
            'heavy intensity rain': 'сильный дождь',
            'thunderstorm': 'гроза',
            'snow': 'снег',
            'light snow': 'небольшой снег',
            'mist': 'туман',
            'fog': 'туман',
            'haze': 'дымка',
            'smoke': 'смог',
            'dust': 'пыль',
            'sand': 'песчаная буря',
            'tornado': 'торнадо',
            'squalls': 'шквал',
            'drizzle': 'морось',
            'light intensity drizzle': 'небольшая морось'
        }

        # Переводим состояние на русский
        status_ru = weather_translations.get(status_en.lower(), status_en)  # ← ДОБАВЛЕНО

        # Преобразуем числа в слова
        temp_words = num2words(round(temp), lang='ru')
        humidity_words = num2words(humidity, lang='ru')
        wind_words = num2words(round(wind_speed), lang='ru')

        # Текст для UI И озвучивания (весь текст словами)
        aianswer = (
            f"🌤️ ПОГОДА В ГОРОДЕ {placen.upper()}\n\n"
            f"Состояние: {status_ru}\n"  # ← ИЗМЕНЕНО: используем русский перевод
            f"Температура: {temp_words} градусов по цельсию\n"
            f"Влажность: {humidity_words} процентов\n"
            f"Скорость ветра: {wind_words} метров в секунду"
        )

        print(f"✓ ПОГОДА СОХРАНЕНА: {aianswer}")

    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        aianswer = "Не удалось получить данные о погоде. Проверьте подключение к интернету."

def va_respond(voice: str):
    global recorder, aianswer
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
            aianswer = gpt_result
            print(f"✓ СОХРАНЕНО в aianswer: {aianswer[:50]}...")
            # tts.va_speak(gpt_result)  # ← ЗАКОММЕНТИРОВАЛИ
            time.sleep(1)
            recorder.start()
            return True
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
                n = wiki.summary({voice}, sentences=4)
                aianswer = n
                # try:
                #     tts.va_speak(replace_numbers(n))
                # except:
                #     tts.va_speak(
                #         "Слишком много текста. Я не могу его произнести. Лучше прочитайте текст который я вам составил")
                print(n)
            except:
                # tts.va_speak("Извините не могу найти запрос на вашу тему")  # ← ЗАКОММЕНТИРОВАЛИ
                aianswer = "Извините не могу найти запрос на вашу тему"
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
    global aianswer

    if cmd == 'ctime':
        now = datetime.datetime.now()
        hour_words = num2words(now.hour, lang='ru')
        minute_words = num2words(now.minute, lang='ru')
        aianswer = f"🕐 ТЕКУЩЕЕ ВРЕМЯ\n\nСейчас {hour_words} часов {minute_words} минут"
        print(f"✓ ВРЕМЯ СОХРАНЕНО: {aianswer}")

    elif cmd == 'hello':
        play("hello")

    elif cmd == 'weather':
        weather()

    elif cmd == 'geobraceletgive':
        geobraceletgiving()

    elif cmd == 'stop':
        try:
            recorder.stop()
        except:
            pass
        aianswer = "⏸️ РЕЖИМ ОЖИДАНИЯ\n\nЯ перестал слушать.\nОбратитесь ко мне снова когда будете готовы."
        print("Переход в режим ожидания...")
        return

    elif cmd == 'restart':
        recorder.stop()
        os.system("python main.py")

    elif cmd == 'thanks':
        play("thanks", False)

    elif cmd == 'off':
        quite()


# `-1` is the default input audio device.

recorder = PvRecorder(device_index=config.MICROPHONE_INDEX, frame_length=porcupine.frame_length)
#recorder.start()
print('Using device: %s' % recorder.selected_device)

print(f"Компьютер начал свою работу ...")
time.sleep(0.5)

ltc = time.time() - 1000

# def cycle():
#     print("Yes, sir.")
#     play("greet1")
#     recorder.start()  # prevent self recording
#     ltc = time.time()
#     while time.time() - ltc <= 10:
#         pcm = recorder.read()
#         sp = struct.pack("h" * len(pcm), *pcm)
#
#         if kaldi_rec.AcceptWaveform(sp):
#             if va_respond(json.loads(kaldi_rec.Result())["text"]):
#                 ltc = time.time()

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
app.mainloop()
