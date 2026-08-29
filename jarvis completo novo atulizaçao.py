# ============================================================
# J.A.R.V.I.S V8
# ============================================================
# 🇧🇷 PORTUGUÊS DO BRASIL
#
# 🧠 CÉREBRO: OmniRoute
# 🔊 VOZ: pyttsx3
# 🎤 MICROFONE: SoundCard
# 🗣️ RECONHECIMENTO: Google Speech Recognition
# 💾 MEMÓRIA: memoria.json
# 🎨 INTERFACE: Tkinter + núcleo azul animado
#
# OmniRoute padrão:
# http://localhost:20128/v1/chat/completions
# ============================================================

import tkinter as tk
from tkinter import scrolledtext, messagebox

import threading
import requests
import json
import os
import webbrowser
import subprocess
import datetime
import urllib.parse
import tempfile
import wave
import math
import queue
import time


# ============================================================
# BIBLIOTECAS OPCIONAIS
# ============================================================

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import soundcard as sc
    import numpy as np
except ImportError:
    sc = None
    np = None


# ============================================================
# CONFIGURAÇÃO
# ============================================================

OMNIROUTE_URL = (
    "http://localhost:20128/v1/chat/completions"
)


# ------------------------------------------------------------
# API KEY
# ------------------------------------------------------------
#
# Se seu OmniRoute não exigir chave, deixe:
#
# OMNIROUTE_API_KEY = ""
#
# Se exigir, coloque sua chave aqui.
#
# ------------------------------------------------------------
OMNIROUTE_API_KEY = ""
# ------------------------------------------------------------
# MODELO
# ------------------------------------------------------------
#
# "auto" pode ser usado quando o OmniRoute estiver
# configurado para escolher automaticamente.
#
# ------------------------------------------------------------

MODELO = "auto"

MEMORIA_FILE = "memoria.json"


# ============================================================
# ESTADO DO SISTEMA
# ============================================================

voz_ativa = True

ouvindo = False

falando = False

encerrando = False

historico = []

memoria = {}

fala_lock = threading.Lock()

processamento_lock = threading.Lock()


# ============================================================
# CORES
# ============================================================

FUNDO = "#02060b"

PAINEL = "#07131f"

PAINEL_2 = "#030a12"

AZUL = "#00c8ff"

AZUL_CLARO = "#8cecff"

BRANCO = "#e8faff"

CINZA = "#78909c"

VERDE = "#00ff9d"

AMARELO = "#ffd166"

VERMELHO = "#ff496c"


# ============================================================
# JANELA
# ============================================================

janela = tk.Tk()

janela.title(
    "J.A.R.V.I.S V8"
)

janela.geometry(
    "1250x800"
)

janela.minsize(
    950,
    650
)

janela.configure(
    bg=FUNDO
)


# ============================================================
# FUNÇÕES DE SEGURANÇA DA INTERFACE
# ============================================================

def depois(funcao, *args):

    if encerrando:
        return

    try:
        janela.after(
            0,
            lambda: funcao(*args)
        )
    except Exception:
        pass


def atualizar_status(
    texto,
    cor=VERDE
):

    def atualizar():

        try:

            status.config(
                text=f"● {texto}",
                fg=cor
            )

        except Exception:
            pass

    depois(atualizar)


def atualizar_mic(
    texto,
    cor=CINZA
):

    def atualizar():

        try:

            status_mic.config(
                text=texto,
                fg=cor
            )

        except Exception:
            pass

    depois(atualizar)


def atualizar_ia(
    texto,
    cor=VERDE
):

    def atualizar():

        try:

            status_ia.config(
                text=texto,
                fg=cor
            )

        except Exception:
            pass

    depois(atualizar)


def adicionar_chat(
    remetente,
    texto
):

    def escrever():

        try:

            chat.config(
                state="normal"
            )

            chat.insert(
                tk.END,
                f"\n{remetente}\n",
                "titulo"
            )

            chat.insert(
                tk.END,
                str(texto) + "\n"
            )

            chat.see(
                tk.END
            )

            chat.config(
                state="disabled"
            )

        except Exception:
            pass

    depois(escrever)


# ============================================================
# MEMÓRIA
# ============================================================

