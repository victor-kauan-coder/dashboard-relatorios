import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF
from datetime import date, datetime, timedelta
import os
import plotly.graph_objects as go
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import re

# --- CONFIGURAÇÃO DE IDIOMA ---
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except:
        pass

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="PET Saúde · Gestão Integrada",
    layout="wide",
    page_icon="pet-logo.png",
    initial_sidebar_state="expanded"
)

# ==========================================
# DESIGN SYSTEM (CSS)
# ==========================================
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Sora:wght@300;400;600;700&display=swap');

:root {
    --bg-base:        var(--background-color);
    --bg-surface:     var(--secondary-background-color);
    --bg-elevated:    var(--secondary-background-color);
    --border:         rgba(150, 150, 150, 0.2);
    --border-active:  #E8762A;
    --text-primary:   var(--text-color);
    --accent:         #E8762A;
    --accent-light:   #FFAA70;
    --accent-dim:     rgba(232,118,42,0.12);
    --accent2:        #2A6AE8;
    --accent2-light:  #6A9FFF;
    --accent2-dim:    rgba(42,106,232,0.12);
    --font-display:   'Sora', sans-serif;
    --font-body:      'Plus Jakarta Sans', sans-serif;
    --radius-sm:      6px;
    --radius-md:      12px;
    --transition:     all 0.2s cubic-bezier(0.4,0,0.2,1);
}

.stApp, .stApp > header {
    font-family: var(--font-body) !important;
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
}
.block-container { padding: 1.75rem 2.25rem 4rem !important; max-width: 1440px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebarUserContent"] { padding-top: 0 !important; }
[data-testid="stSidebar"] label {
    color: var(--text-primary) !important;
    opacity: 0.8 !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
}

/* User Profile Card */
.user-profile-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    margin-bottom: 12px;
}
.user-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1.1rem;
    font-family: var(--font-display);
    flex-shrink: 0;
}
.user-info { display: flex; flex-direction: column; overflow: hidden; }
.user-name { font-weight: 600; font-size: 0.85rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: 0.65rem; color: var(--text-primary); opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; }

/* Buttons & Elements */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-light) 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    padding: 0.6rem 1.1rem !important;
    width: 100% !important;
    box-shadow: 0 3px 14px rgba(232,118,42,0.3) !important;
}

[data-testid="stExpander"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
}

hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# COMPONENTES VISUAIS
# ==========================================
def sidebar_divider():
    st.sidebar.markdown("<div style='height:1px;background:var(--border);margin:0.8rem 0;'></div>", unsafe_allow_html=True)

def section_label(text):
    st.markdown(f"""<p style="font-size:0.62rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-primary);opacity:0.5;margin:1.75rem 0 0.85rem;padding-bottom:0.55rem;border-bottom:1px solid var(--border);">{text}</p>""", unsafe_allow_html=True)

def page_header(title, subtitle):
    st.markdown(f"""
<div style="padding:1.5rem 0 1.25rem;margin-bottom:0.25rem;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:1.1rem;">
    <div style="width:3px;height:52px;background:linear-gradient(180deg,var(--accent) 0%,var(--accent2) 100%);border-radius:2px;flex-shrink:0;margin-top:3px;"></div>
    <div>
        <p style="margin:0 0 0.12rem;font-family:'Sora',sans-serif;font-size:0.6rem;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;color:var(--accent);">UFPI · PET SAÚDE / I&SD</p>
        <h1 style="margin:0 0 0.25rem;font-family:'Sora',sans-serif;font-size:1.75rem;font-weight:700;color:var(--text-primary);line-height:1.15;letter-spacing:-0.02em;">{title}</h1>
        <p style="margin:0;font-size:0.77rem;color:var(--text-primary);opacity:0.8;font-weight:300;">{subtitle}</p>
    </div>
</div>""", unsafe_allow_html=True)

