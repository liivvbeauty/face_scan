import json
import datetime
from io import BytesIO

import streamlit as st
from PIL import Image

import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="LIIVV Face Relax Scanner",
    page_icon="✨",
    layout="wide"
)


# =========================================================
# ESTILO VISUAL LIIVV
# =========================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #F8F4EF;
        }

        .main-title {
            font-size: 38px;
            font-weight: 700;
            color: #3B2A25;
            margin-bottom: 4px;
        }

        .subtitle {
            font-size: 18px;
            color: #6B5C55;
            margin-bottom: 28px;
        }

        .liivv-box {
            background: #FFFFFF;
            padding: 24px;
            border-radius: 20px;
            border: 1px solid #E7DDD3;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 20px;
        }

        .small-note {
            color: #7A6A61;
            font-size: 13px;
            margin-top: 20px;
        }

        div.stButton > button {
            background-color: #3B2A25;
            color: white;
            border-radius: 12px;
            height: 48px;
            font-weight: 600;
            border: none;
        }

        div.stButton > button:hover {
            background-color: #5A4038;
            color: white;
            border: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CONEXÃO GOOGLE SHEETS
# =========================================================

def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    sheet_id = st.secrets["GOOGLE_SHEET_ID"]

    return client.open_by_key(sheet_id)


@st.cache_data(ttl=60)
def get_password_from_sheet():
    spreadsheet = get_google_sheet()
    worksheet = spreadsheet.sheet1

    records = worksheet.get_all_records()

    for row in records:
        campo = str(row.get("campo", "")).strip().lower()
        valor = str(row.get("valor", "")).strip()

        if campo == "senha":
            return valor

    return None


# =========================================================
# AUTENTICAÇÃO
# =========================================================

def check_password():
    st.markdown('<div class="main-title">LIIVV Face Relax Scanner</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Análise visual de relaxamento facial antes e depois da massagem.</div>',
        unsafe_allow_html=True
    )

    try:
        senha_planilha = get_password_from_sheet()
    except Exception as e:
        st.error("Erro ao acessar a senha na planilha.")
        st.info("Verifique se o Google Sheet foi compartilhado com o e-mail da service account.")
        st.exception(e)
        st.stop()

    if not senha_planilha:
        st.error("Senha não encontrada na planilha.")
        st.info("A primeira aba deve conter as colunas: campo | valor. E uma linha: senha | 100.")
        st.stop()

    with st.container():
        st.markdown('<div class="liivv-box">', unsafe_allow_html=True)

        senha_digitada = st.text_input(
            "Digite a senha de acesso",
            type="password",
            placeholder="Senha"
        )

        entrar = st.button("Entrar", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    if entrar:
        if str(senha_digitada).strip() == str(senha_planilha).strip():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    if not st.session_state.get("authenticated", False):
        st.stop()


# =========================================================
# IMAGENS
# =========================================================

def prepare_image(uploaded_file):
    image = Image.open(uploaded_file).convert("RGB")

    max_size = 1600
    image.thumbnail((max_size, max_size))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)

    return image


# =========================================================
# GEMINI
# =========================================================

def configure_gemini():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")


def analyze_with_gemini(
    before_image,
    after_image,
    client_name,
    service_type,
    observations
):
    model = configure_gemini()

    prompt = f"""
Você é uma consultora premium da LIIVV Beauty, especializada em bem-estar facial,
massagem relaxante, imagem pessoal e percepção visual de descanso.

Você receberá duas imagens:
1. Foto ANTES da massagem
2. Foto DEPOIS da massagem

Cliente: {client_name}
Serviço realizado: {service_type}
Observações internas da profissional: {observations}

IMPORTANTE:
- Faça uma análise visual, estética e não médica.
- Não use linguagem clínica.
- Não diga que diagnosticou nada.
- Não prometa resultado permanente.
- Não afirme idade, condição de saúde, doença ou estado psicológico.
- Use linguagem sofisticada, acolhedora e adequada a um salão premium.
- Compare apenas sinais visuais percebidos nas imagens.

Analise visualmente:

1. Aparência geral de cansaço facial
2. Região dos olhos
3. Testa e linhas associadas à tensão
4. Mandíbula e expressão facial
5. Simetria visual percebida
6. Expressão geral de relaxamento
7. Aparência de bem-estar

Crie scores de 0 a 100:

- Fadiga facial antes
- Fadiga facial depois
- Relaxamento facial antes
- Relaxamento facial depois
- Tensão mandibular antes
- Tensão mandibular depois
- Expressão de bem-estar antes
- Expressão de bem-estar depois
- Wellness Face Score antes
- Wellness Face Score depois

Formato obrigatório da resposta:

# LIIVV Face Relax Report

## Resumo executivo
Texto curto e sofisticado.

## Comparativo de scores
Tabela em markdown com:
Indicador | Antes | Depois | Evolução percebida

## Principais mudanças percebidas
Lista objetiva.

## Pontos de maior evolução
Lista objetiva.

## Leitura por região facial
### Olhos
### Testa
### Mandíbula
### Expressão geral

## Recomendação de continuidade
Sugira próximos cuidados dentro do salão, como massagem relaxante, quick massage,
drenagem facial ou ritual de relaxamento, sem linguagem médica.

## Mensagem curta para a cliente
Texto curto, bonito e compartilhável.

## Observação importante
Informe que esta é uma análise visual, estética e não médica.
"""

    response = model.generate_content(
        [
            prompt,
            before_image,
            after_image
        ]
    )

    return response.text


# =========================================================
# SALVAR RESULTADO NA PLANILHA
# =========================================================

def save_result_to_sheet(client_name, service_type, observations, report_text):
    spreadsheet = get_google_sheet()

    try:
        worksheet = spreadsheet.worksheet("resultados")
    except Exception:
        worksheet = spreadsheet.add_worksheet(
            title="resultados",
            rows=1000,
            cols=20
        )
        worksheet.append_row([
            "data_hora",
            "cliente",
            "servico",
            "observacoes",
            "relatorio"
        ])

    worksheet.append_row([
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        client_name,
        service_type,
        observations,
        report_text
    ])


# =========================================================
# APP PRINCIPAL
# =========================================================

def main_app():
    st.markdown('<div class="main-title">LIIVV Face Relax Scanner</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Compare o antes e depois da massagem por meio de uma análise visual de relaxamento facial.</div>',
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown('<div class="liivv-box">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input(
                "Nome da cliente",
                placeholder="Ex: Mariana"
            )

            service_type = st.selectbox(
                "Serviço realizado",
                [
                    "Massagem relaxante",
                    "Massagem terapêutica",
                    "Quick massage",
                    "Massagem facial",
                    "Drenagem linfática",
                    "Ritual de relaxamento LIIVV",
                    "Outro"
                ]
            )

        with col2:
            observations = st.text_area(
                "Observações internas",
                placeholder="Ex: Cliente chegou com aparência de cansaço e tensão na região da mandíbula."
            )

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Fotos para comparação")

    col_before, col_after = st.columns(2)

    before_image = None
    after_image = None

    with col_before:
        before_file = st.file_uploader(
            "Foto antes da massagem",
            type=["jpg", "jpeg", "png"],
            key="before"
        )

        if before_file:
            before_image = prepare_image(before_file)
            st.image(before_image, caption="Antes da massagem", use_container_width=True)

    with col_after:
        after_file = st.file_uploader(
            "Foto depois da massagem",
            type=["jpg", "jpeg", "png"],
            key="after"
        )

        if after_file:
            after_image = prepare_image(after_file)
            st.image(after_image, caption="Depois da massagem", use_container_width=True)

    st.markdown("---")

    gerar = st.button("Gerar análise LIIVV", use_container_width=True)

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
                    observations=observations
                )

                save_result_to_sheet(
                    client_name=client_name,
                    service_type=service_type,
                    observations=observations,
                    report_text=report
                )

            except Exception as e:
                st.error("Erro ao gerar a análise.")
                st.exception(e)
                st.stop()

        st.success("Análise gerada com sucesso.")

        st.markdown("## Relatório gerado")
        st.markdown(report)

        file_name = f"relatorio_liivv_face_relax_{client_name.strip().replace(' ', '_').lower()}.txt"

        st.download_button(
            label="Baixar relatório em TXT",
            data=report,
            file_name=file_name,
            mime="text/plain",
            use_container_width=True
        )

    st.markdown(
        """
        <p class="small-note">
        Esta ferramenta realiza uma análise visual e estética. Ela não substitui avaliação médica,
        dermatológica, fisioterapêutica, psicológica ou qualquer diagnóstico profissional de saúde.
        </p>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# EXECUÇÃO
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

check_password()
main_app()
