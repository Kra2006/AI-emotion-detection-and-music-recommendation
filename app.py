import tkinter as tk
from tkinter import messagebox
import os
import random
import re
from pathlib import Path
from tkinter import filedialog
from music_player import MusicPlayer

from emotion_model import predict_emotion


# ============================================================
# EMOTION → MUSIC MOOD
# ============================================================

EMOTION_LABELS = ("anger", "fear", "joy", "love", "sadness", "surprise")

# The classifier returns these six labels. Keep their music categories aligned
# with the emotion-named folders that are present in this project's music tree.
MUSIC_MOOD = {emotion: emotion for emotion in EMOTION_LABELS}


# ============================================================
# MUSIC FOLDERS
# ============================================================

MUSIC_FOLDERS = {
    "anger": "music/anger",
    "fear": "music/fear",
    "joy": "music/joy",
    "love": "music/love",
    "sadness": "music/sadness",
    "surprise": "music/surprise",
    "neutral": "music/neutral"
}


# ============================================================
# GLOBAL VARIABLES
# ============================================================

current_song = None
player = None

# Most recent meaningful emotion
last_meaningful_emotion = None

# Prevent asking music question multiple times
conversation_ending_asked = False
last_special_music_query = None


def special_music_query(text):
    """Return a targeted music search for a recognized special occasion."""
    if re.search(r"\b(birthday|bday)\b", text, flags=re.IGNORECASE):
        return "birthday songs celebration"
    return None


def active_music_folder():
    # Store birthday picks with joyful music; no occasion folder exists yet.
    mood = "joy" if last_special_music_query else MUSIC_MOOD.get(last_meaningful_emotion or "", "neutral")
    return MUSIC_FOLDERS.get(mood, MUSIC_FOLDERS["neutral"])


# ============================================================
# CHECK WHETHER CONVERSATION IS ENDING
# ============================================================

def is_conversation_ending(text):

    text = text.lower().strip()

    end_phrases = [
        "bye",
        "goodbye",
        "good bye",
        "see you",
        "see ya",
        "talk later",
        "catch you later",
        "i have to go",
        "i gotta go",
        "gotta go",
        "that's all",
        "that is all",
        "nothing else",
        "no more",
        "end conversation",
        "end the conversation",
        "finish conversation",
        "conversation is over",
        "i am done",
        "i'm done",
        "im done",
        "done",
        "thank you",
        "thanks",
        "i feel better",
        "i'm feeling better",
        "im feeling better"
    ]

    for phrase in end_phrases:

        if phrase in text:
            return True

    return False


# ============================================================
# GET SONG
# ============================================================

def get_song(emotion):
    """Choose a track for the predicted emotion, then fall back to any library track."""
    emotion = str(emotion).strip().lower()
    music_mood = MUSIC_MOOD.get(emotion, "neutral")
    supported_formats = (
        ".mp3",
        ".wav",
        ".m4a",
        ".ogg",
        ".flac"
    )

    def songs_in(folder):
        if not os.path.isdir(folder):
            return []
        return [
            str(Path(folder, name).resolve())
            for name in os.listdir(folder)
            if name.lower().endswith(supported_formats)
            and Path(folder, name).is_file()
        ]

    # Prefer tracks classified for the detected emotion.
    matched = songs_in(MUSIC_FOLDERS.get(music_mood, MUSIC_FOLDERS["neutral"]))
    if matched:
        return random.choice(matched)

    # If that category is empty, use any track already in the music library.
    library = []
    for folder in MUSIC_FOLDERS.values():
        library.extend(songs_in(folder))
    return random.choice(library) if library else None


# ============================================================
# PLAY SONG
# ============================================================

def play_song(song):
    global current_song
    if not song:
        return
    current_song = song
    try:
        player.play(song)
        return True
    except Exception as e:
        messagebox.showerror("Music Error", f"Unable to play the song.\n\n{e}")
        return False


def stop_music():
    global current_song
    if player:
        player.stop()
    current_song = None


def pause_music():
    try:
        player.pause()
    except Exception as e:
        messagebox.showerror("Playback", str(e))


def resume_music():
    try:
        player.resume()
    except Exception as e:
        messagebox.showerror("Playback", str(e))


def toggle_music_pause():
    try:
        player.toggle_pause()
    except Exception as e:
        messagebox.showerror("Playback", str(e))