def metric_card(label, value, sub, variant="default"):
    color = "var(--accent)" if variant == "orange" else ("var(--accent2)" if variant == "blue" else "var(--border)")
    bg = "var(--accent-dim)" if variant == "orange" else ("var(--accent2-dim)" if variant == "blue" else "var(--bg-surface)")
    return f"""
<div style="background:{bg};border:1px solid {color};border-top:3px solid {color};border-radius:12px;padding:1.1rem 1.25rem 1rem;box-shadow:0 2px 12px rgba(0,0,0,0.05);height:100%;">
    <p style="margin:0 0 0.5rem;font-size:0.6rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;opacity:0.6;">{label}</p>
    <p style="margin:0 0 0.2rem;font-family:'Sora',sans-serif;font-size:2rem;font-weight:700;color:{color};line-height:1;">{value}</p>
    <p style="margin:0;font-size:0.7rem;opacity:0.7;font-weight:300;">{sub}</p>
</div>"""

def report_card(row):
    data_fmt = row['Data da atividade'].strftime('%d/%m/%Y')
    ativ = str(row.get('ATIVIDADE(S) REALIZADA(S)', '') or 'Não informado.')
    if len(ativ) > 110: ativ = ativ[:110] + "..."
    st.markdown(f"""
<div style="background:var(--bg-surface);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.4rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;">
        <span style="font-family:'Sora',sans-serif;font-size:0.8rem;font-weight:600;">{row['Nome']}</span>
        <span style="background:var(--accent-dim);border:1px solid var(--accent);color:var(--accent);font-size:0.64rem;font-weight:700;padding:0.17rem 0.52rem;border-radius:4px;">{data_fmt}</span>
    </div>
    <p style="margin:0;font-size:0.73rem;opacity:0.8;line-height:1.55;font-weight:300;">{ativ}</p>
</div>""", unsafe_allow_html=True)


# ==========================================
# GRÁFICOS (PLOTLY)
# ==========================================
def base_layout(h=220):
    return dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=8, r=8, t=24, b=8), height=h)

def chart_barras(df):
    cont = df.groupby('Nome').size().reset_index(name='N').sort_values('N', ascending=True)
    fig = go.Figure(go.Bar(x=cont['N'], y=cont['Nome'], orientation='h', marker=dict(color=cont['N'], colorscale=[[0, "rgba(42,106,232,0.3)"], [0.5, "#2A6AE8"], [1, "#E8762A"]])))
    fig.update_layout(**base_layout(h=max(180, len(cont) * 44)), showlegend=False)
    return fig

def chart_linha(df):
    por = df.groupby(df['Data da atividade'].dt.date).size().reset_index(name='N')
    fig = go.Figure(go.Scatter(x=por['Data da atividade'], y=por['N'], mode='lines+markers', line=dict(color="#E8762A", width=2.5, shape='spline'), fill='tozeroy', fillcolor="rgba(232,118,42,0.12)"))
    fig.update_layout(**base_layout(h=200), showlegend=False)
    return fig

def chart_donut(df):
    if 'Função' not in df.columns: return None
    cont = df['Função'].value_counts().reset_index()
    fig = go.Figure(go.Pie(labels=cont['Função'], values=cont['count'], hole=0.58, marker=dict(colors=["#E8762A", "#2A6AE8", "#3DB87A"])))
    fig.update_layout(**base_layout(h=230), legend=dict(orientation='h', y=-0.2, x=0.5, xanchor='center'))
    return fig


# ==========================================
# GESTÃO DE PDF (ESTRITO PRETO E BRANCO)
# ==========================================
def limpar_texto(texto):
    if pd.isna(texto) or texto == "": return ""
    s = str(texto)
    subs = {'\u2013':'-','\u2014':'-','\u201c':'"','\u201d':'"','\u2018':"'",'\u2019':"'",'\u2022':'-','\u00e3':'a','\u00e7':'c','\u00e9':'e','\u00ea':'e','\u00f5':'o','\u00fc':'u','\u00e1':'a','\u00ed':'i','\u00f3':'o','\u00fa':'u','\u00c3':'A','\u00c7':'C','\u00e0':'a','\u00e2':'a','\u00f4':'o','\u00f2':'o'}
    for k, v in subs.items(): s = s.replace(k, v)
    try: return s.encode('latin-1', 'replace').decode('latin-1')
    except: return s

