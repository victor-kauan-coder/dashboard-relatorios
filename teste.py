import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF
from datetime import date, datetime, timedelta
import optparse
import os
# --- CONFIGURA LOCALE ---
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except:
        pass

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Relatórios",
    layout="wide",
    page_icon="pet-logo.png" # Certifique-se que existe ou comente
)

st.markdown(
    """
    <style>
        div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        div[data-testid="stSidebarUserContent"] img { margin-top: -50px; }
    </style>
    """,
    unsafe_allow_html=True,
)

URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1PwDHHAD4ITWZoHuPpFVBE7t3kJy3Wxaw5APSVomBVOA/edit?usp=sharing"

try:
    st.sidebar.image("banner-pet.png", use_container_width=True)
except:
    st.sidebar.warning("Imagem banner-pet.png não encontrada.")
    
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            else:
                # Força o Python a olhar exatamente na mesma pasta deste script .py
                diretorio_atual = os.path.dirname(os.path.abspath(__file__))
                caminho_credenciais = os.path.join(diretorio_atual, "credentials.json")
                
                creds = Credentials.from_service_account_file(caminho_credenciais, scopes=scopes)
        except (StreamlitSecretNotFoundError, FileNotFoundError):
            st.error("Credenciais não encontradas.")
            return pd.DataFrame()

        client = gspread.authorize(creds)
        sheet = client.open_by_url(URL_DA_PLANILHA).sheet1
        all_values = sheet.get_all_values()

        if len(all_values) > 1:
            header = all_values[0]
            data = all_values[1:]
            dados = pd.DataFrame(data, columns=header)
            dados.columns = dados.columns.str.strip()

            if 'Data da atividade' in dados.columns:
                dados['Data da atividade'] = pd.to_datetime(
                    dados['Data da atividade'], errors='coerce', dayfirst=True
                )
                dados.dropna(subset=['Data da atividade'], inplace=True)

            if 'Horário de Início' in dados.columns:
                temp_time = pd.to_datetime(dados['Horário de Início'], errors='coerce')
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        else:
            return pd.DataFrame()
    except Exception:
        st.error("Erro ao carregar dados.")
        return pd.DataFrame()

# ==========================================
# FUNÇÕES DE PDF
# ==========================================
def limpar_texto(texto):
    if pd.isna(texto) or texto == "":
        return ""
    texto_str = str(texto)
    texto_str = texto_str.replace('–', '-').replace('—', '-').replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'").replace('•', '-')
    try:
        return texto_str.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return texto_str

