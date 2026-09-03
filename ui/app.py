import streamlit as st
import requests
import uuid
import io
import os
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# ---------------- Config ----------------
load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")


# ---------------- Session state ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_title" not in st.session_state:
    st.session_state.chat_title = "New Chat"
if "chats" not in st.session_state:
    st.session_state.chats = []
if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False


# ---------------- API helpers ----------------
def api_request(method, endpoint, **kwargs):
    kwargs.setdefault("timeout", 60)
    return requests.request(method, f"{API_BASE}/api{endpoint}", **kwargs)


def get_json(response):
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def show_api_error(response):
    data = get_json(response)
    error = data.get("detail") or response.text or "Unknown server error."
    st.error(f"Error {response.status_code}: {error}")


# ---------------- Chat history ----------------
def load_chat_list():
    try:
        response = api_request("GET", "/history")
        if response.status_code != 200:
            return
        data = get_json(response)
        st.session_state.chats = data.get("chats", [])
        st.session_state.history_loaded = True
    except requests.exceptions.RequestException:
        pass


def create_new_chat():
    try:
        response = api_request("POST", "/history/create")
        if response.status_code != 200:
            show_api_error(response)
            return
        data = get_json(response)
        st.session_state.session_id = data.get("session_id", str(uuid.uuid4()))
        st.session_state.chat_title = data.get("title", "New Chat")
        st.session_state.messages = []
        load_chat_list()
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Cannot create new chat: {str(e)}")


def load_chat(session_id):
    try:
        response = api_request("GET", f"/history/{session_id}")
        if response.status_code != 200:
            show_api_error(response)
            return False
        data = get_json(response)
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"]}
            for m in data.get("messages", [])
        ]
        st.session_state.session_id = session_id
        st.session_state.chat_title = data.get("title", "New Chat")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Cannot load chat: {str(e)}")
        return False


def rename_chat(session_id, new_title):
    new_title = new_title.strip()
    if not new_title:
        st.warning("Please enter a chat name.")
        return
    try:
        response = api_request("PATCH", f"/history/{session_id}/rename", data={"title": new_title})
        if response.status_code != 200:
            show_api_error(response)
            return
        st.session_state.chat_title = new_title
        load_chat_list()
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Rename failed: {str(e)}")


def delete_chat(session_id):
    try:
        response = api_request("DELETE", f"/history/{session_id}")
        if response.status_code not in (200, 204):
            show_api_error(response)
            return
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_title = "New Chat"
        load_chat_list()
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Delete failed: {str(e)}")


def clear_current_chat():
    try:
        response = api_request("POST", "/clear", data={"session_id": st.session_state.session_id})
        if response.status_code != 200:
            show_api_error(response)
            return
        st.session_state.messages = []
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Clear chat failed: {str(e)}")


# ---------------- Load history on first run ----------------
if not st.session_state.history_loaded:
    load_chat_list()


# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("💬 Chat")

    if st.button("➕ New Chat", width='stretch'):
        create_new_chat()

    st.divider()
    st.subheader("📚 Chat History")

    if st.session_state.chats:
        for chat in st.session_state.chats:
            sid = chat["session_id"]
            title = chat["title"]
            label = f"🟢 {title}" if sid == st.session_state.session_id else f"💬 {title}"
            if st.button(label, key=f"open_{sid}", width='stretch'):
                if load_chat(sid):
                    st.rerun()
    else:
        st.caption("No saved conversations yet.")

    st.divider()
    st.subheader("✏️ Conversation")

    rename_title = st.text_input("Chat name", value=st.session_state.chat_title, key="rename_input")
    if st.button("✏️ Rename Chat", width='stretch'):
        rename_chat(st.session_state.session_id, rename_title)

    if st.button("🧹 Clear Current Chat", width='stretch'):
        clear_current_chat()

    if st.button("🗑️ Delete Conversation", width='stretch'):
        delete_chat(st.session_state.session_id)

    st.divider()
    st.header("Upload Options")
    uploaded_image = st.file_uploader(
        "Attach an image to your query",
        type=["png", "jpg", "jpeg", "webp"]
    )
    if uploaded_image:
        st.image(uploaded_image, caption="Preview", width='stretch')

        if st.button("📄 Convert to PDF"):
            files = {"file": (uploaded_image.name, uploaded_image.getvalue(), uploaded_image.type)}
            pdf_response = requests.post(f"{API_BASE}/api/convert-to-pdf", files=files)
            if pdf_response.status_code == 200:
                st.download_button(
                    "Download PDF",
                    data=pdf_response.content,
                    file_name="converted.pdf",
                    mime="application/pdf",
                )
            else:
                st.error(f"Conversion failed: {pdf_response.status_code}")

    st.divider()
    st.header("🔄 File Converter")
    st.caption("Upload up to 10 files, then describe what you want in plain English.")

    convert_files_input = st.file_uploader(
        "Files to convert",
        type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "docx", "csv", "xlsx"],
        accept_multiple_files=True,
        key="convert_uploader",
    )
    convert_command = st.text_input(
        "What do you want to do?",
        placeholder="e.g. Convert these images into one PDF",
        key="convert_command",
    )

    if st.button("▶️ Run Conversion", width='stretch'):
        if not convert_files_input:
            st.warning("Please upload at least one file.")
        elif not convert_command.strip():
            st.warning("Please describe what you want to do.")
        else:
            multipart_files = [
                ("files", (f.name, f.getvalue(), f.type or "application/octet-stream"))
                for f in convert_files_input
            ]
            try:
                conv_response = requests.post(
                    f"{API_BASE}/api/files/convert",
                    data={"command": convert_command},
                    files=multipart_files,
                    timeout=120,
                )
                if conv_response.status_code == 200:
                    content_type = conv_response.headers.get("content-type", "application/octet-stream")
                    ext_map = {
                        "application/pdf": "pdf",
                        "application/zip": "zip",
                        "text/plain": "txt",
                        "text/csv": "csv",
                        "image/jpeg": "jpg",
                        "image/png": "png",
                    }
                    out_ext = ext_map.get(content_type, "bin")
                    st.success("Conversion complete!")
                    st.download_button(
                        "⬇️ Download result",
                        data=conv_response.content,
                        file_name=f"converted_output.{out_ext}",
                        mime=content_type,
                    )
                else:
                    try:
                        detail = conv_response.json().get("detail", conv_response.text)
                    except Exception:
                        detail = conv_response.text
                    st.error(f"Conversion failed ({conv_response.status_code}): {detail}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {str(e)}")


st.title(f"🤖 {st.session_state.chat_title}")
st.caption(f"Conversation ID: {st.session_state.session_id}")


# ---------------- Render chat history ----------------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            # Voice -> Voice: auto-plays without needing a click, since the
            # question itself was asked by voice.
            if "audio_bytes" in msg:
                st.audio(msg["audio_bytes"], format="audio/mp3", autoplay=True)
            elif st.button("🔊 Play", key=f"play_{i}"):
                tts = gTTS(msg["content"])
                buf = io.BytesIO()
                tts.write_to_fp(buf)
                st.audio(buf.getvalue(), format="audio/mp3")


# ---------------- Input: text or voice ----------------
col1, col2 = st.columns([0.92, 0.08])
with col1:
    prompt = st.chat_input("Ask a question...")
with col2:
    audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="recorder", just_once=True)

used_voice_input = False

if audio and not prompt:
    try:
        transcript = groq_client.audio.transcriptions.create(
            file=("audio.wav", audio["bytes"]),
            model="whisper-large-v3"
        )
        prompt = transcript.text
        used_voice_input = True
    except Exception as e:
        st.error(f"Transcription failed: {e}")


# ---------------- Send message ----------------
if prompt:
    img_bytes = uploaded_image.getvalue() if uploaded_image else None

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        files = {}
        if uploaded_image and img_bytes:
            files = {"file": (uploaded_image.name, img_bytes, uploaded_image.type)}

        response = requests.post(
            f"{API_BASE}/api/chat",
            data={"message": prompt, "session_id": st.session_state.session_id},
            files=files if files else None
        )

        if response.status_code == 200:
            bot_reply = response.json().get("reply", "No response content.")
        else:
            bot_reply = f"Error {response.status_code}: {response.text}"

    except Exception as e:
        bot_reply = f"Failed to connect to backend server: {str(e)}"

    assistant_message = {"role": "assistant", "content": bot_reply}

    # Voice -> Voice: if the question came in as speech, generate the
    # audio reply now and store it so it renders (and auto-plays) below.
    if used_voice_input:
        try:
            tts = gTTS(bot_reply)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            assistant_message["audio_bytes"] = buf.getvalue()
        except Exception:
            pass

    st.session_state.messages.append(assistant_message)
    st.rerun()
