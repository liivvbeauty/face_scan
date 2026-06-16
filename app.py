import os
import re
import datetime
from io import BytesIO

import streamlit as st
from PIL import Image

import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai


# =========================================================
# CONFIG STREAMLIT
# =========================================================

st.set_page_config(
    page_title="LIIVV Beauty | Face Relax Scanner",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# SECRETS ESPERADOS
# =========================================================
# SPREADSHEET_ID = "ID_OU_URL_DA_PLANILHA"
# ACCESS_SHEET_NAME = "senha"
# SERVICES_SHEET_NAME = "servicos"
# GEMINI_API_KEY = "SUA_CHAVE_REAL_DO_GEMINI"
#
# [gcp_service_account]
# type="service_account"
# project_id="..."
# private_key_id="..."
# private_key="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
# client_email="..."
# client_id="..."
# auth_uri="https://accounts.google.com/o/oauth2/auth"
# token_uri="https://oauth2.googleapis.com/token"
# auth_provider_x509_cert_url="https://www.googleapis.com/oauth2/v1/certs"
# client_x509_cert_url="..."


RAW_SPREADSHEET_VALUE = (
    st.secrets.get("SPREADSHEET_URL")
    or st.secrets.get("SPREADSHEET_ID")
    or st.secrets.get("GOOGLE_SHEET_ID")
    or ""
)

ACCESS_SHEET_NAME = st.secrets.get("ACCESS_SHEET_NAME", "senha").strip()
SERVICES_SHEET_NAME = st.secrets.get("SERVICES_SHEET_NAME", "servicos").strip()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# =========================================================
# CSS LIIVV
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');

    .stApp { background-color: #F7F2F4; }

    .block-container {
        padding-top: 1.4rem;
        max-width: 1120px;
    }

    .liivv-header {
        background: linear-gradient(135deg, #7A3C4B 0%, #2B2B2B 100%);
        padding: 34px 18px 30px 18px;
        border-radius: 0 0 34px 34px;
        text-align: center;
        margin-bottom: 18px;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
    }

    .liivv-logo {
        font-family: 'Montserrat', Arial, sans-serif;
        font-size: 4.2rem;
        color: #EBA6A6;
        margin: 0;
        letter-spacing: 12px;
        line-height: 0.95;
        font-weight: 300;
    }

    .liivv-subtitle {
        font-family: 'Montserrat', sans-serif;
        color: #F7F2F4;
        font-size: 0.84rem;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-top: 10px;
        font-weight: 700;
    }

    .intro-card, .filter-card, .result-card, .empty-card {
        background: #FFFFFF;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 8px 20px rgba(43,43,43,0.08);
        border: 1px solid rgba(122,60,75,0.10);
        margin-bottom: 16px;
    }

    .intro-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 1.55rem;
        color: #7A3C4B;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .intro-text, .small-text {
        font-family: 'Montserrat', sans-serif;
        color: #555;
        font-size: 0.96rem;
        line-height: 1.5;
        margin: 0;
    }

    .section-title {
        font-family: 'Montserrat', sans-serif;
        font-weight: 800;
        color: #7A3C4B;
        font-size: 1.08rem;
        margin-bottom: 12px;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #EBA6A6 0%, #7A3C4B 100%);
        color: white !important;
        border-radius: 999px;
        padding: 0.85rem 1.1rem;
        font-weight: 800;
        font-size: 1.02rem;
        width: 100%;
        border: none;
        box-shadow: 0 10px 20px rgba(122, 60, 75, 0.22);
        font-family: 'Montserrat', sans-serif;
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #7A3C4B 0%, #2B2B2B 100%);
        color: white !important;
        border: none;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        border-radius: 14px;
        border-color: rgba(122,60,75,0.22);
    }

    .mini-label {
        font-weight: 800;
        color: #7A3C4B;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# GOOGLE SHEETS
# =========================================================

def extract_spreadsheet_id(value: str) -> str:
    value = str(value or "").strip().strip('"').strip("'")

    if not value:
        return ""

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if match:
        return match.group(1)

    if "/edit" in value:
        return value.split("/edit")[0].strip()

    if "?" in value:
        return value.split("?")[0].strip()

    return value.strip()


SPREADSHEET_ID = extract_spreadsheet_id(RAW_SPREADSHEET_VALUE)


@st.cache_resource
def get_client() -> gspread.Client:
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(credentials)


def get_spreadsheet():
    if not SPREADSHEET_ID:
        st.error("SPREADSHEET_ID não encontrado nos Secrets.")
        st.stop()

    return get_client().open_by_key(SPREADSHEET_ID)


@st.cache_data(ttl=60, show_spinner=False)
def get_password_from_sheet():
    worksheet = get_spreadsheet().worksheet(ACCESS_SHEET_NAME)
    records = worksheet.get_all_records()

    for row in records:
        campo = str(row.get("campo", "")).strip().lower()
        valor = str(row.get("valor", "")).strip()

        if campo == "senha":
            return valor

    return None


@st.cache_data(ttl=60, show_spinner=False)
def load_services_from_sheet():
    worksheet = get_spreadsheet().worksheet(SERVICES_SHEET_NAME)
    values = worksheet.col_values(1)

    services = []
    for value in values[1:]:
        value = str(value).strip()
        if value:
            services.append(value)

    return services


def save_result_to_sheet(client_name, service_type, observations, report_text):
    spreadsheet = get_spreadsheet()

    try:
        worksheet = spreadsheet.worksheet("resultados")
    except Exception:
        worksheet = spreadsheet.add_worksheet(
            title="resultados",
            rows=1000,
            cols=20,
        )
        worksheet.append_row(
            [
                "data_hora",
                "cliente",
                "servico",
                "observacoes",
                "relatorio",
            ],
            value_input_option="USER_ENTERED",
        )

    worksheet.append_row(
        [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            client_name,
            service_type,
            observations,
            report_text,
        ],
        value_input_option="USER_ENTERED",
    )


# =========================================================
# GEMINI
# =========================================================

def get_gemini_api_key():
    return (
        st.secrets.get("GEMINI_API_KEY")
        or st.secrets.get("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def configure_gemini():
    api_key = get_gemini_api_key()

    if not api_key or api_key.strip() in ["SUA_CHAVE_GEMINI", "COLE_AQUI_A_CHAVE_REAL_DO_GEMINI"]:
        st.error("Chave Gemini inválida. Configure GEMINI_API_KEY nos Secrets do Streamlit com uma chave real.")
        st.stop()

    genai.configure(api_key=api_key)
    return genai.GenerativeModel("models/gemini-2.5-flash")


def analyze_with_gemini(before_image, after_image, client_name, service_type, observations):
    model = configure_gemini()

    prompt = f"""
Você é uma consultora premium da LIIVV Beauty, especializada em bem-estar facial,
massagem relaxante, imagem pessoal e percepção visual de descanso.

Você receberá duas imagens:
1. Foto ANTES da massagem
2. Foto DEPOIS da massagem

Cliente: {client_name}
Serviço realizado: {service_type}
Observações internas: {observations}

REGRAS OBRIGATÓRIAS DE HONESTIDADE:
1. Não force melhora visual se ela não estiver claramente perceptível.
2. Se as fotos tiverem iluminação, ângulo, distância, expressão facial, enquadramento ou nitidez diferentes, informe que a análise é parcialmente conclusiva ou inconclusiva.
3. Se as imagens forem muito semelhantes ou insuficientes, diga claramente: "Não foi possível confirmar mudanças visuais relevantes com segurança."
4. A análise é estética e visual, não médica.
5. Não faça diagnóstico clínico.
6. Não afirme idade, doença, estado psicológico ou condição de saúde.
7. Não prometa resultado permanente.
8. Use linguagem sofisticada, objetiva e adequada a um salão premium.

Avalie visualmente:
- Aparência geral de cansaço facial
- Região dos olhos
- Testa e sinais de tensão visual
- Mandíbula e expressão facial
- Simetria visual percebida
- Expressão geral de relaxamento
- Aparência de bem-estar
- Qualidade comparativa das fotos

Formato obrigatório:

# LIIVV Face Relax Report

## Conclusão da análise
Diga se a análise é conclusiva, parcialmente conclusiva ou inconclusiva.

## Nível de confiabilidade
Alta, Média ou Baixa. Explique objetivamente.

## Resumo executivo
Texto curto, sofisticado e honesto.

## Comparativo de scores
Tabela em markdown:
Indicador | Antes | Depois | Evolução percebida | Confiança

## Evidências visuais observadas
Liste apenas o que realmente foi possível observar.

## Pontos que limitaram a análise
Liste iluminação, ângulo, nitidez, enquadramento, expressão ou distância, se aplicável.

## Leitura por região facial
### Olhos
### Testa
### Mandíbula
### Expressão geral

## Recomendação de continuidade LIIVV
Sugira próximos cuidados dentro do salão, sem linguagem médica e sem promessa de resultado.

## Mensagem curta para a cliente
Texto curto, bonito e compartilhável.

## Observação importante
Informe que esta é uma análise visual, estética e não médica.
"""

    response = model.generate_content([
        prompt,
        before_image,
        after_image,
    ])

    return response.text


# =========================================================
# IMAGENS
# =========================================================

def prepare_image(uploaded_file):
    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail((1600, 1600))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)

    return image


# =========================================================
# UI
# =========================================================

def render_header():
    st.markdown(
        """
        <div class="liivv-header">
            <div class="liivv-logo">LIIVV</div>
            <div class="liivv-subtitle">Beauty | Face Relax Scanner</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_intro():
    st.markdown(
        """
        <div class="intro-card">
            <div class="intro-title">O que mudou no seu rosto depois da massagem?</div>
            <p class="intro-text">
                Envie uma foto antes e outra depois do atendimento. A LIIVV gera uma leitura visual
                de descanso, relaxamento facial e aparência de bem-estar, com análise honesta e sem forçar conclusões.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def check_password():
    render_header()
    render_intro()

    try:
        senha_planilha = get_password_from_sheet()
    except Exception as exc:
        st.error("Erro ao acessar a senha na planilha.")
        with st.expander("Detalhes técnicos"):
            st.write("ID usado:")
            st.code(SPREADSHEET_ID)
            st.write("Aba de senha:")
            st.code(ACCESS_SHEET_NAME)
            st.code(str(exc))
        st.stop()

    if not senha_planilha:
        st.error("Senha não encontrada.")
        st.caption("A aba de senha deve conter as colunas: campo | valor. Exemplo: senha | 100.")
        st.stop()

    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Acesso ao app</div>', unsafe_allow_html=True)

    senha_digitada = st.text_input("Digite a senha", type="password")
    entrar = st.button("Entrar")

    st.markdown("</div>", unsafe_allow_html=True)

    if entrar:
        if str(senha_digitada).strip() == str(senha_planilha).strip():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    if not st.session_state.get("authenticated", False):
        st.stop()


def main_app():
    render_header()
    render_intro()

    try:
        services = load_services_from_sheet()
    except Exception as exc:
        st.error("Erro ao carregar os serviços da planilha.")
        with st.expander("Detalhes técnicos"):
            st.write("Aba de serviços:")
            st.code(SERVICES_SHEET_NAME)
            st.code(str(exc))
        st.stop()

    if not services:
        st.error("Nenhum serviço encontrado na aba de serviços.")
        st.stop()

    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Informações do atendimento</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        client_name = st.text_input("Nome da cliente", placeholder="Ex: Mariana")
        service_type = st.selectbox("Serviço realizado", services)

    with col2:
        observations = st.text_area(
            "Observações internas",
            placeholder="Ex: Cliente chegou com aparência de cansaço e tensão na região da mandíbula.",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Fotos para comparação</div>', unsafe_allow_html=True)

    col_before, col_after = st.columns(2)

    before_image = None
    after_image = None

    with col_before:
        before_file = st.file_uploader(
            "Foto antes da massagem",
            type=["jpg", "jpeg", "png"],
            key="before",
        )

        if before_file:
            before_image = prepare_image(before_file)
            st.image(before_image, caption="Antes da massagem", use_container_width=True)

    with col_after:
        after_file = st.file_uploader(
            "Foto depois da massagem",
            type=["jpg", "jpeg", "png"],
            key="after",
        )

        if after_file:
            after_image = prepare_image(after_file)
            st.image(after_image, caption="Depois da massagem", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    gerar = st.button("Gerar análise LIIVV")

    if gerar:
        if not client_name.strip():
            st.warning("Informe o nome da cliente.")
            st.stop()

        if before_image is None or after_image is None:
            st.warning("Envie a foto antes e a foto depois.")
            st.stop()

        with st.spinner("Analisando as imagens e gerando o relatório premium..."):
            try:
                report = analyze_with_gemini(
                    before_image=before_image,
                    after_image=after_image,
                    client_name=client_name,
                    service_type=service_type,
                    observations=observations,
                )

                save_result_to_sheet(
                    client_name=client_name,
                    service_type=service_type,
                    observations=observations,
                    report_text=report,
                )

            except Exception as exc:
                st.error("Erro ao gerar a análise.")
                with st.expander("Detalhes técnicos"):
                    st.code(str(exc))
                st.stop()

        st.success("Análise gerada com sucesso.")

        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(report)
        st.markdown("</div>", unsafe_allow_html=True)

        st.download_button(
            label="Baixar relatório em TXT",
            data=report,
            file_name=f"relatorio_liivv_face_relax_{client_name.strip().replace(' ', '_').lower()}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown(
        """
        <div class="empty-card">
            <p class="small-text">
                <span class="mini-label">Observação importante:</span>
                esta ferramenta realiza uma análise visual e estética. Ela não substitui avaliação médica,
                dermatológica, fisioterapêutica, psicológica ou qualquer diagnóstico profissional de saúde.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# EXECUÇÃO
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

check_password()
main_app()
