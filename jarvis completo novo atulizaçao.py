# ============================================================
# J.A.R.V.I.S — VERSÃO STREAMLIT (para share.streamlit.io)
# ============================================================
# 🇧🇷 PORTUGUÊS DO BRASIL
#
# Adaptado da versão V8 (Tkinter desktop) para rodar 100% na
# nuvem via Streamlit Community Cloud.
#
# O QUE MUDOU EM RELAÇÃO À VERSÃO TKINTER (e por quê):
#
# - Interface: Tkinter -> Streamlit (Tkinter não roda num
#   servidor web, precisa de tela local).
# - Cérebro: OmniRoute (http://localhost:...) -> Pollinations AI
#   (gratuita, sem chave). O endpoint local do OmniRoute só
#   existe no SEU PC — o servidor do Streamlit Cloud nunca
#   conseguiria acessá-lo.
# - Voz (saída): pyttsx3 -> gTTS. pyttsx3 fala usando o
#   alto-falante do computador que roda o script; no servidor
#   da nuvem isso não existe (e ninguém ouviria). O gTTS gera
#   um arquivo de áudio que é tocado no NAVEGADOR do usuário.
# - Microfone (entrada): SoundCard -> st.audio_input. SoundCard
#   captura o áudio da placa de som do servidor; st.audio_input
#   grava o áudio pelo microfone do NAVEGADOR do usuário e
#   manda pro servidor, que é o jeito certo de fazer isso na web.
# - Comandos de PC (abrir calculadora, bloco de notas,
#   explorador, configurações): REMOVIDOS. Eles rodariam no
#   servidor da nuvem, não no computador do usuário — não fazem
#   sentido e foram tirados.
# - "Abrir site" / "pesquisar": em vez de abrir o navegador do
#   servidor (webbrowser.open, que não afeta o usuário), agora
#   o JARVIS responde com um LINK clicável no chat.
# - Memória (memoria.json): continua funcionando durante a
#   sessão/enquanto o app estiver no ar, mas o Streamlit Cloud
#   tem armazenamento temporário — um redeploy ou reinício do
#   app pode apagar o arquivo. Para algo 100% permanente no
#   futuro, dá pra trocar por um banco de dados externo.
# ============================================================

import streamlit as st
import requests
import json
import os
import datetime
import urllib.parse
import io

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


# ============================================================
# CONFIGURAÇÃO
# ============================================================

POLLINATIONS_URL = "https://text.pollinations.ai/openai"
MODELO = "openai"
MEMORIA_FILE = "memoria.json"

SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "roblox": "https://www.roblox.com",
}


# ============================================================
# MEMÓRIA
# ============================================================

def carregar_memoria():
    if not os.path.exists(MEMORIA_FILE):
        return {}
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def salvar_memoria():
    try:
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.memoria, f, ensure_ascii=False, indent=2)
    except Exception as erro:
        print("Erro ao salvar memória:", erro)


# ============================================================
# ESTADO (session_state substitui as variáveis globais do Tkinter)
# ============================================================

if "historico" not in st.session_state:
    st.session_state.historico = []      # enviado para a IA
if "chat" not in st.session_state:
    st.session_state.chat = []           # exibido na tela: [(remetente, texto)]
if "memoria" not in st.session_state:
    st.session_state.memoria = carregar_memoria()
if "voz_ativa" not in st.session_state:
    st.session_state.voz_ativa = True
if "status" not in st.session_state:
    st.session_state.status = ("PRONTA", "#00ff9d")
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None


def set_status(texto, cor="#00ff9d"):
    st.session_state.status = (texto, cor)


def adicionar_chat(remetente, texto):
    st.session_state.chat.append((remetente, texto))


# ============================================================
# IA — Pollinations (gratuita, sem chave, funciona na nuvem)
# ============================================================