def carregar_memoria():

    global memoria

    if not os.path.exists(
        MEMORIA_FILE
    ):

        memoria = {}

        return

    try:

        with open(
            MEMORIA_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

            if isinstance(
                dados,
                dict
            ):

                memoria = dados

            else:

                memoria = {}

    except Exception as erro:

        print(
            "Erro ao carregar memória:",
            erro
        )

        memoria = {}


def salvar_memoria():

    try:

        arquivo_temp = (
            MEMORIA_FILE
            + ".tmp"
        )

        with open(
            arquivo_temp,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                memoria,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            arquivo_temp,
            MEMORIA_FILE
        )

    except Exception as erro:

        print(
            "Erro ao salvar memória:",
            erro
        )


carregar_memoria()


# ============================================================
# VOZ
# ============================================================

def encontrar_voz_ptbr(
    engine
):

    try:

        vozes = engine.getProperty(
            "voices"
        )

    except Exception:

        return None

    melhores = []

    portugues = []

    for voz in vozes:

        nome = str(
            getattr(
                voz,
                "name",
                ""
            )
        ).lower()

        identificador = str(
            getattr(
                voz,
                "id",
                ""
            )
        ).lower()

        idiomas = str(
            getattr(
                voz,
                "languages",
                ""
            )
        ).lower()

        dados = (
            nome
            + " "
            + identificador
            + " "
            + idiomas
        )

        if (
            "pt-br" in dados
            or "pt_br" in dados
            or "brazil" in dados
            or "brasil" in dados
        ):

            melhores.append(
                voz
            )

        elif (
            "portugu" in dados
            or "pt-" in dados
        ):

            portugues.append(
                voz
            )

    if melhores:

        return melhores[0]

    if portugues:

        return portugues[0]

    return None


def falar(
    texto
):

    global falando

    if not texto:
        return

    adicionar_chat(
        "J.A.R.V.I.S",
        texto
    )

    if not voz_ativa:
        return

    if pyttsx3 is None:

        atualizar_status(
            "VOZ INDISPONÍVEL",
            VERMELHO
        )

        return

    def falar_thread():

        global falando

        with fala_lock:

            falando = True

            atualizar_status(
                "FALANDO",
                AZUL
            )

            engine = None

            try:

                engine = pyttsx3.init()

                engine.setProperty(
                    "rate",
                    155
                )

                engine.setProperty(
                    "volume",
                    1.0
                )

                voz = encontrar_voz_ptbr(
                    engine
                )

                if voz:

                    engine.setProperty(
                        "voice",
                        voz.id
                    )

                engine.say(
                    texto
                )

                engine.runAndWait()

            except Exception as erro:

                print(
                    "Erro na voz:",
                    erro
                )

            finally:

                try:

                    if engine:

                        engine.stop()

                except Exception:
                    pass

                falando = False

                atualizar_status(
                    "PRONTA",
                    VERDE
                )

    threading.Thread(
        target=falar_thread,
        daemon=True
    ).start()


def testar_voz():

    falar(
        "Olá, senhor. "
        "Teste de voz concluído. "
        "J.A.R.V.I.S está funcionando "
        "em português do Brasil."
    )


# ============================================================
# CABEÇALHO
# ============================================================

tk.Label(
    janela,
    text="J.A.R.V.I.S",
    font=(
        "Arial",
        36,
        "bold"
    ),
    fg=AZUL,
    bg=FUNDO
).pack(
    pady=(18, 0)
)


tk.Label(
    janela,
    text=(
        "JUST A RATHER VERY "
        "INTELLIGENT SYSTEM"
    ),
    font=(
        "Consolas",
        9
    ),
    fg=CINZA,
    bg=FUNDO
).pack()


status = tk.Label(
    janela,
    text="● PRONTA",
    font=(
        "Consolas",
        11,
        "bold"
    ),
    fg=VERDE,
    bg=FUNDO
)

status.pack(
    pady=10
)


# ============================================================
# ÁREA PRINCIPAL
# ============================================================

principal = tk.Frame(
    janela,
    bg=FUNDO
)

principal.pack(
    fill="both",
    expand=True,
    padx=28,
    pady=5
)


# ============================================================
# PAINEL DO CHAT
# ============================================================

painel_chat = tk.Frame(
    principal,
    bg=PAINEL,
    highlightbackground="#0c3b50",
    highlightthickness=1
)

painel_chat.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 10)
)


