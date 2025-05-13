
import streamlit as st
import fitz
from supabase import create_client, Client
from datetime import datetime
from docx import Document
from docx.shared import Pt
from io import BytesIO
import unicodedata

SUPABASE_URL = "https://syrznbowqhvooxwzikhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...YoU"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

secoes_lab = {
    "Bioquímica": ["glicose", "ureia", "creatinina", "potassio", "sodio", "calcio", "fosforo", "clearance", "transferrina"],
    "Hematologia": ["hemoglobina", "hematocrito", "vcm", "hcm", "leucocitos", "plaquetas"],
    "Hormônios": ["tsh", "t4", "t3", "pth", "paratormonio"],
    "Vitaminas e Metabolismo Mineral": ["vitamina", "b12", "acido folico", "25-oh", "calcidiol", "calcitriol"],
    "Glicada / Diabetes": ["glicada", "a1c", "hemoglobina glicada"]
}

def remover_acentos(txt):
    return unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').decode('ASCII')

def extrair_texto(pdf_file):
    texto = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            texto += page.get_text()
    return texto

def classificar_exames(texto):
    linhas = remover_acentos(texto.lower()).splitlines()
    dados = {secao: [] for secao in secoes_lab}
    dados["Outros"] = []
    for linha in linhas:
        l = linha.strip()
        if not l or len(l) < 4: continue
        adicionou = False
        for secao, termos in secoes_lab.items():
            if any(t in l for t in termos):
                dados[secao].append(l.capitalize())
                adicionou = True
                break
        if not adicionou and ":" in l:
            dados["Outros"].append(l.capitalize())
    return dados

def gerar_docx_laboratorial(nome, data, dados):
    doc = Document()
    doc.add_heading("Relatório de Exames Laboratoriais", 0)
    p1 = doc.add_paragraph()
    run1 = p1.add_run(f"Paciente: {nome}")
    run1.bold = True
    run1.font.size = Pt(11)
    p2 = doc.add_paragraph()
    run2 = p2.add_run(f"Data da coleta: {data}")
    run2.font.size = Pt(10)
    doc.add_paragraph("")

    for secao, itens in dados.items():
        if itens:
            doc.add_heading(secao, level=1)
            for item in itens:
                try:
                    texto_limpo = "".join(c for c in item if 32 <= ord(c) <= 126 or c in "
	 .,:-_/()[]%")
                    doc.add_paragraph(texto_limpo.strip(), style="List Bullet")
                except Exception:
                    doc.add_paragraph("Erro ao processar item.", style="List Bullet")
            doc.add_paragraph("-" * 40)

    output = BytesIO()
    doc.save(output)
    return output.getvalue()

def gerar_docx_imagem(nome, data, texto):
    doc = Document()
    doc.add_heading(f"Laudo de Imagem – {nome}", 0)
    doc.add_paragraph(f"Data do exame: {data}")
    for linha in texto.splitlines():
        if linha.strip():
            doc.add_paragraph(linha.strip())
    output = BytesIO()
    doc.save(output)
    return output.getvalue()

st.title("Aplicativo de Laudos – Dr. João Batista Zinato")

with st.form("formulario"):
    tipo = st.radio("Tipo de exame", ["Exame Laboratorial", "Exame de Imagem"])
    nome = st.text_input("Nome do paciente")
    cpf = st.text_input("CPF")
    data = st.date_input("Data do exame")
    arquivo_pdf = st.file_uploader("Envie o PDF do laudo", type="pdf")
    enviar = st.form_submit_button("Processar")

if enviar and arquivo_pdf:
    texto = extrair_texto(arquivo_pdf)
    dados_supabase = {
        "nome": nome or "",
        "cpf": cpf or "",
        "data_nasc": "",
        "data_laudo": datetime.now().isoformat(),
        "conteudo": texto or ""
    }

    try:
        supabase.table("laudos").insert(dados_supabase).execute()
    except Exception:
        st.error("Erro ao salvar no Supabase.")
        st.stop()

    if tipo == "Exame Laboratorial":
        dados = classificar_exames(texto)
        docx_file = gerar_docx_laboratorial(nome, str(data), dados)
    else:
        docx_file = gerar_docx_imagem(nome, str(data), texto)

    st.success("Relatório gerado com sucesso.")
    st.download_button("Baixar relatório", docx_file, file_name="relatorio.docx")
