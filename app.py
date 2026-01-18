import streamlit as st, os, openai, json, subprocess
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from elevenlabs import generate, save
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image
from io import BytesIO
import requests, uuid, time

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

st.set_page_config(page_title="AutoYouTube IA", page_icon="🤖")
st.title("🎬 Generador diario de videos IA")

with st.sidebar:
    st.markdown("### 1) Subir credenciales")
    uploaded = st.file_uploader("client_secret.json", type="json")
    openai_key = st.text_input("OpenAI API key", type="password")
    eleven_key = st.text_input("ElevenLabs API key", type="password")
    nicho = st.text_input("Nicho del canal", value="Inteligencia Artificial")
    cant = st.number_input("Videos a crear", min_value=1, max_value=5, value=2)
    if st.button("Guardar"):
        os.makedirs("secrets", exist_ok=True)
        if uploaded:
            with open("secrets/client_secret.json","wb") as f:
                f.write(uploaded.getbuffer())
        if openai_key:
            openai.api_key = openai_key
            st.success("OpenAI guardada")
        if eleven_key:
            os.environ["ELEVEN_API_KEY"] = eleven_key
            st.success("ElevenLabs guardada")

def generar_guion(tema):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":f"Guion de 30 s para YouTube Short sobre {tema}, tono joven y dinámico, máx 80 palabras."}]
    ).choices[0].message.content

def generar_audio(texto, file):
    audio = generate(text=texto, voice="Rachel", model="eleven_multilingual_v2")
    save(audio, file)

def generar_imagenes(tema, n=5):
    imgs=[]
    for i in range(n):
        url=openai.Image.create(prompt=f"{tema}, estilo futurista colorido, 512x512",n=1,size="512x512").data[0].url
        img=Image.open(BytesIO(requests.get(url).content))
        fname=f"temp{i}.png"
        img.save(fname)
        imgs.append(fname)
    return imgs

def crear_video(imgs, audio, out):
    clips=[ImageClip(im).set_duration(6) for im in imgs]
    video=concatenate_videoclips(clips,method="compose")
    aud=AudioFileClip(audio)
    video=video.set_audio(aud).set_duration(aud.duration)
    video.write_videofile(out,fps=24,codec="libx264",audio_codec="aac",logger=None)

def yt_service():
    creds=None
    if os.path.exists("token.json"):
        creds=Credentials.from_authorized_user_file("token.json",SCOPES)
    if not creds or not creds.valid:
        flow=InstalledAppFlow.from_client_secrets_file("secrets/client_secret.json",SCOPES)
        creds=flow.run_local_server(port=0)
        with open("token.json","w") as t: t.write(creds.to_json())
    return build("youtube","v3",credentials=creds)

def subir(titulo,desc,file):
    youtube=yt_service()
    body=dict(snippet=dict(title=titulo,description=desc,tags=["IA","Shorts"],categoryId="28"),
              status=dict(privacyStatus="public"))
    media=MediaFileUpload(file,chunksize=-1,resumable=True)
    res=youtube.videos().insert(part="snippet,status",body=body,media_body=media).execute()
    return res["id"]

if st.button("▶️ Ejecutar bot"):
    bar=st.progress(0)
    for i in range(cant):
        tema=f"{nicho} – Dato #{i+1}"
        st.write(f"🔰 Procesando: {tema}")
        guion=generar_guion(tema)
        audio=f"audio{i}.mp3"
        video=f"video{i}.mp4"
        generar_audio(guion,audio)
        bar.progress((i*4+1)/(cant*4))
        imgs=generar_imagenes(tema)
        bar.progress((i*4+2)/(cant*4))
        crear_video(imgs,audio,video)
        bar.progress((i*4+3)/(cant*4))
        vid_id=subir(f"{tema} #Shorts",guion+"\n\n#IA #Shorts",video)
        bar.progress((i*4+4)/(cant*4))
        st.success(f"✅ Subido: https://youtu.be/{vid_id}")
    st.balloons()