chat = scrolledtext.ScrolledText(
    painel_chat,
    wrap=tk.WORD,
    font=(
        "Consolas",
        11
    ),
    bg=PAINEL_2,
    fg=BRANCO,
    insertbackground=AZUL,
    relief="flat"
)

chat.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=15
)

chat.config(
    state="disabled"
)

chat.tag_config(
    "titulo",
    foreground=AZUL,
    font=(
        "Consolas",
        10,
        "bold"
    )
)


# ============================================================
# PAINEL DIREITO
# ============================================================

direita = tk.Frame(
    principal,
    bg=PAINEL,
    width=300,
    highlightbackground="#0c3b50",
    highlightthickness=1
)

direita.pack(
    side="right",
    fill="y"
)

direita.pack_propagate(
    False
)


tk.Label(
    direita,
    text="NÚCLEO J.A.R.V.I.S",
    font=(
        "Arial",
        13,
        "bold"
    ),
    fg=AZUL,
    bg=PAINEL
).pack(
    pady=(22, 8)
)


# ============================================================
# NÚCLEO AZUL ANIMADO
# ============================================================

canvas = tk.Canvas(
    direita,
    width=250,
    height=250,
    bg=PAINEL,
    highlightthickness=0
)

canvas.pack(
    pady=5
)

angulo = 0

pulso = 0

direcao_pulso = 1


def animar_nucleo():

    global angulo
    global pulso
    global direcao_pulso

    if encerrando:
        return

    try:

        canvas.delete(
            "all"
        )

        cx = 125
        cy = 125

        # ----------------------------
        # PULSO
        # ----------------------------

        pulso += (
            direcao_pulso
            * 0.8
        )

        if pulso >= 18:

            direcao_pulso = -1

        if pulso <= 0:

            direcao_pulso = 1

        # ----------------------------
        # ANÉIS
        # ----------------------------

        canvas.create_oval(
            10 - pulso / 3,
            10 - pulso / 3,
            240 + pulso / 3,
            240 + pulso / 3,
            outline="#06384c",
            width=2
        )

        canvas.create_oval(
            30,
            30,
            220,
            220,
            outline="#075b78",
            width=2
        )

        canvas.create_oval(
            50,
            50,
            200,
            200,
            outline="#008fb8",
            width=2
        )

        canvas.create_oval(
            70,
            70,
            180,
            180,
            outline=AZUL,
            width=3
        )

        # ----------------------------
        # ARCOS
        # ----------------------------

        canvas.create_arc(
            40,
            40,
            210,
            210,
            start=angulo,
            extent=75,
            outline=AZUL_CLARO,
            width=4
        )

        canvas.create_arc(
            58,
            58,
            192,
            192,
            start=-angulo * 1.5,
            extent=50,
            outline=VERDE,
            width=3
        )

        canvas.create_arc(
            20,
            20,
            230,
            230,
            start=angulo * 0.5,
            extent=30,
            outline="#008fb8",
            width=3
        )

        # ----------------------------
        # NÚCLEO
        # ----------------------------

        tamanho = (
            28
            + pulso / 4
        )

        canvas.create_oval(
            cx - tamanho,
            cy - tamanho,
            cx + tamanho,
            cy + tamanho,
            fill="#06283a",
            outline=AZUL,
            width=3
        )

        canvas.create_oval(
            cx - 14,
            cy - 14,
            cx + 14,
            cy + 14,
            fill="#008fb8",
            outline=AZUL_CLARO,
            width=2
        )

        canvas.create_text(
            cx,
            cy,
            text="J",
            fill=BRANCO,
            font=(
                "Arial",
                20,
                "bold"
            )
        )

        # ----------------------------
        # MARCADORES
        # ----------------------------

        for i in range(8):

            a = math.radians(
                angulo
                + i * 45
            )

            x1 = (
                cx
                + math.cos(a)
                * 100
            )

            y1 = (
                cy
                + math.sin(a)
                * 100
            )

            x2 = (
                cx
                + math.cos(a)
                * 113
            )

            y2 = (
                cy
                + math.sin(a)
                * 113
            )

            canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=AZUL,
                width=2
            )

        angulo = (
            angulo + 2
        ) % 360

        janela.after(
            30,
            animar_nucleo
        )

    except Exception:
        pass