def _pagina_pdf(pdf, df_m, nome, mes, ano, prec, visto=False):
    meses = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    pdf.set_draw_color(0, 0, 0); pdf.set_text_color(0, 0, 0)
    
    y_l = 12; h_l = 14; px = [18, 58, 88, 132, 175]
    imgs = ["ufpi.png", "sus.png", "pet.png", "fms.png", "caps.png"]
    for x, img in zip(px, imgs):
        if os.path.exists(img):
            try: pdf.image(img, x=x, y=y_l, h=h_l)
            except: pass
                
    pdf.set_y(30); pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 6, limpar_texto("UNIVERSIDADE FEDERAL DO PIAUI - UFPI"), ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, limpar_texto("PROJETO PET SAUDE / I&SD - INFORMACAO E SAUDE DIGITAL"), ln=True, align='C')
    pdf.ln(2); pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3); pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, limpar_texto("FOLHA DE FREQUENCIA"), ln=True, align='C')
    
    pdf.ln(3); mes_idx = int(mes) - 1 if 1 <= int(mes) <= 12 else 0
    fnc = str(df_m.iloc[0]['Função']).upper() if not pd.isna(df_m.iloc[0]['Função']) else "MONITOR(A)"
    if fnc == 'NAN' or fnc == '': fnc = "MONITOR(A)"
    
    for lbl, val in [("MES DE REFERENCIA", f"{meses[mes_idx].upper()} / {ano}"), ("GRUPO TUTORIAL", "Grupo 1 - Letramento p/ Usuarios SUS"), ("LOCAL", "CAPS AD - Teresina / PI"), ("PRECEPTORA", prec), (fnc, nome)]:
        pdf.set_font("Helvetica", 'B', 8); pdf.cell(44, 5, limpar_texto(f"  {lbl}:"), border=0)
        pdf.set_font("Helvetica", '', 8);  pdf.cell(0, 5, limpar_texto(val), border=0, ln=True)

    pdf.ln(4); ws = [28, 28, 28, 86]
    pdf.set_fill_color(220, 220, 220); pdf.set_font("Helvetica", 'B', 8)
    for h, w in zip(["Data", "Entrada", "Saida", "Atividades Desenvolvidas"], ws): pdf.cell(w, 8, limpar_texto(h), border=1, align='C', fill=True)
    pdf.ln(); pdf.set_font("Helvetica", '', 8)
    
    flip = False
    for _, row in df_m.sort_values('Data da atividade').iterrows():
        d = row['Data da atividade'].strftime('%d/%m/%Y'); ent = str(row.get('Horário de Início', '')).strip()
        try: sai = (datetime.strptime(ent, "%H:%M") + timedelta(hours=4)).strftime("%H:%M")
        except: sai = ""
        ativ = limpar_texto(str(row.get('ATIVIDADE(S) REALIZADA(S)', '')).upper())

        pdf.set_fill_color(245, 245, 245) if flip else pdf.set_fill_color(255, 255, 255)
        flip = not flip
        y0 = pdf.get_y()
        pdf.cell(ws[0], 5, d, border=0, align='C', fill=True)
        pdf.cell(ws[1], 5, ent, border=0, align='C', fill=True)
        pdf.cell(ws[2], 5, sai, border=0, align='C', fill=True)
        pdf.multi_cell(ws[3], 5, ativ, border=1, align='L', fill=True)
        y1 = pdf.get_y(); h_r = y1 - y0
        pdf.rect(pdf.l_margin, y0, ws[0], h_r); pdf.rect(pdf.l_margin+ws[0], y0, ws[1], h_r); pdf.rect(pdf.l_margin+ws[0]+ws[1], y0, ws[2], h_r)
        pdf.set_y(y1)
        if pdf.get_y() > 255: pdf.add_page()

    pdf.ln(8); pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 5, limpar_texto(f"Assinatura do {fnc}: _________________________________________________"), ln=True)
    if visto:
        pdf.ln(10); pdf.cell(0, 5, limpar_texto(f"Visto do Preceptor (Consolidado): ____________________________  Data: {date.today().strftime('%d/%m/%Y')}"), ln=True)

