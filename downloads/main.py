import sys
import os
import json
import time
import threading
import requests
import pyperclip
import tempfile
import ctypes
from ctypes import wintypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QCheckBox, QComboBox, QPushButton, 
                             QSystemTrayIcon, QMenu, QLineEdit, QFrame, QStackedWidget,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPalette

# myappid = 'com.claritykey.ai.python' (Moved to __main__ to avoid DPI conflict)

# Configuration
APP_VERSION = "v1.1"
SETTINGS_FILE = os.path.join(os.getenv('APPDATA'), 'ClarityKeyAI', 'settings.json')
SESSION_FILE = os.path.join(os.getenv('APPDATA'), 'ClarityKeyAI', 'session.json')
USAGE_FILE = os.path.join(os.getenv('APPDATA'), 'ClarityKeyAI', 'usage.json')
MODEL_ID = "qwen/qwen3.5-flash-02-23"

# Supabase Auth Configuration
SUPABASE_URL = "https://ehdwjvqwgkjfrquqwehj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVoZHdqdnF3Z2tqZnJxdXF3ZWhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2NDQ5MDMsImV4cCI6MjA4ODIyMDkwM30.qQ8J3yKBnqxz6XnjD7JkZSxFaBH87XTs5DLpa34yJvA"
class SupabaseAuth:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        self.auth = self # Compatibility with supabase-py syntax

    def sign_in_with_password(self, credentials):
        res = requests.post(f"{self.url}/auth/v1/token?grant_type=password", 
                            json=credentials, headers=self.headers)
        return self._handle_response(res)

    def set_session(self, access_token, refresh_token):
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"
        res = requests.get(f"{self.url}/auth/v1/user", headers=headers)
        return self._handle_response(res, True, (access_token, refresh_token))

    def _handle_response(self, res, is_session=False, tokens=None):
        data = res.json()
        if res.status_code >= 400:
            return type('Res', (), {'session': None, 'user': None, 'error': data.get('error_description', data.get('message', 'Auth error'))})
        user_data = data.get('user', data)
        user = type('User', (), {'email': user_data.get('email'), 'id': user_data.get('id')})
        if is_session and tokens:
            session = type('Session', (), {'access_token': tokens[0], 'refresh_token': tokens[1], 'user': user})
        else:
            session = type('Session', (), {'access_token': data.get('access_token'), 'refresh_token': data.get('refresh_token'), 'user': user})
        return type('Res', (), {'session': session, 'user': user, 'error': None})

    def sign_out(self): pass

# Initialize Supabase Auth Client
supabase = None
if SUPABASE_URL != "https://your-project.supabase.co":
    supabase = SupabaseAuth(SUPABASE_URL, SUPABASE_KEY)