animar_nucleo()


# ============================================================
# STATUS DO MICROFONE
# ============================================================

status_mic = tk.Label(
    direita,
    text="MICROFONE: PRONTO",
    font=(
        "Consolas",
        9
    ),
    fg=CINZA,
    bg=PAINEL
)

status_mic.pack(
    pady=3
)


# ============================================================
# STATUS DA IA
# ============================================================

status_ia = tk.Label(
    direita,
    text="IA: OMNIROUTE",
    font=(
        "Consolas",
        9,
        "bold"
    ),
    fg=VERDE,
    bg=PAINEL
)

status_ia.pack(
    pady=3
)


# ============================================================
# OMNIROUTE
# ============================================================

def perguntar_ia(
    pergunta
):

    if not OMNIROUTE_URL:

        return (
            "Senhor, o endereço do "
            "OmniRoute não foi configurado."
        )

    memoria_texto = ""

    if memoria:

        try:

            memoria_texto = (
                "\n\nMEMÓRIA DO SENHOR:\n"
                + json.dumps(
                    memoria,
                    ensure_ascii=False,
                    indent=2
                )
            )

        except Exception:
            memoria_texto = ""

    sistema = f"""
Você é J.A.R.V.I.S., um assistente
pessoal avançado.

IDIOMA:
- Responda sempre em Português do Brasil.
- Não responda em inglês sem o senhor pedir.

TRATAMENTO:
- Chame o usuário de senhor naturalmente.
- Seja educado e profissional.

PERSONALIDADE:
- Inteligente
- Confiante
- Objetivo
- Educado
- Humor leve quando apropriado.

REGRAS:
- Não invente informações.
- Não diga que executou algo se não executou.
- Se não souber, diga que não sabe.
- Para perguntas simples, seja breve.

{memoria_texto}
"""

    mensagens = [
        {
            "role": "system",
            "content": sistema
        }
    ]

    mensagens.extend(
        historico[-20:]
    )

    mensagens.append(
        {
            "role": "user",
            "content": pergunta
        }
    )

    headers = {
        "Content-Type":
            "application/json"
    }

    if OMNIROUTE_API_KEY.strip():

        headers["Authorization"] = (
            "Bearer "
            + OMNIROUTE_API_KEY.strip()
        )

    try:

        atualizar_status(
            "PENSANDO",
            AMARELO
        )

        atualizar_ia(
            "IA: PROCESSANDO",
            AMARELO
        )

        resposta = requests.post(
            OMNIROUTE_URL,
            headers=headers,
            json={
                "model": MODELO,
                "messages": mensagens,
                "temperature": 0.7,
                "stream": False
            },
            timeout=120
        )

        resposta.raise_for_status()

        dados = resposta.json()

        # --------------------------------
        # FORMATO OPENAI
        # --------------------------------

        if (
            "choices" in dados
            and dados["choices"]
        ):

            texto = (
                dados["choices"][0]
                .get("message", {})
                .get("content", "")
            )

        else:

            texto = ""

        # --------------------------------
        # VERIFICAÇÃO
        # --------------------------------

        if not texto:

            return (
                "Senhor, o OmniRoute "
                "retornou uma resposta vazia."
            )

        texto = str(
            texto
        ).strip()

        historico.append(
            {
                "role": "user",
                "content": pergunta
            }
        )

        historico.append(
            {
                "role": "assistant",
                "content": texto
            }
        )

        atualizar_ia(
            "IA: ONLINE",
            VERDE
        )

        atualizar_status(
            "PRONTA",
            VERDE
        )

        return texto

    except requests.exceptions.ConnectionError:

        atualizar_ia(
            "IA: OFFLINE",
            VERMELHO
        )

        atualizar_status(
            "OMNIROUTE OFFLINE",
            VERMELHO
        )

        return (
            "Senhor, não consegui conectar "
            "ao OmniRoute. Verifique se ele "
            "está aberto."
        )

    except requests.exceptions.Timeout:

        atualizar_ia(
            "IA: TEMPO ESGOTADO",
            VERMELHO
        )

        atualizar_status(
            "TIMEOUT",
            VERMELHO
        )

        return (
            "Senhor, o OmniRoute demorou "
            "demais para responder."
        )

    except requests.exceptions.HTTPError as erro:

        codigo = ""

        try:

            codigo = (
                " HTTP "
                + str(
                    erro.response.status_code
                )
            )

        except Exception:
            pass

        atualizar_ia(
            "IA: ERRO API",
            VERMELHO
        )

        atualizar_status(
            "ERRO API",
            VERMELHO
        )

        return (
            "Senhor, o OmniRoute "
            "recusou a solicitação."
            + codigo
        )

    except ValueError:

        atualizar_ia(
            "IA: RESPOSTA INVÁLIDA",
            VERMELHO
        )

        return (
            "Senhor, o OmniRoute "
            "enviou uma resposta "
            "que não consegui interpretar."
        )

    except Exception as erro:

        atualizar_ia(
            "IA: ERRO",
            VERMELHO
        )

        atualizar_status(
            "ERRO",
            VERMELHO
        )

        return (
            "Senhor, ocorreu um erro "
            "no cérebro OmniRoute: "
            + str(erro)
        )