def gerar_pdf(df_geral, nomes, mes, ano):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15)
    for i, nome in enumerate(nomes):
        pdf.add_page(); df_i = df_geral[df_geral['Nome'] == nome].copy()
        prec = df_i['Nome do preceptor'].iloc[0] if 'Nome do preceptor' in df_i.columns and not df_i.empty else "___"
        _pagina_pdf(pdf, df_i, nome, mes, ano, prec, visto=(i == len(nomes)-1))
    return bytes(pdf.output(dest='S'))


# ==========================================
# GESTÃO DE DADOS (GOOGLE SHEETS)
# ==========================================
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1PwDHHAD4ITWZoHuPpFVBE7t3kJy3Wxaw5APSVomBVOA/edit?usp=sharing"

@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_service_account_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json"), scopes=scopes)
        client = gspread.authorize(creds)
        vals = client.open_by_url(URL_PLANILHA).sheet1.get_all_values()
        
        if len(vals) <= 1: return pd.DataFrame()
        
        dados = pd.DataFrame(vals[1:], columns=vals[0])
        dados.columns = dados.columns.str.strip()
        
        if 'Data da atividade' in dados.columns:
            dados['Data da atividade'] = pd.to_datetime(dados['Data da atividade'], errors='coerce', dayfirst=True)
        if 'Horário de Início' in dados.columns:
            limpos = dados['Horário de Início'].astype(str).str.extract(r'(\d{1,2}:\d{2})')[0]
            dados['Horário de Início'] = pd.to_datetime(limpos, format='%H:%M', errors='coerce').dt.strftime('%H:%M')
            
        return dados.dropna(subset=['Data da atividade'])
    except Exception as e:
        st.error(f"Erro ao carregar banco de dados: {e}"); return pd.DataFrame()

def salvar_nova_atividade(lista):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        gspread.authorize(creds).open_by_url(URL_PLANILHA).sheet1.append_row(lista)
        return True
    except: return False

def atualizar_atividade(carimbo, nome, nova_linha):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        client = gspread.authorize(creds)
        planilha = client.open_by_url(URL_PLANILHA).sheet1

        registros = planilha.get_all_values()
        row_idx = -1
        for i, r in enumerate(registros):
            if r[0] == carimbo and r[1] == nome:
                row_idx = i + 1
                break

        if row_idx != -1:
            planilha.update(range_name=f"A{row_idx}:O{row_idx}", values=[nova_linha])
            return True
        return False
    except Exception as e:
        st.error(f"Erro na comunicação com o banco: {e}")
        return False


# ==========================================
# CONTROLE DE ACESSO (AUTHENTICATION)
# ==========================================
inject_css()

# Tenta ler o arquivo local. Se não existir, lê dos Secrets do Streamlit Cloud
if "credentials" in st.secrets:
    config = {
        "credentials": dict(st.secrets["credentials"]),
        "cookie": dict(st.secrets["cookie"])
    }
else:
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        st.error("Configurações não encontradas. Verifique o arquivo config.yaml ou os Secrets.")
        st.stop()

auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if st.session_state["authentication_status"] is None or st.session_state["authentication_status"] is False:
    st.markdown("<div style='margin-top: 5rem;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div style='text-align:center; margin-bottom: 2rem;'>", unsafe_allow_html=True)
        try: st.image("pet-logo.png", width=180)
        except: st.markdown("<h2 style='color:var(--accent);'>Acesso Restrito</h2>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        auth.login()
        if st.session_state["authentication_status"] is False: st.error('Credenciais inválidas.')


# ==========================================
# ÁREA LOGADA (SISTEMA DE ROTAS)
# ==========================================
if st.session_state["authentication_status"]:
    user_key = st.session_state["username"]
    user_data = config['credentials']['usernames'][user_key]
    role = user_data.get('role', 'monitor')
    
    # 1. LOGO NO TOPO DA SIDEBAR
    try:
        st.sidebar.image("banner-pet.png", use_container_width=True)
    except:
        st.sidebar.markdown("<h3 style='text-align:center; color:var(--accent); margin-top:0;'>PET SAÚDE</h3>", unsafe_allow_html=True)
        
    sidebar_divider()

    # ---------------------------------------------------------
    # ROTA: ADMINISTRADOR
    # ---------------------------------------------------------
    if role == 'admin':
        df = carregar_dados()
        if not df.empty:
            st.sidebar.markdown("<p style='font-size:0.6rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-primary);opacity:0.5;'>FILTROS</p>", unsafe_allow_html=True)
            
            # FILTRO 1: Monitores
            m_sel = st.sidebar.multiselect("Filtrar Monitores", options=sorted(df['Nome'].unique()))
            
            # FILTRO 2: Preceptores
            lista_preceptores = []
            if 'Nome do preceptor' in df.columns:
                # Extrai apenas preceptores válidos (ignora vazios, nulos ou 'Escolher')
                lista_preceptores = sorted([p for p in df['Nome do preceptor'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan" and str(p).lower() != "escolher"])
            
            p_sel = st.sidebar.multiselect("Filtrar Preceptores", options=lista_preceptores)
            
            # FILTRO 3: Período
            hoje = date.today(); sel_d = st.sidebar.date_input("Período", value=(hoje.replace(day=1), hoje))
            d1, d2 = sel_d if (isinstance(sel_d, tuple) and len(sel_d)==2) else (hoje, hoje)

            df_f = df.copy()
            
            # Aplicação dos Filtros
            if m_sel: 
                df_f = df_f[df_f['Nome'].isin(m_sel)]
            if p_sel:
                df_f = df_f[df_f['Nome do preceptor'].isin(p_sel)]
                
            df_f = df_f[(df_f['Data da atividade'].dt.date >= d1) & (df_f['Data da atividade'].dt.date <= d2)]

            if m_sel and not df_f.empty:
                sidebar_divider()
                st.sidebar.markdown("<p style='font-size:0.6rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-primary);opacity:0.5;'>EXPORTAR PDF</p>", unsafe_allow_html=True)
                pdf_b = gerar_pdf(df_f, m_sel, df_f['Data da atividade'].iloc[-1].month, df_f['Data da atividade'].iloc[-1].year)
                st.sidebar.download_button(f"Baixar Frequências ({len(m_sel)})", pdf_b, f"Frequencias_PET.pdf", "application/pdf")

            page_header("Painel de Gestão", "Monitoramento centralizado de atividades e frequências do grupo tutorial.")
            
            section_label("Métricas do Período")
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.markdown(metric_card("Total Registros", len(df_f), "atividades enviadas", "orange"), unsafe_allow_html=True)
            with k2: st.markdown(metric_card("Monitores Ativos", df_f['Nome'].nunique(), "participantes únicos", "blue"), unsafe_allow_html=True)
            with k3: st.markdown(metric_card("Horas Totais", f"{len(df_f)*4}h", "base: 4h por registro"), unsafe_allow_html=True)
            with k4: st.markdown(metric_card("Preceptores", df_f['Nome do preceptor'].nunique(), "responsáveis validados"), unsafe_allow_html=True)

            section_label("Análise de Frequência")
            g1, g2 = st.columns([3, 2])
            with g1: st.plotly_chart(chart_barras(df_f), use_container_width=True, config={'displayModeBar': False})
            with g2: 
                fig_dn = chart_donut(df_f)
                if fig_dn: st.plotly_chart(fig_dn, use_container_width=True, config={'displayModeBar': False})
            st.plotly_chart(chart_linha(df_f), use_container_width=True, config={'displayModeBar': False})

            section_label("Consulta Detalhada de Relatórios")
            df_v = df_f.sort_values('Data da atividade', ascending=False)
            if not df_v.empty:
                ce, cd = st.columns([2, 3])
                with ce:
                    opcs = [f"{r['Data da atividade'].strftime('%d/%m/%Y')} - {r['Nome']}" for _, r in df_v.iterrows()]
                    esc = st.selectbox("Selecionar Registro Específico:", options=opcs, label_visibility="collapsed")
                    st.markdown("<p style='font-size:0.6rem;font-weight:700;letter-spacing:0.1em;opacity:0.5;margin-top:1rem;'>ÚLTIMOS ENVIOS</p>", unsafe_allow_html=True)
                    for _, r in df_v.head(5).iterrows(): report_card(r)
                with cd:
                    if esc:
                        rel = df.loc[df_v.index[opcs.index(esc)]]
                        st.markdown(f"<div style='background:var(--bg-surface);border:1px solid var(--border);border-top:3px solid var(--accent);border-radius:12px;padding:1.3rem;margin-bottom:1rem;'><h3 style='margin:0;color:var(--text-primary);'>{rel['Nome']}</h3><p style='margin:0;opacity:0.7;font-size:0.8rem;'>{rel['Data da atividade'].strftime('%d/%m/%Y')} | Preceptor(a): {rel.get('Nome do preceptor','—')}</p><p style='margin:0;opacity:0.7;font-size:0.8rem;'>Tutores: {rel.get('tutores presentes','Nenhum')}</p></div>", unsafe_allow_html=True)
                        for t, k in [("Atividades Realizadas", 'ATIVIDADE(S) REALIZADA(S)'), ("Objetivos da Atividade", 'OBJETIVO DA(S) ATIVIDADE(S)'), ("Relato Fundamentado", 'RELATO FUNDAMENTADO'), ("Reflexões Críticas", 'REFLEXÕES CRÍTICAS')]:
                            with st.expander(t): st.write(rel.get(k, 'Não informado.'))

    # ---------------------------------------------------------
    # ROTA: MONITOR (PORTAL DE ENVIO E HISTÓRICO)
    # ---------------------------------------------------------
    elif role == 'monitor':
        if 'acao_monitor' not in st.session_state: st.session_state.acao_monitor = 'lista'
        if 'registro_selecionado' not in st.session_state: st.session_state.registro_selecionado = None

        page_header("Portal do Sistema", "Gestão de Atividades e Banco de Dados PET.")
        aba1, aba2 = st.tabs(["[+] Registrar Nova Atividade", "[≡] Meu Histórico do Sistema"])

        with aba1:
            st.markdown("<p style='font-size:0.85rem; color:var(--text-secondary); margin-bottom:1.5rem;'>Preencha os detalhes técnicos. Sua identificação no banco de dados é processada automaticamente via Token.</p>", unsafe_allow_html=True)
            
            with st.form("form_mon", clear_on_submit=True):
                c_d, c_h = st.columns(2)
                with c_d: d_a = st.date_input("Data do Registro *", value=date.today())
                with c_h: h_i = st.time_input("Horário de Início *")
                
                loc = st.text_input("Localização *")
                st.markdown("---")
                prec = st.selectbox("Preceptor(a) Validador(a) *", ["Escolher", "Mariângela - Preceptora turno MANHÃ", "Sammia - Preceptora turno TARDE"])
                
                c_t, c_o = st.columns(2)
                with c_t: tuts = st.multiselect("Tutores", ["Joana Machado", "Léia Lima"])
                with c_o: orie = st.multiselect("Orientação de Serviço", ["Beatriz Costa"])
                
                st.markdown("---")
                ativ = st.text_area("Descrição das Atividades *", height=100)
                obje = st.text_area("Objetivos Executados *", height=100)
                relat = st.text_area("Relato Fundamentado *", height=150)
                refl = st.text_area("Reflexões Críticas *", height=100)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Submeter Atividade", use_container_width=True):
                    if prec == "Escolher" or not loc or not ativ or not obje or not relat or not refl:
                        st.error("Protocolo Incompleto: Preencha todos os campos sinalizados (*).")
                    else:
                        linha = [
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"), st.session_state['name'], "",
                            ", ".join(tuts) if tuts else "Nenhum", prec, "", d_a.strftime('%d/%m/%Y'), loc, h_i.strftime('%H:%M'),
                            ativ, obje, relat, refl, ", ".join(orie) if orie else "Nenhuma", user_data.get('funcao', 'Monitor')
                        ]
                        if salvar_nova_atividade(linha):
                            st.toast("Transação Efetuada: Registro salvo no banco de dados.", icon="✅")
                            st.success("Tudo certo! O formulário foi esvaziado e está pronto para uma nova entrada.")
                            carregar_dados.clear()

        with aba2:
            df = carregar_dados()
            if df.empty or 'Nome' not in df.columns:
                st.warning("Banco de dados indisponível.")
            else:
                nome_busca = st.session_state['name'].strip().lower()
                df_meu = df[df['Nome'].astype(str).str.strip().str.lower() == nome_busca].copy()
                
                if df_meu.empty:
                    st.info("Nenhum registro localizado sob suas credenciais.")
                else:
                    if st.session_state.acao_monitor == 'detalhes' and st.session_state.registro_selecionado is not None:
                        row = st.session_state.registro_selecionado
                        if st.button("Voltar ao Histórico", key="btn_voltar_detalhes"):
                            st.session_state.acao_monitor = 'lista'; st.rerun()
                            
                        st.markdown(f"### Detalhes do Registro")
                        st.markdown(f"**Data Operacional:** {row['Data da atividade'].strftime('%d/%m/%Y')} às {row['Horário de Início']}")
                        st.markdown(f"**Preceptor(a):** {row.get('Nome do preceptor', 'N/A')} | **Local:** {row.get('Local Específico:', 'N/A')}")
                        st.markdown(f"**Tutores:** {row.get('tutores presentes', '—')} | **Orientadora:** {row.get('Orientadora de serv', '—')}")
                        st.markdown("---")
                        st.markdown("**Atividades Relatadas:**"); st.info(row.get('ATIVIDADE(S) REALIZADA(S)', ''))
                        st.markdown("**Objetivos:**"); st.info(row.get('OBJETIVO DA(S) ATIVIDADE(S)', ''))
                        st.markdown("**Fundamentação:**"); st.info(row.get('RELATO FUNDAMENTADO', ''))
                        st.markdown("**Reflexões:**"); st.info(row.get('REFLEXÕES CRÍTICAS', ''))

                    elif st.session_state.acao_monitor == 'editar' and st.session_state.registro_selecionado is not None:
                        row = st.session_state.registro_selecionado
                        if st.button("Cancelar Edição", key="btn_canc_edit"):
                            st.session_state.acao_monitor = 'lista'; st.rerun()
                            
                        st.markdown("### Modificar Registro")
                        st.caption(f"ID da Transação: {row.get('Carimbo de data/hora', 'N/A')}")
                        
                        with st.form("form_editar_mon"):
                            e_cd, e_ch = st.columns(2)
                            with e_cd: edit_d = st.date_input("Data do Registro *", value=row['Data da atividade'].date())
                            with e_ch: 
                                try: time_val = datetime.strptime(str(row['Horário de Início']), '%H:%M').time()
                                except: time_val = datetime.now().time()
                                edit_h = st.time_input("Horário de Início *", value=time_val)
                                
                            edit_loc = st.text_input("Localização *", value=row.get('Local Específico:', ''))
                            
                            opcoes_prec = ["Escolher", "Mariângela - Preceptora turno MANHÃ", "Sammia - Preceptora turno TARDE"]
                            idx_prec = opcoes_prec.index(row.get('Nome do preceptor', 'Escolher')) if row.get('Nome do preceptor') in opcoes_prec else 0
                            edit_prec = st.selectbox("Preceptor(a) *", opcoes_prec, index=idx_prec)
                            
                            edit_ativ = st.text_area("Descrição das Atividades *", value=row.get('ATIVIDADE(S) REALIZADA(S)', ''), height=100)
                            edit_obje = st.text_area("Objetivos *", value=row.get('OBJETIVO DA(S) ATIVIDADE(S)', ''), height=100)
                            edit_relat = st.text_area("Relato Fundamentado *", value=row.get('RELATO FUNDAMENTADO', ''), height=150)
                            edit_refl = st.text_area("Reflexões Críticas *", value=row.get('REFLEXÕES CRÍTICAS', ''), height=100)
                            
                            if st.form_submit_button("Salvar Modificações", use_container_width=True):
                                if edit_prec == "Escolher" or not edit_loc or not edit_ativ:
                                    st.error("Preencha os campos essenciais.")
                                else:
                                    linha_atualizada = [
                                        row['Carimbo de data/hora'], st.session_state['name'], row.get('Status', ''),
                                        row.get('tutores presentes', ''), edit_prec, row.get('Status do preceptor', ''),
                                        edit_d.strftime('%d/%m/%Y'), edit_loc, edit_h.strftime('%H:%M'),
                                        edit_ativ, edit_obje, edit_relat, edit_refl,
                                        row.get('Orientadora de serv', ''), user_data.get('funcao', 'Monitor')
                                    ]
                                    if atualizar_atividade(row['Carimbo de data/hora'], st.session_state['name'], linha_atualizada):
                                        st.toast("Modificação salva no sistema.", icon="✅")
                                        carregar_dados.clear(); st.session_state.acao_monitor = 'lista'; st.rerun()

                    else:
                        st.markdown("<p style='font-size:0.85rem; color:var(--text-secondary); margin-bottom:1rem;'>Selecione [ Detalhes ] para visualizar a entrada completa ou [ Editar ] para corrigir informações.</p>", unsafe_allow_html=True)
                        f_ini, f_fim = st.date_input("Filtrar Período de Sistema:", value=(date.today().replace(day=1), date.today()))
                        df_filt = df_meu[(df_meu['Data da atividade'].dt.date >= f_ini) & (df_meu['Data da atividade'].dt.date <= f_fim)]
                        df_filt = df_filt.sort_values('Data da atividade', ascending=False)
                        
                        st.markdown("<div style='display:flex; font-weight:700; color:var(--text-muted); font-size:0.75rem; border-bottom:1px solid var(--border); padding-bottom:0.5rem; margin-bottom:0.5rem;'><div style='flex:1;'>DATA / HORÁRIO</div><div style='flex:1.5;'>PRECEPTOR(A)</div><div style='flex:1.5;'>LOCAL</div><div style='flex:1; text-align:right;'>AÇÕES</div></div>", unsafe_allow_html=True)
                        for idx, row in df_filt.iterrows():
                            c1, c2, c3, c4 = st.columns([1, 1.5, 1.5, 1])
                            with c1: st.markdown(f"<span style='font-size:0.85rem;'>{row['Data da atividade'].strftime('%d/%m/%Y')}<br><span style='color:var(--text-muted); font-size:0.7rem;'>{row['Horário de Início']}</span></span>", unsafe_allow_html=True)
                            with c2: st.markdown(f"<span style='font-size:0.8rem;'>{row.get('Nome do preceptor', '—')}</span>", unsafe_allow_html=True)
                            with c3: st.markdown(f"<span style='font-size:0.8rem;'>{row.get('Local Específico:', '—')}</span>", unsafe_allow_html=True)
                            with c4:
                                b1, b2 = st.columns(2)
                                if b1.button("Detalhes", key=f"v_{idx}", use_container_width=True):
                                    st.session_state.registro_selecionado = row; st.session_state.acao_monitor = 'detalhes'; st.rerun()
                                if b2.button("Editar", key=f"e_{idx}", use_container_width=True):
                                    st.session_state.registro_selecionado = row; st.session_state.acao_monitor = 'editar'; st.rerun()
                            st.markdown("<div style='border-bottom:1px solid var(--border); margin: 0.5rem 0;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # RODAPÉ DA SIDEBAR (PERFIL E SAIR)
    # ---------------------------------------------------------
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    st.sidebar.markdown(f"""
    <div class="user-profile-card">
        <div class="user-avatar">{st.session_state['name'][0].upper()}</div>
        <div class="user-info">
            <span class="user-name">{st.session_state['name']}</span>
            <span class="user-role">{role.upper()} | {user_data.get('funcao', 'Membro')}</span>
        </div>
    </div>""", unsafe_allow_html=True)
    auth.logout('Sair da Conta', 'sidebar')