def _desenhar_pagina(pdf, df_monitor, nome_monitor, mes, ano, preceptora, adicionar_visto_preceptor=False):
    """
    Desenha a página de um monitor.
    :param adicionar_visto_preceptor: Se True, adiciona a assinatura do preceptor no final.
    """
    meses_ptbr = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    try:
        pdf.set_font("Arial", 'B', 12)
        fonte_padrao = "Arial"
    except:
        pdf.set_font("Helvetica", 'B', 12)
        fonte_padrao = "Helvetica"

    # --- CABEÇALHO ---
    pdf.cell(0, 5, limpar_texto("UNIVERSIDADE FEDERAL DO PIAUÍ - UFPI"), ln=True, align='C') 
    pdf.cell(0, 5, limpar_texto("PROJETO PET SAÚDE/I&SD - INFORMAÇÃO E SAÚDE DIGITAL"), ln=True, align='C') 
    pdf.ln(5)
    pdf.cell(0, 7, limpar_texto("FOLHA DE FREQUÊNCIA"), ln=True, align='C') 
    pdf.ln(5)

    # --- METADADOS ---
    pdf.set_font(fonte_padrao, size=10)
    mes_idx = int(mes) - 1 if 1 <= int(mes) <= 12 else 0
    
    função = df_monitor.iloc[0]['Função'].upper()

    raw_funcao = df_monitor.iloc[0]['Função']

    # 2. Verifica se é Nulo (NaN), Vazio ou None
    if pd.isna(raw_funcao) or str(raw_funcao).strip() == "":
        função = 'MONITOR(A)'
    else:
        # 3. Se não for nulo, converte para string e joga para maiúsculo
        função = str(raw_funcao).upper()

    # Verifica se por acaso estava escrito "NAN" como texto na planilha
    if função == 'NAN': 
        função = 'MONITOR(A)'

    pdf.cell(0, 5, limpar_texto(f"MÊS DE REFERÊNCIA: {meses_ptbr[mes_idx].upper()} / {ano}"), ln=True) 
    pdf.cell(0, 5, limpar_texto("Grupo Tutorial: Grupo 1 - Letramento para Usuários dos Serviços Digitais do SUS"), ln=True)
    pdf.cell(0, 5, limpar_texto("Local de Atuação: CAPS AD - Teresina / PI"), ln=True)
    pdf.cell(0, 5, limpar_texto(f"Preceptora: {preceptora}"), ln=True)
    pdf.cell(0, 5, limpar_texto(f"{função}: {nome_monitor}"), ln=True)
    pdf.ln(5)

    # --- TABELA ---
    pdf.set_font(fonte_padrao, 'B', 8)
    w_data, w_ent, w_sai, w_ati = 25, 25, 25, 85
    
    pdf.cell(w_data, 7, limpar_texto("Data"), border=1, align='C')
    pdf.cell(w_ent, 7, limpar_texto("Horário de Entrada"), border=1, align='C')
    pdf.cell(w_sai, 7, limpar_texto("Horário de Saída"), border=1, align='C')
    pdf.cell(w_ati, 7, limpar_texto("Atividades Desenvolvidas"), border=1, align='C')
    pdf.ln()

    # --- DADOS ---
    pdf.set_font(fonte_padrao, size=8)
    if not df_monitor.empty:
        df_monitor = df_monitor.sort_values(by='Data da atividade')
    
    altura_linha_base = 5

    for _, row in df_monitor.iterrows():
        data = limpar_texto(row['Data da atividade'].strftime('%d/%m/%Y')) if not pd.isna(row['Data da atividade']) else ""
        
        entrada_str = str(row.get('Horário de Início', '')).strip()
        try:
            entrada_dt = datetime.strptime(entrada_str, "%H:%M")
            saida = (entrada_dt + timedelta(hours=4)).strftime("%H:%M")
        except ValueError:
            saida = ""
        
        entrada = limpar_texto(entrada_str)
        saida = limpar_texto(saida)
        
        raw_ativ = str(row.get('ATIVIDADE(S) REALIZADA(S)', ''))
        if raw_ativ.lower() == 'nan': raw_ativ = ''
        atividade_texto = limpar_texto(raw_ativ.upper())
        
        y_inicial = pdf.get_y()
        pdf.cell(w_data, altura_linha_base, data, border=0, align='C')
        pdf.cell(w_ent, altura_linha_base, entrada, border=0, align='C')
        pdf.cell(w_sai, altura_linha_base, saida, border=0, align='C')
        x_ati = pdf.get_x()
        pdf.multi_cell(w_ati, altura_linha_base, atividade_texto, border=1, align='L')
        y_final_ati = pdf.get_y()
        h_real = y_final_ati - y_inicial
        
        pdf.rect(pdf.l_margin, y_inicial, w_data, h_real)
        pdf.rect(pdf.l_margin + w_data, y_inicial, w_ent, h_real)
        pdf.rect(pdf.l_margin + w_data + w_ent, y_inicial, w_sai, h_real)
        pdf.set_y(y_final_ati)
        
        if pdf.get_y() > 260: 
             pdf.add_page()

    # --- RODAPÉ ---
    pdf.ln(10)
    pdf.set_font(fonte_padrao, size=10)
    pdf.cell(0, 5, limpar_texto("Observações:"), ln=True)
    pdf.cell(0, 5, "", border='B', ln=True)
    pdf.ln(15)
    
    # Assinatura do MONITOR (Sempre aparece na folha dele)
   

    pdf.cell(0, 5, limpar_texto(f"ASSINATURA DO {função}: _________________________________________ "), align='L')
    pdf.ln(15)
    
    # Assinatura do PRECEPTOR (Só aparece se for a última página do arquivo ou solicitado)
    if adicionar_visto_preceptor:
        hoje = date.today()

        # %d = dia com 2 dígitos
        # %m = mês com 2 dígitos
        # %Y = ano com 4 dígitos
        dia, mes_hj, ano_hj = hoje.strftime("%d"), hoje.strftime("%m"), hoje.strftime("%Y")
        # Adiciona um espaço extra para separar bem
        pdf.ln(10) 
        pdf.cell(0, 5, limpar_texto(f"VISTO DO PRECEPTOR (Consolidado): _________________________________________ DATA: {dia} / {mes_hj} / {ano_hj}"), align='L')