# ============================================================
# DATA E HORA
# ============================================================

def data_hora():

    agora = datetime.datetime.now()

    return (
        "Senhor, hoje é "
        + agora.strftime(
            "%d/%m/%Y"
        )
        + " e são "
        + agora.strftime(
            "%H:%M"
        )
        + "."
    )


# ============================================================
# SITES
# ============================================================

SITES = {

    "google":
        "https://www.google.com",

    "youtube":
        "https://www.youtube.com",

    "chatgpt":
        "https://chatgpt.com",

    "github":
        "https://github.com",

    "gmail":
        "https://mail.google.com",

    "whatsapp":
        "https://web.whatsapp.com",

    "instagram":
        "https://www.instagram.com",

    "facebook":
        "https://www.facebook.com",

    "roblox":
        "https://www.roblox.com"
}


def abrir_site(
    nome
):

    nome = nome.lower().strip()

    if nome in SITES:

        try:

            webbrowser.open(
                SITES[nome]
            )

            return (
                f"Senhor, abrindo {nome}."
            )

        except Exception:

            return (
                "Senhor, não consegui "
                "abrir o navegador."
            )

    return None


# ============================================================
# COMANDOS DO WINDOWS
# ============================================================

def comando_pc(
    texto
):

    c = texto.lower().strip()

    if c == "abrir calculadora":

        try:

            subprocess.Popen(
                "calc.exe"
            )

            return (
                "Senhor, calculadora aberta."
            )

        except Exception:

            return (
                "Senhor, não consegui "
                "abrir a calculadora."
            )

    if c in (
        "abrir bloco de notas",
        "abrir bloco notas"
    ):

        try:

            subprocess.Popen(
                "notepad.exe"
            )

            return (
                "Senhor, bloco de notas aberto."
            )

        except Exception:

            return (
                "Senhor, não consegui "
                "abrir o bloco de notas."
            )

    if c in (
        "abrir arquivos",
        "abrir explorador",
        "abrir explorador de arquivos"
    ):

        try:

            subprocess.Popen(
                "explorer.exe"
            )

            return (
                "Senhor, explorador "
                "de arquivos aberto."
            )

        except Exception:

            return (
                "Senhor, não consegui "
                "abrir o explorador."
            )

    if c == "abrir configurações":

        try:

            subprocess.Popen(
                "start ms-settings:",
                shell=True
            )

            return (
                "Senhor, configurações abertas."
            )

        except Exception:

            return (
                "Senhor, não consegui "
                "abrir as configurações."
            )

    if c.startswith(
        "abrir "
    ):

        nome = c[6:].strip()

        resultado = abrir_site(
            nome
        )

        if resultado:

            return resultado

    return None


# ============================================================
# PESQUISA
# ============================================================

