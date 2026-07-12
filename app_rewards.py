import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import uuid
import requests
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# CONFIGURAÇÕES INICIAIS
# =====================================================================
st.set_page_config(page_title="Gestão Microsoft Rewards", layout="wide", page_icon="🎮")

TAXA_CONVERSAO = 172.1
TOPICO_NTFY = "josimar_rewards_alert_99"

CATEGORIAS = [
    "BONUS DE SEQUENCIA", "BONUS BING STAR", "BONUS DE NIVEL",
    "BONUS DE PESQUISA", "SERIE DE PESQUISA NO BING",
    "SERIE CONJUNTO DIARIO", "SERIE NAVEGAR NO EDGE",
    "SERIE APLICATIVO BING", "PESQUISAS BING", "ATIVIDADES",
    "LER E GANHAR", "ACESSAR APP XBOX", "JOGAR JEWEL",
    "JOGAR NO CONSOLE", "BONUS JOGAR NO CONSOLE", "JOGAR NO PC",
    "BONUS JOGAR NO PC", "JOGAR UM JOGO DO XBOX GAME PASS",
    "SEQUENCIA SEMANAL DO XBOX GAME PASS", "PACOTE MENSAL - 4 e 8 JOGOS",
    "COMPRAR JOGOS"
]

# =====================================================================
# FUNÇÕES DE LÓGICA E BANCO DE DADOS
# =====================================================================
def obter_data_logica(dt):
    if dt.hour == 0:
        return (dt - timedelta(days=1)).date()
    return dt.date()

conn = st.connection("gsheets", type=GSheetsConnection)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1lKTGiEkDZBm4XoQuYFOwv3F5Si-DCvEv3At5Fyd4EDY/edit?gid=0#gid=0"

def carregar_dados():
    try:
        df = conn.read(spreadsheet=URL_PLANILHA)
        colunas_esperadas = ['ID', 'Data_Hora', 'Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao']
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = None
        df = df.dropna(how='all')
        if not df.empty:
             df['Data_Hora'] = pd.to_datetime(df['Data_Hora'])
             df['Data_Logica'] = pd.to_datetime(df['Data_Logica']).dt.date
        return df
    except Exception as e:
        return pd.DataFrame(columns=['ID', 'Data_Hora', 'Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao'])

def salvar_dados(df_novo):
     try:
         df_save = df_novo.copy()
         df_save['Data_Hora'] = df_save['Data_Hora'].astype(str)
         df_save['Data_Logica'] = df_save['Data_Logica'].astype(str)
         conn.update(worksheet="Página1", data=df_save)
     except Exception as e:
         st.error(f"Erro ao salvar: {e}")

def enviar_notificacao_ntfy(mensagem, titulo="🎮 Microsoft Rewards"):
    try:
        requests.post(f"https://ntfy.sh/{TOPICO_NTFY}",
            data=mensagem.encode('utf-8'),
            headers={"Title": titulo, "Tags": "video_game,tada"}
        )
    except: pass

df = carregar_dados()
# Puxa a hora universal (UTC) e subtrai 3 horas para forçar o horário de Brasília
agora = datetime.utcnow() - timedelta(hours=3)
hoje = obter_data_logica(agora)

st.title("🎮 Painel Microsoft Rewards")

aba_resumo, aba_lancar, aba_resgatar, aba_historico = st.tabs([
    "📊 Resumo", "➕ Lançar Pontos", "🛍️ Resgates", "⚙️ Histórico"
])