def gerar_pdf_monitores(df_geral, lista_nomes, mes, ano, col_nome_monitor='Nome'):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    qtd_monitores = len(lista_nomes)

    for i, nome in enumerate(lista_nomes):
        pdf.add_page()
        
        # Filtra dados
        df_indiv = df_geral[df_geral[col_nome_monitor] == nome].copy()
        
        # Verifica se é o ÚLTIMO monitor da lista para adicionar a assinatura do preceptor
        eh_o_ultimo = (i == qtd_monitores - 1)

        if not df_indiv.empty:
            precep = df_indiv['Nome do preceptor'].iloc[0] if 'Nome do preceptor' in df_indiv.columns else "______________"
            
            _desenhar_pagina(
                pdf, 
                df_indiv, 
                nome, 
                mes, 
                ano, 
                precep, 
                adicionar_visto_preceptor=eh_o_ultimo # AQUI ESTÁ A MÁGICA
            )
        else:
            pdf.cell(0, 10, limpar_texto(f"Sem dados para {nome}."), ln=True)

    saida = pdf.output(dest='S')
    if isinstance(saida, str):
        return saida.encode('latin-1')
    else:
        return bytes(saida)

# ==========================================
# INTERFACE
# ==========================================
st.title("📊 Dashboard de Relatórios e Presenças")
st.markdown("---")

df = carregar_dados()