def pesquisar(
    consulta
):

    consulta = consulta.strip()

    if not consulta:

        return (
            "Senhor, diga o que deseja pesquisar."
        )

    try:

        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(
                consulta
            )
        )

        webbrowser.open(
            url
        )

        return (
            "Senhor, iniciei a pesquisa por "
            + consulta
            + "."
        )

    except Exception:

        return (
            "Senhor, não consegui "
            "abrir a pesquisa."
        )


# ============================================================
# PROCESSAMENTO
# ============================================================

def processar(
    pergunta
):

    pergunta = pergunta.strip()

    if not pergunta:
        return

    adicionar_chat(
        "VOCÊ",
        pergunta
    )

    c = pergunta.lower().strip()

    # ----------------------------------------
    # SAIR
    # ----------------------------------------

    if c in (
        "sair",
        "encerrar",
        "desligar",
        "desligar jarvis"
    ):

        falar(
            "Até logo, senhor. "
            "Encerrando o sistema."
        )

        janela.after(
            2500,
            fechar_janela
        )

        return

    # ----------------------------------------
    # DATA/HORA
    # ----------------------------------------

    if (
        "que horas" in c
        or c == "hora"
        or c == "data"
        or "que dia é hoje" in c
    ):

        resposta = data_hora()

    # ----------------------------------------
    # PESQUISA
    # ----------------------------------------

    elif c.startswith(
        "pesquisar "
    ):

        resposta = pesquisar(
            pergunta[
                len("pesquisar "):
            ]
        )

    # ----------------------------------------
    # MEMÓRIA
    # ----------------------------------------

    elif c.startswith(
        "lembre que "
    ):

        info = pergunta[
            len("lembre que "):
        ].strip()

        if info:

            chave = (
                "informacao_"
                + datetime.datetime.now()
                .strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
            )

            memoria[chave] = info

            salvar_memoria()

            resposta = (
                "Entendido, senhor. "
                "Guardei essa informação."
            )

        else:

            resposta = (
                "Senhor, diga qual informação "
                "devo guardar."
            )

    # ----------------------------------------
    # MOSTRAR MEMÓRIA
    # ----------------------------------------

    elif c in (
        "minha memória",
        "minha memoria",
        "mostrar memória",
        "mostrar memoria"
    ):

        if not memoria:

            resposta = (
                "Senhor, minha memória "
                "está vazia."
            )

        else:

            partes = []

            for valor in memoria.values():

                partes.append(
                    "• " + str(valor)
                )

            resposta = (
                "Senhor, estas são as "
                "informações que guardei:\n\n"
                + "\n".join(partes)
            )

    # ----------------------------------------
    # LIMPAR MEMÓRIA
    # ----------------------------------------

    elif c in (
        "apagar memória",
        "apagar memoria",
        "limpar memória",
        "limpar memoria"
    ):

        memoria.clear()

        salvar_memoria()

        resposta = (
            "Minha memória foi limpa, senhor."
        )

    # ----------------------------------------
    # COMANDO PC
    # ----------------------------------------

    else:

        resposta = comando_pc(
            pergunta
        )

        # ------------------------------------
        # IA
        # ------------------------------------

        if resposta is None:

            resposta = perguntar_ia(
                pergunta
            )

    falar(
        resposta
    )


# ============================================================
# ENVIO DE TEXTO
# ============================================================

def enviar():

    if encerrando:
        return

    texto = entrada.get().strip()

    if not texto:
        return

    entrada.delete(
        0,
        tk.END
    )

    threading.Thread(
        target=processar_seguro,
        args=(texto,),
        daemon=True
    ).start()


def processar_seguro(
    texto
):

    with processamento_lock:

        try:

            processar(
                texto
            )

        except Exception as erro:

            print(
                "Erro no processamento:",
                erro
            )

            falar(
                "Senhor, ocorreu um erro "
                "ao processar seu comando."
            )


# ============================================================
# MICROFONE
# ============================================================

def listar_microfones():

    if sc is None:

        return []

    try:

        return sc.all_microphones(
            include_loopback=False
        )

    except Exception:

        return []


def capturar_microfone():

    if sc is None:

        raise RuntimeError(
            "SoundCard não está instalado."
        )

    microfones = listar_microfones()

    if not microfones:

        raise RuntimeError(
            "Nenhum microfone foi encontrado."
        )

    try:

        microfone = sc.default_microphone()

        if microfone:

            return microfone

    except Exception:

        pass

    return microfones[0]


