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

# Page setup
st.set_page_config(page_title="Translatify", layout="centered")
st.title("🌍 Translatify - Multilingual Translator")

page = st.sidebar.radio("Navigation", ["Translator", "History"])

# Initialize session state
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# DB setup
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

# Load models based on language
@st.cache_resource
def load_model_and_tokenizer(lang):
    if lang == "German":
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-de")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-de")
    elif lang == "Tamil":
        tokenizer = AutoTokenizer.from_pretrained("suriya7/English-to-Tamil")
        model = AutoModelForSeq2SeqLM.from_pretrained("suriya7/English-to-Tamil")
    else:  # Hinglish
        tokenizer = AutoTokenizer.from_pretrained("Hinglish/Bhashini-Hinglish-translation")
        model = AutoModelForSeq2SeqLM.from_pretrained("Hinglish/Bhashini-Hinglish-translation")
    return tokenizer, model

if page == "Translator":
    st.subheader("Translate English to German, Tamil or Hinglish")
    language_option = st.selectbox("Choose Target Language", ["German", "Tamil", "Hinglish"])

    tokenizer, model = load_model_and_tokenizer(language_option)

    input_method = st.radio("Choose input method:", ["Type Text", "Speak"])

    if input_method == "Type Text":
        st.session_state.input_text = st.text_area("Enter English text:", height=150)

    else:
        st.info("🎙️ Click 'Start Recording', then speak. Click 'Stop Recording' once done.")

        duration = st.slider("Recording duration (seconds):", 2, 10, 5)

        if st.button("🎤 Start Recording"):
            fs = 16000  # Sample rate
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
                text = recognizer.recognize_google(audio)
                st.session_state.input_text = text
                st.success("You said:")
                st.write(f"🗣️ {text}")
            except Exception as e:
                st.error(f"Speech recognition error: {e}")
            finally:
                os.unlink(audio_path)

    if st.button("Translate"):
        if st.session_state.input_text.strip():
            inputs = tokenizer(st.session_state.input_text, return_tensors="pt", padding=True)
            translated_tokens = model.generate(**inputs)
            translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

            st.success(f"✅ Translation to {language_option}:")
            st.write(translated_text)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO history (input_text, translated_text, target_language, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (st.session_state.input_text, translated_text, language_option, timestamp))
            conn.commit()
        else:
            st.warning("⚠️ Please enter or say something first.")

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