import streamlit as st
from transformers import MarianMTModel, MarianTokenizer, AutoTokenizer, AutoModelForSeq2SeqLM
import sqlite3
from datetime import datetime
import speech_recognition as sr
import numpy as np
import sounddevice as sd
import scipy.io.wavfile
import tempfile
import os
import re
from gtts import gTTS
import base64

st.set_page_config(page_title="Translatify Chatbot", layout="centered")

def set_background(image_file):
    with open(image_file, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background("bg.jpg") 

st.image("logo.png", width=50)

st.title("𓀃 Translatify - A Multilingual Translator")
page = st.sidebar.radio("Navigate", ["Translate", "History"])

# Database setup
conn = sqlite3.connect('translation_history.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_text TEXT,
        translated_text TEXT,
        target_language TEXT,
        timestamp TEXT
    )
''')
conn.commit()

@st.cache_resource
def load_model_and_tokenizer(lang):
    if lang.lower() == "german":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-de")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-de")
    elif lang.lower() == "tamil":
        tokenizer = AutoTokenizer.from_pretrained("suriya7/English-to-Tamil")
        model = AutoModelForSeq2SeqLM.from_pretrained("suriya7/English-to-Tamil")
    elif lang.lower() == "french":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-fr")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-fr")
    elif lang.lower() == "hindi":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-hi")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-hi")
    elif lang.lower() == "spanish":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-es")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-es")
    elif lang.lower() == "malayalam":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ml")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-ml")
    else:
        return None, None
    return tokenizer, model

def extract_translation_request(sentence):
    languages = ["german", "tamil", "french", "hindi", "spanish", "malayalam"]
    sentence = sentence.lower()
    target_lang = next((lang for lang in languages if lang in sentence), None)
    if not target_lang:
        return None, None
    phrase = re.sub(r"(what\s+is\s+the\s+meaning\s+of|translate|what\s+is\s+mean\s+by)\s*", "", sentence)
    phrase = re.sub(r"\s+in\s+" + target_lang, "", phrase).strip()
    return phrase, target_lang.capitalize()

# gTTS language code mapping
gtts_lang_codes = {
    "German": "de",
    "Tamil": "ta",
    "French": "fr",
    "Hindi": "hi",
    "Spanish": "es",
    "Malayalam": "ml"
}

if page == "Translate":
    st.subheader("💬 Ask your translation question")

    input_method = st.radio("Choose input method:", ["Type your translation question:", "Speak your translation question:"])
    query = ""

    if input_method == "Type your translation question:":
        query = st.text_input("Ask your translation question:", placeholder="e.g., What is the meaning of Hello in Tamil")

    else:
        st.info("🎙️ Click 'Start Recording', then speak. Click 'Stop Recording' once done.")
        duration = st.slider("Recording duration (seconds):", 2, 10, 5)

        if st.button("🎤 Start Recording"):
            fs = 16000
            st.info("Recording...")
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            st.success("✅ Recording complete!")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                scipy.io.wavfile.write(f.name, fs, recording)
                audio_path = f.name

            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)

            try:
                query = recognizer.recognize_google(audio)
                st.success("You said:")
                st.write(f"🗣️ {query}")
            except Exception as e:
                st.error(f"Speech recognition error: {e}")
            finally:
                os.unlink(audio_path)

    if query:
        phrase, lang = extract_translation_request(query)
        if phrase and lang:
            tokenizer, model = load_model_and_tokenizer(lang)
            if tokenizer is None or model is None:
                st.error("❌ Could not load model for that language.")
            else:
                inputs = tokenizer(phrase, return_tensors="pt", padding=True)
                outputs = model.generate(**inputs)
                translated = tokenizer.decode(outputs[0], skip_special_tokens=True)

                st.success(f"✅ Translation in {lang}:")
                st.write(f"💬 {translated}")

                gtts_code = gtts_lang_codes.get(lang)
                if gtts_code:
                    try:
                        tts = gTTS(text=translated, lang=gtts_code)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                            tts.save(audio_file.name)
                            st.audio(audio_file.name, format="audio/mp3")
                    except Exception as e:
                        st.warning(f"🔇 Could not convert to audio: {e}")
                else:
                    st.warning(f"🔇 Audio not supported for language: {lang}")

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    INSERT INTO history (input_text, translated_text, target_language, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (phrase, translated, lang, timestamp))
                conn.commit()
        else:
            st.warning("⚠️ Try asking like: What is the meaning of Hello in Tamil")

elif page == "History":
    st.subheader("📜 Translation History")
    cursor.execute('SELECT input_text, translated_text, target_language, timestamp FROM history ORDER BY id DESC')
    records = cursor.fetchall()
    if records:
        for input_text, translated_text, lang, time in records:
            st.markdown(f"**🕒 {time} | 🌐 {lang}**")
            st.markdown(f"- **Input:** {input_text}")
            st.markdown(f"- **Translation:** {translated_text}")
            st.markdown("---")
    else:
        st.info("No translation history yet.")