def choose_local_song():
    song = filedialog.askopenfilename(title="Choose a local song", filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.m4a *.flac"), ("All files", "*.*")])
    if song:
        play_song(song)


def recommend_online_song():
    """Try online first: cache the preview locally, then play it in the app."""
    emotion = last_meaningful_emotion or "neutral"
    mood = "joy" if last_special_music_query else MUSIC_MOOD.get(emotion, "neutral")
    folder = active_music_folder()
    song_label.config(text="Searching and loading music...")

    def play_online(path, title):
        def on_ui_thread():
            if play_song(path):
                song_label.config(text=f"Playing online download: {title}")
            else:
                play_local_fallback("Could not play the downloaded online song.")
        root.after(0, on_ui_thread)

    def online_failed(error):
        root.after(0, lambda: play_local_fallback(f"Online music unavailable: {error}"))

    def play_local_fallback(reason):
        local_song = get_song("joy" if last_special_music_query else emotion)
        if local_song:
            if play_song(local_song):
                song_label.config(text=f"Online unavailable; playing local: {os.path.basename(local_song)}")
            else:
                messagebox.showerror("Music Error", f"{reason}\n\nLocal playback failed for {local_song}.")
        else:
            song_label.config(text="No online or local music available")
            messagebox.showerror("Music Error", f"{reason}\n\nAdd a track under {folder} for offline fallback.")

    MusicPlayer.online_search(mood, folder, play_online, online_failed, search_term=last_special_music_query)

def download_youtube_song():
    url = youtube_url_entry.get().strip()
    if not url:
        messagebox.showinfo("YouTube download", "Paste a YouTube video URL first.")
        return
    if not url.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
        messagebox.showerror("YouTube download", "Enter a valid YouTube URL.")
        return
    folder = active_music_folder()
    song_label.config(text="Downloading audio...")
    download_button.config(state=tk.DISABLED)
    def done(title):
        root.after(0, lambda: (download_button.config(state=tk.NORMAL), song_label.config(text=f"Downloaded to {folder}: {title}")))
    def failed(error):
        root.after(0, lambda: (download_button.config(state=tk.NORMAL), song_label.config(text="Download failed"), messagebox.showerror("Download failed", error)))
    MusicPlayer.download_youtube(url, folder, done, failed)


# ============================================================
# ASK USER WHETHER TO PLAY MUSIC
# ============================================================

def ask_to_play_music():

    global conversation_ending_asked

    if last_meaningful_emotion is None:

        messagebox.showwarning(
            "No Emotion Detected",
            "I need to understand your mood first."
        )

        return

    # Prevent repeated popup
    if conversation_ending_asked:
        return

    conversation_ending_asked = True

    answer = messagebox.askyesno(
        "Mood Music",
        "I understand how you're feeling.\n\n"
        "Would you like me to play a song that suits your mood?"
    )

    if answer:

        recommend_online_song()

    else:

        song_label.config(
            text="🎵 Music not played"
        )


# ============================================================
# GENERATE AI RESPONSE
# ============================================================

def generate_response(emotion):

    responses = {

        "joy":
            "That's great to hear! 😊 What made you feel so happy?",

        "love":
            "It sounds like something meaningful is making you feel good. ❤️ Tell me more about it.",

        "sadness":
            "I'm sorry you're feeling this way. 😔 If you want, you can tell me what happened.",

        "anger":
            "It sounds like something is frustrating you. 😟 What happened?",

        "fear":
            "I understand that you're feeling worried. 💙 What is making you feel this way?",

        "surprise":
            "That sounds unexpected! 😮 What happened?",

    }

    return responses.get(
        emotion,
        "I understand. Tell me more about how you're feeling."
    )


# ============================================================
# ANALYZE USER MESSAGE
# ============================================================

def analyze_message():

    global last_meaningful_emotion
    global last_special_music_query

    text = message_entry.get().strip()

    # Don't process empty messages
    if not text:
        return

    last_special_music_query = special_music_query(text)

    # Show user message
    chat_box.config(state=tk.NORMAL)

    chat_box.insert(
        tk.END,
        f"You: {text}\n\n"
    )

    chat_box.config(state=tk.DISABLED)

    # Clear input
    message_entry.delete(0, tk.END)

    try:

        # Predict emotion
        emotion, confidence = predict_emotion(text)

        emotion = str(emotion)
        confidence = float(confidence)

        # Update emotion display
        emotion_label.config(
            text=f"Detected Emotion: {emotion.capitalize()}"
        )

        confidence_label.config(
            text=f"Confidence: {confidence:.2f}%"
        )

        # Check whether user is ending conversation
        conversation_ending = is_conversation_ending(text)

        # ----------------------------------------------------
        # IMPORTANT:
        # Don't replace the meaningful emotion with "bye",
        # "thanks", etc.
        # ----------------------------------------------------

        if not conversation_ending:

            last_meaningful_emotion = emotion

        # Generate AI response
        response = generate_response(emotion)

        chat_box.config(state=tk.NORMAL)

        chat_box.insert(
            tk.END,
            f"AI: {response}\n\n"
        )

        chat_box.config(state=tk.DISABLED)

        # Automatically scroll chat to bottom
        chat_box.see(tk.END)

        # ----------------------------------------------------
        # IF CONVERSATION IS ENDING
        # ASK WHETHER USER WANTS MUSIC
        # ----------------------------------------------------

        if conversation_ending:

            # Wait 500 milliseconds so the AI response
            # appears before the popup
            root.after(
                500,
                ask_to_play_music
            )

        elif last_special_music_query:
            # Occasion messages such as "It's my birthday" play targeted music.
            root.after(500, recommend_online_song)

    except Exception as e:

        messagebox.showerror(
            "Prediction Error",
            f"Something went wrong:\n\n{e}"
        )


# ============================================================
# ENTER KEY
# ============================================================

def enter_pressed(event):

    analyze_message()


# ============================================================
# CLEAR CHAT
# ============================================================

def clear_chat():

    global last_meaningful_emotion
    global conversation_ending_asked
    global current_song
    global last_special_music_query

    chat_box.config(state=tk.NORMAL)

    chat_box.delete(
        "1.0",
        tk.END
    )

    chat_box.config(state=tk.DISABLED)

    emotion_label.config(
        text="Detected Emotion: None"
    )

    confidence_label.config(
        text="Confidence: 0%"
    )

    song_label.config(
        text="🎵 No song playing"
    )

    if player:
        player.stop()
    last_meaningful_emotion = None
    last_special_music_query = None
    conversation_ending_asked = False
    current_song = None


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()

root.title(
    "🤖 AI Emotion Conversation & Mood Music Player"
)

root.geometry(
    "850x760"
)

root.resizable(
    False,
    False
)


# ============================================================
# TITLE
# ============================================================

title_label = tk.Label(
    root,
    text="🤖 AI Emotion Conversation",
    font=("Arial", 24, "bold")
)

title_label.pack(
    pady=(15, 5)
)


subtitle_label = tk.Label(
    root,
    text="Talk with the AI and let it understand your mood",
    font=("Arial", 12)
)

subtitle_label.pack(
    pady=(0, 10)
)


# ============================================================
# CHAT BOX
# ============================================================

chat_box = tk.Text(
    root,
    width=90,
    height=18,
    font=("Arial", 11),
    wrap=tk.WORD
)

chat_box.pack(
    padx=20,
    pady=10
)

chat_box.config(
    state=tk.DISABLED
)


# ============================================================
# MESSAGE INPUT FRAME
# ============================================================

input_frame = tk.Frame(root)

input_frame.pack(
    pady=5
)


message_entry = tk.Entry(
    input_frame,
    width=65,
    font=("Arial", 12)
)

message_entry.grid(
    row=0,
    column=0,
    padx=5
)


send_button = tk.Button(
    input_frame,
    text="Send",
    font=("Arial", 11, "bold"),
    width=10,
    command=analyze_message
)

send_button.grid(
    row=0,
    column=1,
    padx=5
)


# ============================================================
# EMOTION INFORMATION
# ============================================================

emotion_label = tk.Label(
    root,
    text="Detected Emotion: None",
    font=("Arial", 13, "bold")
)

emotion_label.pack(
    pady=(10, 2)
)


confidence_label = tk.Label(
    root,
    text="Confidence: 0%",
    font=("Arial", 11)
)

confidence_label.pack(
    pady=2
)


# ============================================================
# MUSIC STATUS
# ============================================================

song_label = tk.Label(
    root,
    text="🎵 No song playing",
    font=("Arial", 11)
)

song_label.pack(
    pady=5
)


# Compact music controls
player = MusicPlayer(lambda text: song_label.config(text=text))

music_panel = tk.LabelFrame(root, text="Music", padx=10, pady=7)
music_panel.pack(fill=tk.X, padx=20, pady=5)

music_controls = tk.Frame(music_panel)
music_controls.pack()
tk.Button(music_controls, text="Play Mood Music", command=recommend_online_song, width=16).grid(row=0, column=0, padx=4, pady=3)
tk.Button(music_controls, text="Choose Local File", command=choose_local_song, width=16).grid(row=0, column=1, padx=4, pady=3)
tk.Button(music_controls, text="Pause / Resume", command=toggle_music_pause, width=16).grid(row=0, column=2, padx=4, pady=3)
tk.Button(music_controls, text="Stop", command=stop_music, width=10).grid(row=0, column=3, padx=4, pady=3)

download_row = tk.Frame(music_panel)
download_row.pack(fill=tk.X, pady=(4, 0))
youtube_url_entry = tk.Entry(download_row)
youtube_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
download_button = tk.Button(download_row, text="Download YouTube audio", command=download_youtube_song)
download_button.pack(side=tk.RIGHT)

chat_actions = tk.Frame(root)
chat_actions.pack(pady=(2, 8))
tk.Button(chat_actions, text="Clear Chat", command=clear_chat, width=14).pack()


# ============================================================
# ENTER KEY SUPPORT
# ============================================================

message_entry.bind(
    "<Return>",
    enter_pressed
)


# ============================================================
# START APPLICATION
# ============================================================

message_entry.focus()

root.mainloop()
