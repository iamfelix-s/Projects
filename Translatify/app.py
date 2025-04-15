import streamlit as st
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile
import tempfile
import os
import re
import base64
from datetime import datetime
from gtts import gTTS
import mysql.connector
from deep_translator import GoogleTranslator

st.set_page_config(
    page_title="Translatify - Multilingual Translator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded")

@st.cache_resource 
def set_background(image_file):
    with open(image_file, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()
    st.markdown(
        f"""<style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>""",
        unsafe_allow_html=True,
    )
set_background("bg.jpg")

st.sidebar.image("logo_redefined.png", width=150)
st.title("𓀃 Translatify - A Multilingual Translator")
st.sidebar.title("📚 Navigation Menu")

nav_translate = st.sidebar.button("Translate")
nav_history = st.sidebar.button("History")
nav_about = st.sidebar.button("About")

if nav_translate:
    st.session_state.page = "Translate"
elif nav_history:
    st.session_state.page = "History"
elif nav_about:
    st.session_state.page = "About"
if "page" not in st.session_state:
    st.session_state.page = "Translate"

# 🌐 MySQL DB
conn = mysql.connector.connect(
    host="localhost", user="root", password="Felix@71", database="translatify_db"
)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        input_text TEXT,
        translated_text TEXT,
        target_language VARCHAR(100),
        timestamp DATETIME
    )
''')
conn.commit()

def extract_translation_request(sentence):
    translator = GoogleTranslator(source='auto', target='en') 
    supported_langs = translator.get_supported_languages(as_list=True)

    sentence = sentence.lower()
    found_lang = next((lang for lang in supported_langs if lang.lower() in sentence), None)

    if not found_lang:
        return None, None

    phrase = re.sub(r"(what\s+is\s+the\s+meaning\s+of|translate|what\s+is\s+mean\s+by)\s*", "", sentence)
    phrase = re.sub(r"\s+in\s+" + found_lang.lower(), "", phrase).strip()

    return phrase, found_lang

# 🔊 Language Codes for gTTS
gtts_lang_codes = {
    "afrikaans": "af", "albanian": "sq", "arabic": "ar", "armenian": "hy",
    "azerbaijani": "az", "basque": "eu", "belarusian": "be", "bengali": "bn",
    "bosnian": "bs", "bulgarian": "bg", "catalan": "ca", "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW", "croatian": "hr", "czech": "cs", "danish": "da",
    "dutch": "nl", "english": "en", "esperanto": "eo", "estonian": "et", "filipino": "tl",
    "finnish": "fi", "french": "fr", "galician": "gl", "georgian": "ka", "german": "de",
    "greek": "el", "gujarati": "gu", "haitian creole": "ht", "hebrew": "iw", "hindi": "hi",
    "hungarian": "hu", "icelandic": "is", "indonesian": "id", "irish": "ga", "italian": "it",
    "japanese": "ja", "javanese": "jw", "kannada": "kn", "kazakh": "kk", "khmer": "km",
    "korean": "ko", "kurdish (kurmanji)": "ku", "lao": "lo", "latin": "la", "latvian": "lv",
    "lithuanian": "lt", "macedonian": "mk", "malay": "ms", "malayalam": "ml", "maltese": "mt",
    "marathi": "mr", "mongolian": "mn", "nepali": "ne", "norwegian": "no", "persian": "fa",
    "polish": "pl", "portuguese": "pt", "punjabi": "pa", "romanian": "ro", "russian": "ru",
    "serbian": "sr", "sinhala": "si", "slovak": "sk", "slovenian": "sl", "spanish": "es",
    "sundanese": "su", "swahili": "sw", "swedish": "sv", "tamil": "ta", "telugu": "te",
    "thai": "th", "turkish": "tr", "ukrainian": "uk", "urdu": "ur", "uzbek": "uz",
    "vietnamese": "vi", "welsh": "cy", "xhosa": "xh", "yiddish": "yi", "yoruba": "yo",
    "zulu": "zu"
}

def translate_page():
    st.subheader("💬 Translate from any to any language")

    # Dropdown for target language (GTTS-compatible)
    all_langs = GoogleTranslator().get_supported_languages(as_dict=True)
    lang_names = list(all_langs.keys())
    selected_lang = st.selectbox("Select Target Language", lang_names)
    target_code = all_langs[selected_lang]

    input_method = st.radio("Choose input method:", ["Type your translation", "Speak your translation"])
    query = ""

    if input_method == "Type your translation":
        query = st.text_input("Enter your sentence to translate", placeholder="e.g., Hello, what's the plan for today?")

    else:
        st.info("🎙️ Click to record and speak")
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
        try:
            translated = GoogleTranslator(source='auto', target=target_code).translate(query)
            st.success(f"✅ Translated to {selected_lang}:")
            st.write(f"💬 {translated}")

            if target_code in gtts_lang_codes.values():
                tts = gTTS(text=translated, lang=target_code)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                    tts.save(audio_file.name)
                    st.audio(audio_file.name, format="audio/mp3")
            else:
                st.warning("🔇 Audio not supported for this language.")

            # Save to DB
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO history (input_text, translated_text, target_language, timestamp)
                VALUES (%s, %s, %s, %s)
            ''', (query, translated, selected_lang, timestamp))
            conn.commit()

        except Exception as e:
            st.error(f"❌ Error translating: {e}")