def perguntar_ia(pergunta):
    memoria_texto = ""
    if st.session_state.memoria:
        try:
            memoria_texto = "\n\nMEMÓRIA DO SENHOR:\n" + json.dumps(
                st.session_state.memoria, ensure_ascii=False, indent=2
            )
        except Exception:
            memoria_texto = ""

    sistema = f"""Você é J.A.R.V.I.S., um assistente pessoal avançado.

IDIOMA:
- Responda sempre em Português do Brasil.

TRATAMENTO:
- Chame o usuário de senhor naturalmente.

PERSONALIDADE:
- Inteligente, confiante, objetivo, educado, humor leve quando apropriado.

REGRAS:
- Não invente informações.
- Você é uma versão web e NÃO tem acesso ao computador do usuário
  (não pode abrir programas nem arquivos locais).
- Se não souber, diga que não sabe.
- Para perguntas simples, seja breve.
{memoria_texto}
"""

    mensagens = [{"role": "system", "content": sistema}]
    mensagens.extend(st.session_state.historico[-20:])
    mensagens.append({"role": "user", "content": pergunta})

    try:
        set_status("PENSANDO", "#ffd166")
        resposta = requests.post(
            POLLINATIONS_URL,
            json={"model": MODELO, "messages": mensagens, "temperature": 0.7},
            timeout=60,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        texto = dados.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not texto:
            set_status("ERRO IA", "#ff496c")
            return "Senhor, a IA retornou uma resposta vazia."
        texto = str(texto).strip()
        st.session_state.historico.append({"role": "user", "content": pergunta})
        st.session_state.historico.append({"role": "assistant", "content": texto})
        set_status("PRONTA", "#00ff9d")
        return texto
    except requests.exceptions.ConnectionError:
        set_status("IA OFFLINE", "#ff496c")
        return "Senhor, não consegui conectar à IA. Verifique a internet do servidor."
    except requests.exceptions.Timeout:
        set_status("TIMEOUT", "#ff496c")
        return "Senhor, a IA demorou demais para responder."
    except Exception as erro:
        set_status("ERRO", "#ff496c")
        return f"Senhor, ocorreu um erro: {erro}"


# ============================================================
# DATA / HORA
# ============================================================

def data_hora():
    agora = datetime.datetime.now()
    return (
        "Senhor, no servidor agora é "
        + agora.strftime("%d/%m/%Y às %H:%M")
        + " (horário do servidor — pode não ser o seu fuso local)."
    )


# ============================================================
# SITES E PESQUISA
# ============================================================

def abrir_site(nome):
    nome = nome.lower().strip()
    if nome in SITES:
        return f"Senhor, aqui está o link: [{nome}]({SITES[nome]})"
    return None


def pesquisar(consulta):
    consulta = consulta.strip()
    if not consulta:
        return "Senhor, diga o que deseja pesquisar."
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(consulta)
    return f"Senhor, aqui está a pesquisa: [{consulta}]({url})"


# ============================================================
# PROCESSAMENTO DE COMANDOS
# ============================================================

def processar(pergunta):
    pergunta = pergunta.strip()
    if not pergunta:
        return
    adicionar_chat("VOCÊ", pergunta)
    c = pergunta.lower().strip()

    if c in ("sair", "encerrar", "desligar", "desligar jarvis"):
        resposta = "Até logo, senhor. (Para encerrar, é só fechar esta aba do navegador.)"
    elif "que horas" in c or c in ("hora", "data") or "que dia é hoje" in c:
        resposta = data_hora()
    elif c.startswith("pesquisar "):
        resposta = pesquisar(pergunta[len("pesquisar "):])
    elif c.startswith("lembre que "):
        info = pergunta[len("lembre que "):].strip()
        if info:
            chave = "informacao_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            st.session_state.memoria[chave] = info
            salvar_memoria()
            resposta = "Entendido, senhor. Guardei essa informação."
        else:
            resposta = "Senhor, diga qual informação devo guardar."
    elif c in ("minha memória", "minha memoria", "mostrar memória", "mostrar memoria"):
        if not st.session_state.memoria:
            resposta = "Senhor, minha memória está vazia."
        else:
            partes = [f"• {v}" for v in st.session_state.memoria.values()]
            resposta = "Senhor, estas são as informações que guardei:\n\n" + "\n".join(partes)
    elif c in ("apagar memória", "apagar memoria", "limpar memória", "limpar memoria"):
        st.session_state.memoria.clear()
        salvar_memoria()
        resposta = "Minha memória foi limpa, senhor."
    else:
        resposta = None
        if c.startswith("abrir "):
            resposta = abrir_site(c[6:].strip())
        if resposta is None:
            resposta = perguntar_ia(pergunta)

    adicionar_chat("J.A.R.V.I.S", resposta)
    if st.session_state.voz_ativa:
        st.session_state.audio_bytes = gerar_audio(resposta)


# ============================================================
# VOZ — SAÍDA (gTTS: gera áudio, tocado no navegador do usuário)
# ============================================================

def gerar_audio(texto):
    if gTTS is None or not texto:
        return None
    try:
        buffer = io.BytesIO()
        gTTS(text=texto, lang="pt", tld="com.br").write_to_fp(buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception as erro:
        print("Erro ao gerar áudio:", erro)
        return None


# ============================================================
# VOZ — ENTRADA (microfone do NAVEGADOR via st.audio_input)
# ============================================================

def transcrever(audio_value):
    if sr is None:
        return None, "Senhor, a biblioteca SpeechRecognition não está instalada."
    try:
        reconhecedor = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_value.getvalue())) as fonte:
            audio_rec = reconhecedor.record(fonte)
        texto = reconhecedor.recognize_google(audio_rec, language="pt-BR")
        return texto, None
    except sr.UnknownValueError:
        return None, "Senhor, não consegui entender o áudio."
    except sr.RequestError:
        return None, "Senhor, o serviço de reconhecimento de voz falhou (verifique a internet)."
    except Exception as erro:
        return None, f"Senhor, erro no microfone: {erro}"