def ouvir():

    global ouvindo

    if encerrando:
        return

    if ouvindo:

        return

    if falando:

        adicionar_chat(
            "SISTEMA",
            "J.A.R.V.I.S está falando. "
            "Aguarde terminar."
        )

        return

    if sc is None or np is None:

        falar(
            "Senhor, SoundCard ou NumPy "
            "não está instalado."
        )

        return

    if sr is None:

        falar(
            "Senhor, SpeechRecognition "
            "não está instalado."
        )

        return

    ouvindo = True

    atualizar_mic(
        "MICROFONE: PREPARANDO...",
        AZUL
    )

    atualizar_status(
        "OUVINDO",
        AZUL
    )

    threading.Thread(
        target=capturar_voz,
        daemon=True
    ).start()


def capturar_voz():

    global ouvindo

    reconhecedor = sr.Recognizer()

    reconhecedor.energy_threshold = 250

    reconhecedor.dynamic_energy_threshold = True

    reconhecedor.pause_threshold = 0.8

    taxa = 16000

    segundos = 8

    caminho = None

    try:

        microfone = capturar_microfone()

        adicionar_chat(
            "SISTEMA",
            "Microfone ativo. "
            "Pode falar, senhor."
        )

        atualizar_mic(
            "MICROFONE: FALE AGORA",
            AZUL
        )

        with microfone.recorder(
            samplerate=taxa,
            channels=1
        ) as gravador:

            audio = gravador.record(
                numframes=int(
                    taxa * segundos
                )
            )

        audio = np.asarray(
            audio
        )

        if audio.ndim > 1:

            audio = audio[:, 0]

        audio = np.nan_to_num(
            audio
        )

        audio = np.clip(
            audio,
            -1,
            1
        )

        audio_int16 = (
            audio * 32767
        ).astype(
            np.int16
        )

        arquivo_temp = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        caminho = arquivo_temp.name

        arquivo_temp.close()

        with wave.open(
            caminho,
            "wb"
        ) as wav:

            wav.setnchannels(
                1
            )

            wav.setsampwidth(
                2
            )

            wav.setframerate(
                taxa
            )

            wav.writeframes(
                audio_int16.tobytes()
            )

        with sr.AudioFile(
            caminho
        ) as fonte:

            audio_rec = (
                reconhecedor.record(
                    fonte
                )
            )

        texto = (
            reconhecedor
            .recognize_google(
                audio_rec,
                language="pt-BR"
            )
        )

        if caminho:

            try:

                os.remove(
                    caminho
                )

            except Exception:
                pass

            caminho = None

        depois(
            voz_recebida,
            texto
        )

    except sr.UnknownValueError:

        limpar_arquivo_temp(
            caminho
        )

        depois(
            erro_mic,
            "Senhor, não consegui "
            "entender sua voz."
        )

    except sr.RequestError as erro:

        limpar_arquivo_temp(
            caminho
        )

        depois(
            erro_mic,
            "Senhor, o reconhecimento "
            "de voz não conseguiu acessar "
            "o serviço. Verifique sua internet."
        )

        print(
            "SpeechRecognition:",
            erro
        )

    except Exception as erro:

        limpar_arquivo_temp(
            caminho
        )

        depois(
            erro_mic,
            "Senhor, ocorreu um erro "
            "no microfone: "
            + str(erro)
        )


def limpar_arquivo_temp(
    caminho
):

    if not caminho:
        return

    try:

        if os.path.exists(
            caminho
        ):

            os.remove(
                caminho
            )

    except Exception:
        pass


def voz_recebida(
    texto
):

    global ouvindo

    ouvindo = False

    atualizar_mic(
        "MICROFONE: PRONTO",
        CINZA
    )

    atualizar_status(
        "PRONTA",
        VERDE
    )

    entrada.delete(
        0,
        tk.END
    )

    entrada.insert(
        0,
        texto
    )

    enviar()