MODE_PROMPTS = {
    'English': {
        'Spelling Fix Only': "You are an AI dyslexia corrector. Understand the copied text, and correct ONLY the spelling if needed. Do not change grammar or sentence structure. Return ONLY the corrected text.",
        'Grammar + Spelling': "You are an AI dyslexia corrector. Understand the copied text and correct only the spelling and grammar if needed. Maintain the original tone. Return ONLY the corrected text.",
        'Simplified Version': "You are an AI dyslexia corrector. Understand the copied text and rewrite it in simpler, clearer language. Return ONLY the simplified text.",
        'Professional Rewrite': "You are an AI dyslexia corrector. Understand the copied text and rewrite it to make it sound professional and clear. Return ONLY the rewritten text."
    },
    'Danish': {
        'Spelling Fix Only': "Du er en AI-ordblinde-korrektør. Forstå den kopierede tekst, og ret KUN stavningen, hvis det er nødvendigt. Ændr ikke grammatik eller sætningsstruktur. Returnér KUN den rettede tekst.",
        'Grammar + Spelling': "Du er en AI-ordblinde-korrektør. Forstå den kopierede tekst, og ret kun stavning og grammatik, hvis det er nødvendigt. Bevar den originale tone. Returnér KUN den rettede tekst.",
        'Simplified Version': "Du er en AI-ordblinde-korrektør. Forstå den kopierede tekst, og omskriv den til et simplere og klarere sprog. Returnér KUN den forenklede tekst.",
        'Professional Rewrite': "Du er en AI-ordblinde-korrektør. Forstå den kopierede tekst, og omskriv den så den lyder professionel og klar. Returnér KUN den omskrevne tekst."
    },
    'Spanish': {
        'Spelling Fix Only': "Eres un corrector de dislexia con IA. Entiende el texto copiado y corrige SOLO la ortografía si es necesario. No cambies la gramática ni la estructura de las frases. Devuelve SOLO el texto corregido.",
        'Grammar + Spelling': "Eres un corrector de dislexia con IA. Entiende el texto copiado y corrige solo la ortografía y la gramática si es necesario. Mantén el tono original. Devuelve SOLO el texto corregido.",
        'Simplified Version': "Eres un corrector de dislexia con IA. Entiende el texto copiado y reescríbelo en un lenguaje más sencillo y claro. Devuelve SOLO el texto simplificado.",
        'Professional Rewrite': "Eres un corrector de dislexia con IA. Entiende el texto copiado y reescríbelo para que suene profesional y claro. Devuelve SOLO el texto reescrito."
    },
    'German': {
        'Spelling Fix Only': "Du bist ein KI-Legasthenie-Korrektor. Verstehe den kopierten Text und korrigiere NUR die Rechtschreibung, wenn nötig. Ändere weder Grammatik noch Satzbau. Gib NUR den korrigierten Text zurück.",
        'Grammar + Spelling': "Du bist ein KI-Legasthenie-Korrektor. Verstehe den kopierten Text und korrigiere nur Rechtschreibung und Grammatik, wenn nötig. Bewahre den Originalton. Gib NUR den korrigierten Text zurück.",
        'Simplified Version': "Du bist ein KI-Legasthenie-Korrektor. Verstehe den kopierten Text und schreibe ihn in einfacherer, klarerer Sprache um. Gib NUR den vereinfachten Text zurück.",
        'Professional Rewrite': "Du bist ein KI-Legasthenie-Korrektor. Verstehe den kopierten Text und schreibe ihn um, damit er professionell und klar klingt. Gib NUR den umgeschriebenen Text zurück."
    },
    'French': {
        'Spelling Fix Only': "Vous êtes un correcteur de dyslexie IA. Comprenez le texte copié et corrigez UNIQUEMENT l'orthographe si nécessaire. Ne modifiez pas la grammaire ni la structure des phrases. Renvoyez UNIQUEMENT le texte corrigé.",
        'Grammar + Spelling': "Vous êtes un correcteur de dyslexie IA. Comprenez le texte copié et corrigez uniquement l'orthographe et la grammaire si nécessaire. Conservez le ton d'origine. Renvoyez UNIQUEMENT le texte corrigé.",
        'Simplified Version': "Vous êtes un correcteur de dyslexie IA. Comprenez le texte copié et réécrivez-le dans un langage plus simple et clair. Renvoyez UNIQUEMENT le texte simplifié.",
        'Professional Rewrite': "Vous êtes un correcteur de dyslexie IA. Comprenez le texte copié et réécrivez-le pour qu'il soit professionnel et clair. Renvoyez UNIQUEMENT le texte réécrit."
    }
}

DEFAULT_SETTINGS = {
    'isEnabled': True,
    'dyslexiaFont': False,
    'autoLaunch': True,
    'showNotifications': True,
    'instantReplace': True,
    'readAloudHotkey': True,
    'easyReading': False,
    'currentMode': 'Grammar + Spelling',
    'language': 'English',
    'playNotifySound': True
}