if not df.empty:
    st.sidebar.header("Filtros:")
    monitores = sorted(df['Nome'].unique())
    monitor_selecionado = st.sidebar.multiselect("Selecione o(s) Monitor(es):", options=monitores, default=[])
    
    preceptores = sorted(df['Nome do preceptor'].unique())
    preceptor_selecionado = st.sidebar.multiselect("Selecione o(a) Preceptor(a):", options=preceptores, default=[])

    data_inicio, data_fim = None, None
    if 'Data da atividade' in df.columns:
        hoje = date.today()
        d_min = hoje.replace(day=1)
        sel_data = st.sidebar.date_input("Selecione o Período:", value=(d_min, hoje), format="DD/MM/YYYY")
        if isinstance(sel_data, tuple) and len(sel_data) == 2:
            data_inicio, data_fim = sel_data
        else:
            data_inicio, data_fim = d_min, hoje
        st.sidebar.write(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")

    # Filtros
    df_filtrado = df.copy()
    if monitor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome'].isin(monitor_selecionado)]
    if preceptor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do preceptor'].isin(preceptor_selecionado)]
    if data_inicio and data_fim:
        df_filtrado = df_filtrado[(df_filtrado['Data da atividade'].dt.date >= data_inicio) & (df_filtrado['Data da atividade'].dt.date <= data_fim)]

    # ==========================================
    # BOTÃO DE DOWNLOAD (CORRIGIDO)
    # ==========================================
    # Verifica se há monitores selecionados e se há dados filtrados
    if monitor_selecionado and not df_filtrado.empty:
        st.sidebar.markdown("---")
        st.sidebar.write(f"📑 **Gerar PDF para {len(monitor_selecionado)} monitor(es)**")
        
        d_ini_str = df_filtrado['Data da atividade'].min().strftime('%d-%m')
        d_fim_str = df_filtrado['Data da atividade'].max().strftime('%d-%m')
        mes_ref = df_filtrado['Data da atividade'].iloc[-1].month
        ano_ref = df_filtrado['Data da atividade'].iloc[-1].year

        try:
            # Gera o PDF diretamente
            pdf_bytes = gerar_pdf_monitores(
                df_geral=df_filtrado, 
                lista_nomes=monitor_selecionado, 
                mes=mes_ref, 
                ano=ano_ref
            )
            
            nome_arquivo = f"Frequencia_{len(monitor_selecionado)}_Monitores_{d_ini_str}_a_{d_fim_str}.pdf"
            
            # Botão aparece diretamente (sem o if st.button anterior)
            st.sidebar.download_button(
                label="📥 Baixar PDF (Assinatura Única no Final)",
                data=pdf_bytes,
                file_name=nome_arquivo,
                mime="application/pdf"
            )
        except Exception as e:
            st.sidebar.error(f"Erro: {e}")

    elif monitor_selecionado:
        st.sidebar.info("Sem dados neste período.")

    # # Tabela e Detalhes (Mantido igual)
    # st.header(f"Relatórios Encontrados: {len(df_filtrado)}")
    # st.dataframe(df_filtrado)
    # st.markdown("---")

    st.header("Visualizar Relatório Detalhado")
    st.subheader(f"Relatórios Encontrados: {len(df_filtrado)}")
    df_detalhes = df_filtrado.sort_values(by='Data da atividade', ascending=False)
    
    if not df_detalhes.empty:
        # Cria a lista de opções para o selectbox
        opcoes = [f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome']}" for _, row in df_detalhes.iterrows()]
        escolha = st.selectbox("Selecione um relatório para ler os detalhes:", options=opcoes)

        if escolha:
            idx = opcoes.index(escolha)
            id_real = df_detalhes.index[idx]
            rel = df.loc[id_real]
            
            # Cabeçalho do Relatório
            st.subheader(f"Relatório de: {rel['Nome']}")
            st.markdown(f"**Data:** {rel['Data da atividade'].strftime('%d/%m/%Y')} | **Preceptor(a):** {rel.get('Nome do preceptor', '')}")
            
            # Espaçamento
            st.write("") 

            # --- AQUI ESTÁ A MUDANÇA PARA O FORMATO DA IMAGEM 2 ---
            
            # Bloco 1: Atividade
            with st.expander(" Atividade(s) Realizada(s)", expanded=False):
                texto_atividade = rel.get('ATIVIDADE(S) REALIZADA(S)', '')
                if not texto_atividade:
                    texto_atividade = "Não informado."
                st.write(texto_atividade)
            # Bloco 2: Objetivo
            with st.expander("Objetivo Da(s) Atividade(s)", expanded=False):
                texto_atividade = rel.get('OBJETIVO DA(S) ATIVIDADE(S)', '')
                if not texto_atividade:
                    texto_atividade = "Não informado."
                st.write(texto_atividade)
            # Bloco 3: Relato
            with st.expander(" Relato com Fundamentação Teórica", expanded=False):
                texto_relato = rel.get('RELATO FUNDAMENTADO', '')
                if not texto_relato:
                    texto_relato = "Não informado."
                st.write(texto_relato)
            # Bloco 4: reflexões    
            with st.expander(" Reflexões Críticas", expanded=False):
                texto_relato = rel.get('REFLEXÕES CRÍTICAS', '')
                if not texto_relato:
                    texto_relato = "Não informado."
                st.write(texto_relato)
            # Bloco 3: Reflexões (Caso exista essa coluna na sua planilha, se não existir, pode remover este bloco)
            coluna_reflexao = 'Reflexões Críticas' # Verifique se o nome na planilha é exatamente este
            if coluna_reflexao in rel:
                with st.expander("v Reflexões Críticas", expanded=False):
                     st.write(rel.get(coluna_reflexao, ''))

    else:
        st.warning("Nenhum relatório encontrado para os filtros selecionados.")
else:
    st.warning("Verifique a planilha e credenciais.")