def erro_mic(
    mensagem
):

    global ouvindo

    ouvindo = False

    atualizar_mic(
        "MICROFONE: ERRO",
        VERMELHO
    )

    atualizar_status(
        "MICROFONE ERRO",
        VERMELHO
    )

    falar(
        mensagem
    )


# ============================================================
# BOTÃO MICROFONE
# ============================================================

botao_mic = tk.Button(
    direita,
    text="🎤 OUVIR",
    command=ouvir,
    font=(
        "Arial",
        11,
        "bold"
    ),
    bg="#06283a",
    fg=AZUL_CLARO,
    activebackground="#0b4962",
    activeforeground="white",
    relief="flat",
    cursor="hand2",
    pady=12
)

botao_mic.pack(
    fill="x",
    padx=20,
    pady=(25, 8)
)


# ============================================================
# VOZ ON/OFF
# ============================================================

def alternar_voz():

    global voz_ativa

    voz_ativa = not voz_ativa

    if voz_ativa:

        botao_voz.config(
            text="🔊 VOZ: ON"
        )

        falar(
            "Voz ativada, senhor."
        )

    else:

        botao_voz.config(
            text="🔇 VOZ: OFF"
        )

        atualizar_status(
            "VOZ DESATIVADA",
            AMARELO
        )


botao_voz = tk.Button(
    direita,
    text="🔊 VOZ: ON",
    command=alternar_voz,
    font=(
        "Arial",
        10,
        "bold"
    ),
    bg="#08243a",
    fg=AZUL_CLARO,
    relief="flat",
    cursor="hand2",
    pady=10
)

botao_voz.pack(
    fill="x",
    padx=20,
    pady=5
)


# ============================================================
# TESTE DE VOZ
# ============================================================

tk.Button(
    direita,
    text="🔊 TESTAR VOZ",
    command=testar_voz,
    font=(
        "Arial",
        10,
        "bold"
    ),
    bg="#08243a",
    fg=AZUL_CLARO,
    relief="flat",
    cursor="hand2",
    pady=10
).pack(
    fill="x",
    padx=20,
    pady=5
)


# ============================================================
# ENTRADA
# ============================================================

frame_entrada = tk.Frame(
    janela,
    bg=FUNDO
)

frame_entrada.pack(
    fill="x",
    padx=28,
    pady=(5, 22)
)


entrada = tk.Entry(
    frame_entrada,
    font=(
        "Consolas",
        12
    ),
    bg=PAINEL_2,
    fg=BRANCO,
    insertbackground=AZUL,
    relief="flat"
)

entrada.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=13
)


entrada.bind(
    "<Return>",
    lambda evento: enviar()
)


tk.Button(
    frame_entrada,
    text="ENVIAR",
    command=enviar,
    font=(
        "Arial",
        10,
        "bold"
    ),
    bg="#07364a",
    fg=AZUL_CLARO,
    activebackground="#0b4962",
    relief="flat",
    cursor="hand2",
    padx=25
).pack(
    side="right",
    padx=(10, 0),
    ipady=9
)


# ============================================================
# FECHAMENTO
# ============================================================

def fechar_janela():

    global encerrando

    if encerrando:
        return

    encerrando = True

    try:

        janela.destroy()

    except Exception:
        pass


def ao_fechar():

    global encerrando

    encerrando = True

    janela.destroy()


janela.protocol(
    "WM_DELETE_WINDOW",
    ao_fechar
)


# ============================================================
# MENSAGENS INICIAIS
# ============================================================

adicionar_chat(
    "J.A.R.V.I.S",
    "Sistema online, senhor. "
    "J.A.R.V.I.S V8 está pronta."
)

adicionar_chat(
    "SISTEMA",
    "Idioma: Português do Brasil\n"
    "Microfone: SoundCard\n"
    "Reconhecimento: Google pt-BR\n"
    "Cérebro: OmniRoute\n"
    "Voz: pyttsx3\n"
    "Memória: memoria.json"
)


entrada.focus()


# ============================================================
# TESTE AUTOMÁTICO
# ============================================================

janela.after(
    1200,
    lambda: falar(
        "Sistema online, senhor. "
        "J.A.R.V.I.S está pronta "
        "para receber seus comandos."
    )
)


# ============================================================
# INICIAR
# ============================================================

janela.mainloop()