def ensure_sound_file():
    filepath = os.path.join(os.getenv('APPDATA'), 'ClarityKeyAI', 'notify.wav')
    if not os.path.exists(filepath):
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            import wave, struct, math
            with wave.open(filepath, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(44100)
                for i in range(44100 // 4): # quarter second
                    factor = min(1.0, i / 2000.0)  # Soft fade-in
                    value = int(math.sin(i / 15.0) * 8000 * factor)
                    f.writeframesraw(struct.pack('<h', value))
        except Exception as e: 
            print(f"Error creating sound: {e}")
    return filepath

class Communicator(QObject):
    settings_changed = pyqtSignal()
    hotkey_pressed = pyqtSignal()
    uses_updated = pyqtSignal()
    device_conflict = pyqtSignal()

class ClarityKeyApp:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()
        self.notify_sound = ensure_sound_file()
        if 'device_id' not in self.settings:
            import uuid
            self.settings['device_id'] = str(uuid.uuid4())
            self.save_settings()
            
        self.last_text = ""
        self.is_processing = False
        self.communicator = Communicator()
        self.communicator.device_conflict.connect(self.handle_device_conflict)
        
        # Load Icon
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_path, "icon.png")

        self.settings_window = None
        self.login_window = None
        self.user_session = None
        self.subscription_status = 'free'
        self.daily_uses_remaining = 5
        self.tray_icon = None
        
        # Set Global Application Icon
        if os.path.exists(self.icon_path):
            QApplication.instance().setWindowIcon(QIcon(self.icon_path))

        # Attempt to load persistent session
        self.load_session()

        # Start Clipboard Watcher Thread
        self.watcher_thread = threading.Thread(target=self.clipboard_watcher, daemon=True)
        
        # Start Global Hotkey Thread for TTS
        self.hotkey_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        self.communicator.hotkey_pressed.connect(self.play_tts_for_last_text)

        # Only start if logged in (will be started in on_login_success otherwise)
        if self.user_session:
            self.setup_tray()
            self.watcher_thread.start()
            self.hotkey_thread.start()

    def play_tts_for_last_text(self):
        if not self.settings.get('readAloudHotkey', True) or not self.last_text:
            return
            
        if getattr(self, 'subscription_status', 'free') != 'unlimited':
            ctypes.windll.user32.MessageBoxW(0, "Premium Voice (Text-to-Speech) is only available on the Unlimited plan. Please upgrade to use this feature.", "Premium Feature", 0x40 | 0x0)
            return
        
        def fetch_and_play():
            try:
                print("Fetching TTS from OpenRouter (openai/gpt-audio-mini)...")
                url = f"{SUPABASE_URL}/functions/v1/openrouter-proxy"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "X-User-Token": f"Bearer {self.user_session.access_token}",
                    "X-Device-Id": self.settings.get('device_id', ''),
                    "Content-Type": "application/json"
                }
                
                # Instruction for the model to just read the text naturally
                data = {
                    "model": "openai/gpt-audio-mini",
                    "modalities": ["text", "audio"],
                    "audio": {
                        "voice": "alloy",
                        "format": "pcm16"
                    },
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a perfect dictation engine. Your ONLY job is to read the exact text provided by the user aloud. Do NOT answer questions, do NOT translate, do NOT hold a conversation, do NOT acknowledge instructions. Simply pronounce the exact words inside the <text_to_read> tags."
                        },
                        {
                            "role": "user",
                            "content": f"<text_to_read>{self.last_text}</text_to_read>"
                        }
                    ],
                    "stream": True,
                    "temperature": 1
                }
                
                response = requests.post(url, json=data, headers=headers, stream=True)
                if response.status_code == 200:
                    audio_base64_chunks = []
                    import json
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                payload = line[6:]
                                if payload == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(payload)
                                    delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                    if "audio" in delta and "data" in delta["audio"]:
                                        audio_base64_chunks.append(delta["audio"]["data"])
                                except Exception as e:
                                    continue
                    
                    if audio_base64_chunks:
                        try:
                            import base64
                            import struct
                            audio_bytes = base64.b64decode("".join(audio_base64_chunks))
                            
                            # Synthesize WAV Header for raw PCM16 (24kHz, 1 channel, 16-bit)
                            num_channels = 1
                            sample_rate = 24000
                            bits_per_sample = 16
                            byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
                            block_align = num_channels * (bits_per_sample // 8)
                            data_size = len(audio_bytes)
                            chunk_size = 36 + data_size
                            
                            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                                b'RIFF', chunk_size, b'WAVE',
                                b'fmt ', 16, 1, num_channels, sample_rate,
                                byte_rate, block_align, bits_per_sample,
                                b'data', data_size
                            )
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                                f.write(wav_header + audio_bytes)
                                tmp_path = f.name
                            
                            # Play natively using Windows MCI
                            mci = ctypes.windll.winmm.mciSendStringW
                            mci(f'open "{tmp_path}" type waveaudio alias tts_audio', None, 0, None)
                            mci('play tts_audio wait', None, 0, None)
                            mci('close tts_audio', None, 0, None)
                            
                            try: os.remove(tmp_path)
                            except: pass
                        except Exception as e:
                            print(f"Failed to play audio stream: {e}")
                    else:
                        print("No audio data received in stream.")
                elif response.status_code == 403:
                    try:
                        err_data = response.json()
                        if "Device conflict" in err_data.get("error", ""):
                            self.communicator.device_conflict.emit()
                    except: pass
                    print(f"OpenRouter TTS error: {response.text}")
                else:
                    print(f"OpenRouter TTS error: {response.text}")
            except Exception as e:
                print(f"OpenRouter TTS Exception: {e}")
                
        threading.Thread(target=fetch_and_play, daemon=True).start()

    def hotkey_listener(self):
        user32 = ctypes.windll.user32
        # ID 1: Insert key (0x2D is VK_INSERT, 0x0000 is no modifier)
        ins_registered = user32.RegisterHotKey(None, 1, 0x0000 | 0x4000, 0x2D)
        if not ins_registered:
            print("Warning: Failed to register global hotkey Insert. Trying fallback...")

        # ID 2: Backup Hotkey Ctrl+Shift+P (0x50 is 'P', 0x0002 is MOD_CONTROL, 0x0004 is MOD_SHIFT)
        backup_registered = user32.RegisterHotKey(None, 2, 0x0002 | 0x0004 | 0x4000, 0x50)
        
        if not ins_registered and not backup_registered:
            print("Warning: Failed to register fallback hotkey Ctrl+Shift+P. No hotkey will be active for TTS.")
            return

        print(f"Hotkeys registered: Insert: {ins_registered}, Ctrl+Shift+P: {backup_registered}")
        
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam in [1, 2]:
                    self.communicator.hotkey_pressed.emit()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save_settings(self):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_session(self):
        if os.path.exists(SESSION_FILE) and supabase:
            try:
                with open(SESSION_FILE, 'r') as f:
                    session_data = json.load(f)
                    # Use refresh_token if session expired? Supabase Client handles this usually
                    # For now, just set it and verify
                    res = supabase.auth.set_session(session_data['access_token'], session_data['refresh_token'])
                    if res.user:
                        self.user_session = res.session
                        self.fetch_profile_status()  # Synchronous on startup
                    else:
                        print(f"Session token invalid or expired.")
                        self.user_session = None
            except Exception as e:
                print(f"Session load error: {e}")
                self.user_session = None

    def save_session(self, session):
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        try:
            with open(SESSION_FILE, 'w') as f:
                json.dump({
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token
                }, f)
        except Exception as e:
            print(f"Error saving session: {e}")

    def logout(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        if supabase:
            supabase.auth.sign_out()
        self.user_session = None
        self.subscription_status = 'free'
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
        self.show_login()

    def handle_device_conflict(self):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "Your account is being used on another device. You have been logged out.", "Device Conflict", 0x30 | 0x0)
        self.logout()

    def fetch_profile_status(self):
        """Fetches and caches the user's subscription status and remaining uses."""
        if not self.user_session: return
        try:
            import datetime
            # Use the user's own JWT token so RLS allows reading their profile
            user_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {self.user_session.access_token}",
                "Content-Type": "application/json"
            }
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{self.user_session.user.id}&select=subscription_status,daily_usage_count,last_usage_date",
                headers=user_headers
            )
            if res.status_code == 200:
                data = res.json()
                if data:
                    profile = data[0]
                    # Claim active device async
                    def _claim_device():
                        try:
                            requests.patch(
                                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{self.user_session.user.id}",
                                headers=user_headers,
                                json={"active_device_id": self.settings.get('device_id')}
                            )
                        except: pass
                    threading.Thread(target=_claim_device, daemon=True).start()
                    
                    self.subscription_status = profile.get('subscription_status', 'free')
                    if self.subscription_status != 'unlimited':
                        today = datetime.date.today().isoformat()
                        count = profile.get('daily_usage_count', 0)
                        last_date = profile.get('last_usage_date')
                        if last_date != today:
                            count = 0
                            
                        # Reconcile highest usage between cloud and local
                        local_count = self.load_daily_usage()
                        actual_count = max(count, local_count)
                        self.save_daily_usage(actual_count)
                        
                        self.daily_uses_remaining = max(0, 5 - actual_count)
                    else:
                        self.daily_uses_remaining = -1  # Unlimited sentinel
                else:
                    # No profile row yet
                    self.subscription_status = 'free'
                    self.daily_uses_remaining = 5
                
                # Ensure the GUI accurately captures this update
                if hasattr(self, 'communicator'):
                    self.communicator.uses_updated.emit()
                    
            print(f"Profile loaded: {self.subscription_status}, uses remaining: {self.daily_uses_remaining}")
        except Exception as e:
            print(f"Error fetching profile: {e}")

    def clipboard_watcher(self):
        while True:
            if self.settings['isEnabled']:
                try:
                    current_text = pyperclip.paste()
                    if current_text and current_text != self.last_text and not self.is_processing:
                        self.process_text(current_text)
                except Exception as e:
                    print(f"Clipboard error: {e}")
            time.sleep(0.5)

    def load_daily_usage(self):
        """Load local usage count. Resets if it's a new day."""
        import datetime
        today = datetime.date.today().isoformat()
        if os.path.exists(USAGE_FILE):
            try:
                with open(USAGE_FILE, 'r') as f:
                    data = json.load(f)
                if data.get('date') == today:
                    return data.get('count', 0)
            except Exception:
                pass
        return 0

    def save_daily_usage(self, count):
        """Save local usage count for today."""
        import datetime
        today = datetime.date.today().isoformat()
        os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
        try:
            with open(USAGE_FILE, 'w') as f:
                json.dump({'date': today, 'count': count}, f)
        except Exception as e:
            print(f"Error saving usage: {e}")

    def check_usage_limit(self):
        """Checks and updates the user's daily usage limit."""
        if not self.user_session:
            return False

        # Fast path: unlimited users are never blocked
        if self.subscription_status == 'unlimited':
            return True

        # Use local file as source of truth (fast, always works)
        current_count = self.load_daily_usage()

        if current_count >= 5:
            if self.daily_uses_remaining != 0:
                self.daily_uses_remaining = 0
                self.communicator.uses_updated.emit()
            print("Daily limit reached (local).")
            return False

        # Consume a use locally first (instant update)
        new_count = current_count + 1
        self.save_daily_usage(new_count)
        self.daily_uses_remaining = max(0, 5 - new_count)
        print(f"Uses remaining today: {self.daily_uses_remaining}")
        
        # Emit signal to update settings window if open
        self.communicator.uses_updated.emit()

        # Sync to Supabase in background (non-blocking)
        def sync_to_supabase():
            try:
                import datetime
                today = datetime.date.today().isoformat()
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{self.user_session.user.id}",
                    headers={**supabase.headers, "Prefer": "return=minimal"},
                    json={"daily_usage_count": new_count, "last_usage_date": today},
                    timeout=5
                )
            except Exception as e:
                print(f"Supabase sync error (non-fatal): {e}")

        threading.Thread(target=sync_to_supabase, daemon=True).start()
        return True

    def process_text(self, text):
        if not self.user_session:
            print("Login required to process text.")
            return

        if not text.strip(): return
        self.is_processing = True

        if not self.check_usage_limit():
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "You have reached your free daily limit of 5 uses. Please upgrade to Unlimited to continue.", "Daily Limit Reached", 0x30 | 0x0)
            self.is_processing = False
            return

        print(f"Processing in mode: {self.settings['currentMode']}")
        
        try:
            current_lang = self.settings.get('language', 'English')
            prompts_for_lang = MODE_PROMPTS.get(current_lang, MODE_PROMPTS['English'])
            # Fallback to English prompt if the current Mode is missing in a specific language map
            prompt_txt = prompts_for_lang.get(self.settings['currentMode'], MODE_PROMPTS['English'].get(self.settings['currentMode'], ""))

            response = requests.post(
                f"{SUPABASE_URL}/functions/v1/openrouter-proxy",
                headers={
                    "apikey": SUPABASE_KEY,
                    "X-User-Token": f"Bearer {self.user_session.access_token}",
                    "X-Device-Id": self.settings.get('device_id', ''),
                    "HTTP-Referer": "https://claritykey.ai",
                    "X-OpenRouter-Title": "ClarityKey AI",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL_ID,
                    "messages": [
                        {"role": "user", "content": f"Target Language: {current_lang}.\n{prompt_txt}\n\nText: {text}"}
                    ]
                },
                timeout=15
            )
            
            data = response.json()
            if 'choices' in data and data['choices']:
                corrected = data['choices'][0]['message']['content'].strip()
                
                # Strip out any markdown bolding/highlighting asterisks returned by the AI
                corrected = corrected.replace("**", "").replace("__", "")
                
                self.last_text = corrected
                pyperclip.copy(corrected)
                print("Text corrected and copied to clipboard.")

                if self.settings.get('playNotifySound', True):
                    try: ctypes.windll.winmm.PlaySoundW(self.notify_sound, None, 0x00020001)
                    except: pass
                
                if self.settings['instantReplace']:
                    # Simulate Ctrl+V on Windows
                    if sys.platform == 'win32':
                        import pyautogui
                        pyautogui.hotkey('ctrl', 'v')
                        
            else:
                if response.status_code == 403:
                    try:
                        err_data = response.json()
                        if "Device conflict" in err_data.get("error", ""):
                            self.communicator.device_conflict.emit()
                    except: pass
                print(f"API Error: {data}")
                self.last_text = text
                
        except Exception as e:
            print(f"Processing error: {e}")
            self.last_text = text
        finally:
            self.is_processing = False

    def show_login(self):
        if not self.login_window:
            self.login_window = LoginWindow(self)
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()

    def on_login_success(self, session):
        self.user_session = session
        self.save_session(session)
        self.fetch_profile_status()  # Synchronous before tray is set up
        if self.login_window:
            self.login_window.close()
        self.setup_tray()
        # Start Watcher only after login
        if not self.watcher_thread.is_alive():
            self.watcher_thread.start()
        if not self.hotkey_thread.is_alive():
            self.hotkey_thread.start()

    def toggle_enabled(self):
        self.settings['isEnabled'] = not self.settings['isEnabled']
        self.save_settings()
        self.update_tray()

    def set_mode(self, mode_name):
        self.settings['currentMode'] = mode_name
        self.save_settings()
        self.update_tray()

    def show_settings(self):
        # Refresh subscription status from Supabase every time the window opens
        self.fetch_profile_status()
        # Always recreate to show fresh subscription status
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def setup_tray(self):
        if self.tray_icon: return # Avoid duplicate tray icons
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon_path), QApplication.instance())
        self.tray_icon.setToolTip(f"ClarityKey AI {APP_VERSION}")
        
        # Connect single click to show settings
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        self.update_tray()
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        # Comparison works directly on the enum member; avoid int() call
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_settings()

    def update_tray(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.setContextMenu(self.create_menu())

    def create_menu(self):
        menu = QMenu()
        
        # User Info
        email = self.user_session.user.email if self.user_session else "Not Logged In"
        if getattr(self, 'subscription_status', 'free') == 'unlimited':
            email += " ✨ (Unlimited)"
        user_action = QAction(f"User: {email}", menu)
        user_action.setEnabled(False)
        menu.addAction(user_action)
        menu.addSeparator()

        # Title action (non-clickable)
        title_action = QAction(f"ClarityKey AI {APP_VERSION}", menu)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        
        status_text = "🟢 Active" if self.settings['isEnabled'] else "🔴 Paused"
        status_action = QAction(status_text, menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        
        menu.addSeparator()
        
        toggle_text = "Disable" if self.settings['isEnabled'] else "Enable"
        toggle_action = QAction(toggle_text, menu)
        toggle_action.triggered.connect(self.toggle_enabled)
        menu.addAction(toggle_action)
        
        menu.addSeparator()
        
        # Mode Actions
        for mode in MODE_PROMPTS['English'].keys():
            action = QAction(f"Mode: {mode}", menu)
            action.setCheckable(True)
            action.setChecked(self.settings['currentMode'] == mode)
            # Use functools.partial or a lambda to handle external state
            action.triggered.connect(lambda checked, m=mode: self.set_mode(m))
            menu.addAction(action)
            
        menu.addSeparator()
        
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        logout_action = QAction("Log Out", menu)
        logout_action.triggered.connect(self.logout)
        menu.addAction(logout_action)
        
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        return menu

class SettingsWindow(QMainWindow):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("ClarityKey AI - Settings")
        self.setFixedSize(850, 600)
        
        if os.path.exists(self.main_app.icon_path):
            self.setWindowIcon(QIcon(self.main_app.icon_path))

        # Main Layout Structure (Sidebar + Content)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Global Application Stylesheet (SaaS / Claymorphism)
        self.setStyleSheet("""
            QMainWindow { background-color: #f1f5f9; }
            QLabel { font-family: 'Segoe UI', system-ui, sans-serif; }
            QComboBox {
                padding: 10px 15px; border-radius: 8px; border: 1px solid #cbd5e1;
                background-color: white; font-size: 14px; color: #1e293b;
            }
            QComboBox::drop-down { border: none; }
            QComboBox:focus { border: 2px solid #3b82f6; }
            QPushButton.primary {
                background-color: #3b82f6; color: white; padding: 10px 20px;
                border-radius: 8px; font-weight: bold; font-size: 14px; border: none;
            }
            QPushButton.primary:hover { background-color: #2563eb; }
            QPushButton.secondary {
                background-color: white; color: #3b82f6; padding: 10px 20px;
                border-radius: 8px; font-weight: bold; font-size: 14px; border: 1px solid #cbd5e1;
            }
            QPushButton.secondary:hover { background-color: #f8fafc; border: 1px solid #94a3b8; }
            
            QCheckBox {
                spacing: 15px; color: #334155; font-size: 14px; font-weight: 500;
            }
            QCheckBox::indicator {
                width: 40px; height: 20px; border-radius: 10px; 
                border: 1px solid #cbd5e1; background: #e2e8f0;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6; border: 1px solid #2563eb;
            }
        """)

        # Sidebar Panel
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background-color: white; border-right: 1px solid #e2e8f0;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Brand / Logo
        brand_container = QWidget()
        brand_layout = QVBoxLayout(brand_container)
        brand_layout.setContentsMargins(30, 35, 30, 25)
        brand_label = QLabel("ClarityKey AI")
        brand_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #0f172a; border: none;")
        brand_layout.addWidget(brand_label)
        sidebar_layout.addWidget(brand_container)

        # Navigation Pages
        self.nav_buttons = []
        self.pages = QStackedWidget()

        self.add_nav_item("⚙️ General", self.create_general_page(), sidebar_layout)
        self.add_nav_item("🧠 AI Engine", self.create_ai_page(), sidebar_layout)
        self.add_nav_item("👤 Account", self.create_account_page(), sidebar_layout)
        
        sidebar_layout.addStretch()

        # Sidebar Footer
        footer_container = QWidget()
        footer_layout = QVBoxLayout(footer_container)
        footer_layout.setContentsMargins(20, 20, 20, 30)
        close_btn = QPushButton("Close window")
        close_btn.setProperty("class", "secondary")
        close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)
        sidebar_layout.addWidget(footer_container)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.pages)
        
        self.select_page(0)

    def add_nav_item(self, text, page_widget, sidebar_layout):
        idx = self.pages.addWidget(page_widget)
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding: 12px 30px; font-size: 15px; font-weight: 600;
                color: #64748b; background: transparent; border: none;
            }
            QPushButton:hover { background-color: #f8fafc; color: #1e293b; }
            QPushButton:checked {
                background-color: #eff6ff; color: #3b82f6; border-right: 4px solid #3b82f6;
            }
        """)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, i=idx: self.select_page(i))
        self.nav_buttons.append(btn)
        sidebar_layout.addWidget(btn)

    def select_page(self, index):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.pages.setCurrentIndex(index)

    def create_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white; border-radius: 16px; border: 1px solid #e2e8f0;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        return card

    def create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("General Settings")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title)
        
        card = self.create_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(25)

        self.enabled_cb = QCheckBox("Enable ClarityKey AI globally")
        self.enabled_cb.setChecked(self.main_app.settings['isEnabled'])
        self.enabled_cb.stateChanged.connect(self.update_setting('isEnabled'))
        card_layout.addWidget(self.enabled_cb)

        self.replace_cb = QCheckBox("Instant Replace (Auto Ctrl+V)")
        self.replace_cb.setChecked(self.main_app.settings['instantReplace'])
        self.replace_cb.stateChanged.connect(self.update_setting('instantReplace'))
        card_layout.addWidget(self.replace_cb)

        self.sound_cb = QCheckBox("Play Sound on Success (Recommended)")
        self.sound_cb.setChecked(self.main_app.settings.get('playNotifySound', True))
        self.sound_cb.stateChanged.connect(self.update_setting('playNotifySound'))
        card_layout.addWidget(self.sound_cb)

        self.read_cb = QCheckBox("Read Text Aloud on Insert Key")
        self.read_cb.setChecked(self.main_app.settings.get('readAloudHotkey', True))
        self.read_cb.stateChanged.connect(self.update_setting('readAloudHotkey'))
        card_layout.addWidget(self.read_cb)

        self.font_cb = QCheckBox("Format output with Dyslexia Friendly Font")
        self.font_cb.setChecked(self.main_app.settings['dyslexiaFont'])
        self.font_cb.stateChanged.connect(self.update_setting('dyslexiaFont'))
        card_layout.addWidget(self.font_cb)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("AI Engine")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title)
        
        card = self.create_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        lbl = QLabel("Preferred Correction Mode")
        lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #1e293b; border: none;")
        card_layout.addWidget(lbl)

        desc = QLabel("Select how the AI should rewrite your text when you copy it.")
        desc.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 10px; border: none;")
        card_layout.addWidget(desc)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(list(MODE_PROMPTS['English'].keys()))
        self.mode_combo.setCurrentText(self.main_app.settings['currentMode'])
        self.mode_combo.currentTextChanged.connect(self.update_setting('currentMode'))
        card_layout.addWidget(self.mode_combo)

        lbl_lang = QLabel("Output Language")
        lbl_lang.setStyleSheet("font-size: 16px; font-weight: 600; color: #1e293b; border: none; margin-top: 15px;")
        card_layout.addWidget(lbl_lang)

        desc_lang = QLabel("Select the language for the AI output.")
        desc_lang.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 10px; border: none;")
        card_layout.addWidget(desc_lang)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Danish", "Spanish", "German", "French"])
        self.lang_combo.setCurrentText(self.main_app.settings.get('language', 'English'))
        self.lang_combo.currentTextChanged.connect(self.update_setting('language'))
        card_layout.addWidget(self.lang_combo)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_account_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("Account & Billing")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title)
        
        card = self.create_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)

        self.user_email_label = QLabel()
        self.user_email_label.setStyleSheet("border: none; background: transparent;")
        self.update_usage_label()
        self.user_email_label.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(self.user_email_label)
        
        self.main_app.communicator.uses_updated.connect(self.update_usage_label)

        manage_btn = QPushButton("Manage Subscription")
        manage_btn.setProperty("class", "secondary")
        import webbrowser
        manage_btn.clicked.connect(lambda: webbrowser.open("https://claritykey.org/subscription.html"))
        card_layout.addWidget(manage_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def update_usage_label(self):
        email = self.main_app.user_session.user.email if self.main_app.user_session else "Guest"
        status = getattr(self.main_app, 'subscription_status', 'free')
        remaining = getattr(self.main_app, 'daily_uses_remaining', 5)
        
        html = f"<div style='margin-bottom: 20px;'><span style='color: #64748b; font-size: 14px;'>Signed in as</span><br><span style='color: #0f172a; font-size: 18px; font-weight: 700;'>{email}</span></div>"
        
        if status == 'unlimited':
            badge = "<span style='background-color: #f3e8ff; color: #7c3aed; padding: 6px 12px; border-radius: 12px; font-size: 13px; font-weight: 700;'>✨ Unlimited Plan</span>"
            html += f"<div>{badge}</div><div style='color: #64748b; font-size: 14px; margin-top: 15px;'>You have unrestricted access to all features including Premium Voice.</div>"
        else:
            if remaining > 0:
                badge = f"<span style='background-color: #f1f5f9; color: #334155; padding: 6px 12px; border-radius: 12px; font-size: 13px; font-weight: 700;'>Free Plan</span>"
                html += f"<div>{badge}</div><div style='color: #475569; font-size: 15px; margin-top: 15px;'><b>{remaining}</b> uses left today.</div>"
            else:
                badge = "<span style='background-color: #fee2e2; color: #ef4444; padding: 6px 12px; border-radius: 12px; font-size: 13px; font-weight: 700;'>⚠️ Daily Limit Reached</span>"
                html += f"<div>{badge}</div><div style='color: #ef4444; margin-top: 15px;'>Upgrade for unlimited uses and premium features.</div>"
        
        self.user_email_label.setText(html)

    def show(self):
        super().show()
        if not self.main_app.user_session and supabase:
            self.close()
            self.main_app.show_login()

    def update_setting(self, key):
        def inner(value):
            if isinstance(value, int):
                value = bool(value)
            self.main_app.settings[key] = value
            self.main_app.save_settings()
            self.main_app.update_tray()
        return inner

class LoginWindow(QMainWindow):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("ClarityKey AI - Log In")
        self.setFixedSize(450, 500)
        
        if os.path.exists(self.main_app.icon_path):
            self.setWindowIcon(QIcon(self.main_app.icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.setStyleSheet("""
            QMainWindow { background-color: #f1f5f9; }
            QLabel { font-family: 'Segoe UI', system-ui, sans-serif; }
            QLineEdit {
                padding: 10px; border-radius: 10px; border: 1px solid #cbd5e1;
                background-color: #f8fafc; font-size: 15px; color: #1e293b;
                min-height: 25px;
            }
            QLineEdit:focus { border: 2px solid #3b82f6; background-color: white; }
            QPushButton.primary {
                background-color: #3b82f6; color: white; padding: 12px;
                border-radius: 10px; font-weight: bold; font-size: 16px; border: none;
                min-height: 20px;
            }
            QPushButton.primary:hover { background-color: #2563eb; }
            QPushButton.primary:disabled { background-color: #94a3b8; }
            .error { color: #ef4444; font-size: 13px; font-weight: 500; }
        """)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 50, 40, 50)
        main_layout.setSpacing(20)

        # Card Container
        card = QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; border: 1px solid #e2e8f0; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(35, 40, 35, 40)
        layout.setSpacing(15)

        title = QLabel("Welcome back")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0f172a; border: none;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sign in to your ClarityKey account")
        subtitle.setStyleSheet("color: #64748b; font-size: 14px; border: none; margin-bottom: 10px;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        layout.addWidget(self.email_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)

        self.error_label = QLabel("")
        self.error_label.setProperty("class", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.error_label)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setProperty("class", "primary")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        import webbrowser
        help_btn = QPushButton("Don't have an account? Sign up")
        help_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #64748b; font-size: 13px; font-weight: 600; padding: 5px; border: none; }
            QPushButton:hover { color: #3b82f6; text-decoration: underline; }
        """)
        help_btn.clicked.connect(lambda: webbrowser.open("https://claritykey.org/auth.html"))
        layout.addWidget(help_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def handle_login(self):
        email = self.email_input.text().strip()
        pw = self.pass_input.text().strip()

        if not email or not pw:
            self.error_label.setText("Please enter both email and password.")
            return

        if supabase is None:
            self.error_label.setText(f"Supabase not initialized.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")
        self.error_label.setText("")

        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
            if res.error:
                self.error_label.setText(f"Login failed: {res.error}")
            elif res.session:
                self.main_app.on_login_success(res.session)
            else:
                self.error_label.setText("Login failed: No session returned")
        except Exception as e:
            self.error_label.setText(f"Login error: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")

if __name__ == "__main__":
    # Needed for instant replace simulation
    try:
        import pyautogui
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        import pyautogui

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)
    
    # Set AppID for Windows Taskbar Branding after Qt initialization to avoid DPI issues
    try:
        myappid = 'com.claritykey.ai.python'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Taskbar AppID set failed: {e}")
    
    clarity_key = ClarityKeyApp()
    
    # Start with Login or go straight to Tray if already signed in
    if not clarity_key.user_session:
        if supabase:
            clarity_key.show_login()
        else:
            # Fallback if no supabase configured, show settings for dev
            clarity_key.setup_tray()
            clarity_key.show_settings()
            if not clarity_key.watcher_thread.is_alive():
                clarity_key.watcher_thread.start()
    else:
        print(f"Already logged in as {clarity_key.user_session.user.email}")
    
    sys.exit(qt_app.exec())