def history_page():
    st.subheader("📜 Translation History")
    search_query = st.text_input("🔍 Search History", placeholder="Search your past translations...")

    cursor.execute('SELECT input_text, translated_text, target_language, timestamp FROM history ORDER BY id DESC')
    records = cursor.fetchall()
    
    st.markdown("""
        <style>
        .history-box {
            backdrop-filter: blur(10px);
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease-in-out;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
        }
        .history-box:hover {
            transform: scale(1.02);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        </style>
    """, unsafe_allow_html=True)

    if records:
        for input_text, translated_text, lang, time in records:
            if search_query.lower() in input_text.lower() or search_query.lower() in translated_text.lower():
                st.markdown(f"""
                    <div class="history-box">
                        <p><b>Input:</b> {input_text}</p>
                        <p><b>Translation:</b> {translated_text}</p>
                        <p><b>Language:</b> {lang}</p>
                        <p><b>Time:</b> {time}</p>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No translation history available.")

    if st.button("🧹 Clear All History"):
        cursor.execute("DELETE FROM history")
        conn.commit()
        st.success("History cleared.")


def about_page():

    st.subheader("📖 About Translatify")
    st.markdown("""
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    """, unsafe_allow_html=True)

    # Glassmorphism
    st.markdown("""
        <style>
            * {
                font-family: 'Roboto'
            }
            .glass-box {
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                background: rgba(255, 255, 255, 0.07);
                border-radius: 16px;
                padding: 40px;
                max-width: 1100px;
                margin: auto;
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: white;
            }
            .glass-box ul {
                line-height: 1.8em;
                font-size: 16px;
            }
            .glass-box li {
                margin-bottom: 8px;
            }
            .greyout {
                color: #808080;
                font-style: italic;
            }
            .developer-container {
                background-color: rgba(255, 255, 255, 0.1); /* Light transparent background */
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="glass-box">
            <h2>𓀃 Welcome to Translatify</h2>
            <p><strong>Translatify</strong> is an intuitive multilingual chatbot that enables seamless conversations across languages. Designed with both elegance and utility in mind, it merges speech, text, and intelligent translation into one beautifully interactive platform.</p>
            <hr>
            <h3>✨ Key Features</h3>
            <ul>
                <li><strong>Any-to-Any Language Translation:</strong> Translate between any two languages — not just English-based. It auto-detects your input language via <em>GoogleTranslator</em>.</li>
                <li><strong>Speech-to-Text + Text-to-Speech (TTS):</strong> Speak naturally, get a real-time translation, and hear it played back using <em>Google Speech Recognition</em> and <em>gTTS</em>.</li>
                <li><strong>Real-Time History Logging:</strong> Every interaction is logged in a <em>MySQL</em> database. Search or delete your past translations easily.</li>
                <li><strong>Modern Glass UI:</strong> Beautifully minimal design with smooth blur effects, hover interactions, and a clear layout.</li>
            </ul>
            <hr>
            <h3>🚀 Why Translatify Stands Out</h3>
            <p>Unlike standard tools that only translate to/from English or lack voice support, <strong>Translatify</strong> is engineered for flexibility and clarity. Whether you're a traveler, student, or business professional, our smart integration of speech + text input, any-to-any language pairing, and real-time UX gives you a world-class translation experience.</p>
            <hr>
            <h3>⚙️ Technologies Used</h3>
            <ul>
                <li><strong>GoogleTranslator API:</strong> Robust real-time translation between 100+ languages</li>
                <li><strong>Google Speech Recognition:</strong> Converts voice input to text with accuracy</li>
                <li><strong>gTTS:</strong> Generates clear, natural audio from translated text</li>
                <li><strong>MySQL:</strong> Handles translation history with secure and efficient storage</li>
                <li><strong>Streamlit:</strong> Provides a reactive and modern frontend framework</li>
            </ul>
            <hr>
            <h3>🔮 Upcoming Features</h3>
            <ul>
                <li>Support for regional accents and custom voices</li>
                <li>Auto-suggested target languages based on context</li>
                <li>Offline mode for selected language combinations</li>
            </ul>
            <hr>
            <div class="developer-container">
                <h3>👥 Meet the Developers</h3>
                <ul>
                    <li><strong>Felix</strong> – <em>Lead Developer, UX & Backend Integration</em><br>
                        <a href='https://github.com/iamfelix-s/VCodez'>GitHub <i class="fab fa-github"></i></a> |
                        <a href='https://www.instagram.com/iamfelix.s'>Instagram <i class="fab fa-instagram"></i></a>
                    </li>
                    <li><strong>Azar</strong> – <em>Speech Processing & Audio Integration</em><br>
                        <a href='https://www.instagram.com/call_me_chaco'>Instagram <i class="fab fa-instagram"></i></a>
                    </li>
                    <li><strong>Moses</strong> – <em>Database & Cloud Deployment</em><br>
                        <a href='https://www.instagram.com/Moses'>Instagram <i class="fab fa-instagram"></i></a>
                    </li>
                </ul>
            </div>
            <hr>
            <h3>💡 Get Involved</h3>
            <ul>
                <li>Follow our journey on GitHub and social media</li>
                <li>Submit feedback, feature requests, or bugs</li>
                <li>Contribute translations, code, or ideas</li>
            </ul>
            <p class='greyout'>Translatify – created to break language barriers with clarity, speed, and style.</p>
        </div>
    """, unsafe_allow_html=True)

if st.session_state.page == "Translate":
    translate_page()
elif st.session_state.page == "History":
    history_page()
elif st.session_state.page == "About":
    about_page()