# --- ABA 1: RESUMO ---
with aba_resumo:
    df_ganhos = df[df['Tipo'] == 'Ganho']
    df_gastos = df[df['Tipo'] == 'Gasto']

    total_ganhos = pd.to_numeric(df_ganhos['Pontos'], errors='coerce').sum()
    total_gastos = pd.to_numeric(df_gastos['Pontos'], errors='coerce').sum()
    saldo_atual = total_ganhos - total_gastos

    ontem = hoje - timedelta(days=1)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    inicio_ano = hoje.replace(month=1, day=1)

    pontos_hoje = df_ganhos[df_ganhos['Data_Logica'] == hoje]['Pontos'].sum()
    pontos_ontem = df_ganhos[df_ganhos['Data_Logica'] == ontem]['Pontos'].sum()
    pontos_semana = df_ganhos[df_ganhos['Data_Logica'] >= inicio_semana]['Pontos'].sum()
    pontos_mes = df_ganhos[df_ganhos['Data_Logica'] >= inicio_mes]['Pontos'].sum()
    pontos_ano = df_ganhos[df_ganhos['Data_Logica'] >= inicio_ano]['Pontos'].sum()
    gastos_mes = df_gastos[df_gastos['Data_Logica'] >= inicio_mes]['Pontos'].sum()

    st.subheader("Visão Geral e Saldo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Atual", f"{saldo_atual:,.0f}".replace(',','.'))
    col2.metric("Equivalente em R$", f"R$ {saldo_atual / TAXA_CONVERSAO:.2f}".replace('.',','))
    col3.metric("Gastos neste Mês", f"{gastos_mes:,.0f}".replace(',','.'))

    st.divider()
    st.subheader("📈 Produção de Pontos")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Hoje", f"{pontos_hoje:,.0f}".replace(',','.'))
    c2.metric("Ontem", f"{pontos_ontem:,.0f}".replace(',','.'))
    c3.metric("Esta Semana", f"{pontos_semana:,.0f}".replace(',','.'))
    c4.metric("Este Mês", f"{pontos_mes:,.0f}".replace(',','.'))
    c5.metric("Este Ano", f"{pontos_ano:,.0f}".replace(',','.'))
    
    st.divider()
    st.subheader("🎯 Acompanhamento de Meta")
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        meta_pontos = st.number_input("Meta (Pontos)", min_value=0, value=15000, step=1000)
        if meta_pontos > 0:
            progresso = min(saldo_atual / meta_pontos, 1.0)
            st.progress(progresso)
    with col_meta2:
        st.info(f"Meta de **{meta_pontos:,.0f} pts** = **R$ {meta_pontos / TAXA_CONVERSAO:.2f}**".replace(',','.'))

    st.divider()
    if not df_ganhos.empty:
        st.subheader("Origem dos Pontos (Mês)")
        df_mes_atual = df_ganhos[df_ganhos['Data_Logica'] >= inicio_mes]
        if not df_mes_atual.empty:
            df_grafico = df_mes_atual.groupby('Categoria')['Pontos'].sum().reset_index()
            fig = px.pie(df_grafico, values='Pontos', names='Categoria', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

# --- ABA 2: LANÇAR PONTOS ---
with aba_lancar:
    st.subheader("Lançamento de Ganhos")
    with st.form("form_ganhos"):
        cols = st.columns(3)
        valores_input = {}
        
        # O sistema descobre que dia da semana é hoje (0 = Seg, 5 = Sáb, 6 = Dom)
        dia_semana = hoje.weekday()
        
        # Mapeamento dos valores exatos das sequências (Primeiro valor é sempre 0)
        sequencias = {
            "SERIE DE PESQUISA NO BING": [0, 3, 100],
            "SERIE CONJUNTO DIARIO": [0, 30, 100],
            "SERIE NAVEGAR NO EDGE": [0, 5, 10, 20, 30, 40, 80, 100],
            "SERIE APLICATIVO BING": [0, 5, 10, 15, 50],
            "ACESSAR APP XBOX": [0, 8, 16, 24, 32, 50]
        }

        for i, cat in enumerate(CATEGORIAS):
            with cols[i % 3]:
                if cat in sequencias:
                    valores_input[cat] = st.selectbox(
                        cat, options=sequencias[cat], key=f"in_{i}"
                    )
                else:
                    padrao = 0
                    if cat == "PESQUISAS BING": padrao = 60
                    elif cat == "LER E GANHAR":
                        if dia_semana < 5: padrao = 25     # Segunda a Sexta
                        elif dia_semana == 5: padrao = 5   # Sábado
                        else: padrao = 0                   # Domingo
                    elif cat == "JOGAR JEWEL": padrao = 10
                    elif cat == "JOGAR NO CONSOLE": padrao = 20
                    elif cat == "JOGAR NO PC": padrao = 20
                    elif cat == "JOGAR UM JOGO DO XBOX GAME PASS": padrao = 20
                    
                    valores_input[cat] = st.number_input(
                        cat, min_value=0, value=padrao, step=1, key=f"in_{i}"
                    )
        
        st.divider()
        valor_gasto_jogos = st.number_input("Valor gasto em jogos na loja (R$) - Opcional", min_value=0.0, value=0.0, step=1.0)
        pontos_compra = int((valor_gasto_jogos / 3.0) * 20) if valor_gasto_jogos > 0 else 0

        submit = st.form_submit_button("💾 Salvar Pontos do Dia", type="primary")
        if submit:
            valores_input["COMPRAR JOGOS"] += pontos_compra
            novos_registros = []
            for cat, pts in valores_input.items():
                if pts > 0:
                    novos_registros.append({
                        'ID': str(uuid.uuid4()), 'Data_Hora': agora, 'Data_Logica': hoje,
                        'Categoria': cat, 'Pontos': pts, 'Tipo': 'Ganho', 'Descricao': ''
                    })
            if novos_registros:
                df = pd.concat([df, pd.DataFrame(novos_registros)], ignore_index=True)
                salvar_dados(df)
                enviar_notificacao_ntfy(f"Sucesso! {sum([r['Pontos'] for r in novos_registros])} pontos salvos.")
                st.success("Salvo na nuvem!")
                st.rerun()

    st.button("🔔 Testar Notificação no Celular", on_click=lambda: enviar_notificacao_ntfy("Alerta funcionando!", "Teste"))

# --- ABA 3: RESGATES ---
with aba_resgatar:
    st.subheader("Registrar Resgate")
    with st.form("form_gastos"):
        pontos_resgatados = st.number_input("Pontos Gastos", min_value=1, value=1000, step=100)
        descricao = st.text_input("Recompensa (Ex: Gift Card Xbox)")
        if st.form_submit_button("🛒 Salvar Resgate", type="primary"):
            novo_resgate = {
                'ID': str(uuid.uuid4()), 'Data_Hora': agora, 'Data_Logica': hoje,
                'Categoria': 'RESGATE', 'Pontos': pontos_resgatados, 'Tipo': 'Gasto', 'Descricao': descricao
            }
            df = pd.concat([df, pd.DataFrame([novo_resgate])], ignore_index=True)
            salvar_dados(df)
            enviar_notificacao_ntfy(f"Resgate: {pontos_resgatados} pontos.", "Recompensa!")
            st.success("Resgate salvo!")
            st.rerun()

# --- ABA 4: HISTÓRICO ---
with aba_historico:
    st.subheader("Gerenciar Dados")
    if not df.empty:
        df_display = df.sort_values(by="Data_Hora", ascending=False).copy()
        df_display['Data_Logica'] = pd.to_datetime(df_display['Data_Logica']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_display[['Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao']], use_container_width=True)
        
        opcoes = df_display['ID'].tolist()
        def formatar(id_val):
            r = df[df['ID'] == id_val].iloc[0]
            return f"{pd.to_datetime(r['Data_Logica']).strftime('%d/%m/%Y')} | {r['Categoria']} | {r['Pontos']} pts"
        
        apagar = st.selectbox("Selecione para excluir", opcoes, format_func=formatar)
        if st.button("🗑️ Excluir Selecionado"):
            df = df[df['ID'] != apagar]
            salvar_dados(df)
            st.rerun()