# ============================================================
# INTERFACE
# ============================================================

st.set_page_config(page_title="J.A.R.V.I.S", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #02060b; }
    .nucleo {
        width: 150px; height: 150px; border-radius: 50%;
        margin: 15px auto;
        background: radial-gradient(circle, #008fb8 0%, #06283a 70%);
        border: 3px solid #00c8ff;
        display: flex; align-items: center; justify-content: center;
        color: #e8faff; font-size: 40px; font-weight: bold;
        animation: pulsar 2.2s ease-in-out infinite;
        box-shadow: 0 0 40px #00c8ff55;
    }
    @keyframes pulsar {
        0% { box-shadow: 0 0 20px #00c8ff55; transform: scale(1); }
        50% { box-shadow: 0 0 55px #00c8ffaa; transform: scale(1.05); }
        100% { box-shadow: 0 0 20px #00c8ff55; transform: scale(1); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='text-align:center; color:#00c8ff;'>J.A.R.V.I.S</h1>"
    "<p style='text-align:center; color:#78909c;'>JUST A RATHER VERY INTELLIGENT SYSTEM</p>",
    unsafe_allow_html=True,
)

texto_status, cor_status = st.session_state.status
st.markdown(
    f"<p style='text-align:center; color:{cor_status}; font-weight:bold;'>● {texto_status}</p>",
    unsafe_allow_html=True,
)

col_chat, col_direita = st.columns([3, 1])

with col_direita:
    st.markdown("<div class='nucleo'>J</div>", unsafe_allow_html=True)

    st.session_state.voz_ativa = st.toggle("🔊 Voz ativada", value=st.session_state.voz_ativa)

    audio_value = st.audio_input("🎤 Fale com o JARVIS")
    if audio_value is not None:
        texto, erro = transcrever(audio_value)
        if erro:
            adicionar_chat("SISTEMA", erro)
        elif texto:
            processar(texto)
        st.rerun()

    if st.button("🗑️ Limpar memória"):
        st.session_state.memoria.clear()
        salvar_memoria()
        adicionar_chat("SISTEMA", "Memória apagada.")
        st.rerun()

    if st.button("🧹 Limpar conversa"):
        st.session_state.chat = []
        st.session_state.historico = []
        st.rerun()

with col_chat:
    for remetente, texto in st.session_state.chat:
        papel = "user" if remetente == "VOCÊ" else "assistant"
        with st.chat_message(papel):
            st.markdown(texto)

    if st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format="audio/mp3", autoplay=True)
        st.session_state.audio_bytes = None

    pergunta = st.chat_input("Digite seu comando...")
    if pergunta:
        processar(pergunta)
        st.rerun()

if not st.session_state.chat:
    adicionar_chat("J.A.R.V.I.S", "Sistema online, senhor. J.A.R.V.I.S está pronta.")
    st.rerun()
