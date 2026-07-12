import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import uuid
import requests
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# CONFIGURAÇÕES INICIAIS E VARIÁVEIS GLOBAIS
# =====================================================================
st.set_page_config(page_title="Gestão Microsoft Rewards", layout="wide", page_icon="🎮")

TAXA_CONVERSAO = 172.1
TOPICO_NTFY = "josimar_rewards_alert_99"

# Divisão exata para o sistema saber o que é de cada plataforma
cat_bing = [
    "BONUS DE SEQUENCIA", "BONUS BING STAR", "BONUS DE NIVEL",
    "BONUS DE PESQUISA", "SERIE DE PESQUISA NO BING",
    "SERIE CONJUNTO DIARIO", "SERIE NAVEGAR NO EDGE",
    "SERIE APLICATIVO BING", "PESQUISAS BING", "ATIVIDADES",
    "LER E GANHAR"
]

cat_xbox = [
    "ACESSAR APP XBOX", "JOGAR JEWEL",
    "JOGAR NO CONSOLE", "BONUS JOGAR NO CONSOLE", "JOGAR NO PC",
    "BONUS JOGAR NO PC", "JOGAR UM JOGO DO XBOX GAME PASS",
    "SEQUENCIA SEMANAL DO XBOX GAME PASS", "PACOTE MENSAL - 4 e 8 JOGOS",
    "COMPRAR JOGOS"
]

CATEGORIAS = cat_bing + cat_xbox

sequencias_globais = {
    "SERIE DE PESQUISA NO BING": [0, 3, 100],
    "SERIE CONJUNTO DIARIO": [0, 30, 100],
    "SERIE NAVEGAR NO EDGE": [0, 5, 10, 20, 30, 40, 80, 120],
    "SERIE APLICATIVO BING": [0, 5, 10, 15, 50],
    "ACESSAR APP XBOX": [0, 8, 16, 24, 32, 50]
}

def classificar_origem(cat):
    if cat in cat_bing: return "Bing"
    if cat in cat_xbox: return "Xbox"
    return "Outros"

# =====================================================================
# LÓGICA DE DADOS, CACHE E FUSO HORÁRIO
# =====================================================================
def obter_data_logica(dt):
    if dt.hour == 0:
        return (dt - timedelta(days=1)).date()
    return dt.date()

conn = st.connection("gsheets", type=GSheetsConnection)

# ⚠️ COLE SUA URL AQUI DENTRO DAS ASPAS
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1lKTGiEkDZBm4XoQuYFOwv3F5Si-DCvEv3At5Fyd4EDY/edit?gid=0#gid=0"

def carregar_dados():
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, ttl=0) # Atualiza ao vivo
        colunas_esperadas = ['ID', 'Data_Hora', 'Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao']
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = None
        df = df.dropna(how='all')
        if not df.empty:
             df['Data_Hora'] = pd.to_datetime(df['Data_Hora'])
             df['Data_Logica'] = pd.to_datetime(df['Data_Logica']).dt.date
             df['Pontos'] = pd.to_numeric(df['Pontos'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['ID', 'Data_Hora', 'Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao'])

def salvar_dados(df_novo):
     try:
         df_save = df_novo.copy()
         df_save['Data_Hora'] = df_save['Data_Hora'].astype(str)
         df_save['Data_Logica'] = df_save['Data_Logica'].astype(str)
         conn.update(spreadsheet=URL_PLANILHA, data=df_save)
         st.cache_data.clear() # Limpa a memória para recarregar rápido
     except Exception as e:
         st.error(f"Erro ao salvar no banco de dados: {e}")

def enviar_notificacao_ntfy(mensagem, titulo="🎮 Microsoft Rewards"):
    try:
        requests.post(f"https://ntfy.sh/{TOPICO_NTFY}",
            data=mensagem.encode('utf-8'),
            headers={"Title": titulo, "Tags": "video_game,tada"}
        )
    except: pass

# Fuso horário de Brasília
agora = datetime.utcnow() - timedelta(hours=3)
hoje = obter_data_logica(agora)

df = carregar_dados()

st.title("🎮 Painel Microsoft Rewards")

aba_resumo, aba_lancar, aba_editar, aba_resgatar, aba_historico = st.tabs([
    "📊 Dashboards", "➕ Lançar Pontos", "✏️ Editar Dia", "🛍️ Resgates", "⚙️ Histórico"
])

# --- ABA 1: DASHBOARDS (RESUMO) ---
with aba_resumo:
    df_ganhos = df[df['Tipo'] == 'Ganho'].copy()
    df_gastos = df[df['Tipo'] == 'Gasto'].copy()

    saldo_atual = df_ganhos['Pontos'].sum() - df_gastos['Pontos'].sum()

    ontem = hoje - timedelta(days=1)
    
    # Faz o cálculo para forçar o início da semana sempre no Domingo
    dias_para_domingo = (hoje.weekday() + 1) % 7
    inicio_semana = hoje - timedelta(days=dias_para_domingo)
    
    inicio_mes = hoje.replace(day=1)=1)

    pontos_hoje = df_ganhos[df_ganhos['Data_Logica'] == hoje]['Pontos'].sum()
    pontos_ontem = df_ganhos[df_ganhos['Data_Logica'] == ontem]['Pontos'].sum()
    pontos_semana = df_ganhos[df_ganhos['Data_Logica'] >= inicio_semana]['Pontos'].sum()
    pontos_mes = df_ganhos[df_ganhos['Data_Logica'] >= inicio_mes]['Pontos'].sum()
    pontos_ano = df_ganhos[df_ganhos['Data_Logica'] >= inicio_ano]['Pontos'].sum()
    gastos_mes = df_gastos[df_gastos['Data_Logica'] >= inicio_mes]['Pontos'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Atual", f"{saldo_atual:,.0f}".replace(',','.'))
    col2.metric("Equivalente em R$", f"R$ {saldo_atual / TAXA_CONVERSAO:.2f}".replace('.',','))
    col3.metric("Gastos neste Mês", f"{gastos_mes:,.0f}".replace(',','.'))

    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Hoje", f"{pontos_hoje:,.0f}".replace(',','.'))
    c2.metric("Ontem", f"{pontos_ontem:,.0f}".replace(',','.'))
    c3.metric("Esta Semana", f"{pontos_semana:,.0f}".replace(',','.'))
    c4.metric("Este Mês", f"{pontos_mes:,.0f}".replace(',','.'))
    c5.metric("Este Ano", f"{pontos_ano:,.0f}".replace(',','.'))
    
    st.divider()
    meta_pontos = st.number_input("Definir Meta de Saldo (Pontos)", min_value=0, value=15000, step=1000)
    if meta_pontos > 0:
        progresso = min(saldo_atual / meta_pontos, 1.0)
        st.progress(progresso)

    st.divider()
    
    # NOVOS GRÁFICOS
    if not df_ganhos.empty:
        df_mes_atual = df_ganhos[df_ganhos['Data_Logica'] >= inicio_mes].copy()
        
        gcol1, gcol2 = st.columns(2)
        with gcol1:
            if not df_mes_atual.empty:
                df_mes_atual['Origem'] = df_mes_atual['Categoria'].apply(classificar_origem)
                df_origem = df_mes_atual.groupby('Origem')['Pontos'].sum().reset_index()
                fig_origem = px.pie(df_origem, values='Pontos', names='Origem', hole=0.5, 
                                    title="Produtividade: Bing vs Xbox (Este Mês)",
                                    color='Origem', color_discrete_map={'Bing':'#00a4ef', 'Xbox':'#107c10', 'Outros':'#7f8c8d'})
                st.plotly_chart(fig_origem, use_container_width=True)
                
        with gcol2:
            df_hoje_grafico = df_ganhos[df_ganhos['Data_Logica'] == hoje]
            if not df_hoje_grafico.empty:
                df_cat_hoje = df_hoje_grafico.groupby('Categoria')['Pontos'].sum().reset_index()
                df_cat_hoje = df_cat_hoje[df_cat_hoje['Pontos'] > 0].sort_values(by='Pontos', ascending=True)
                fig_hoje = px.bar(df_cat_hoje, x='Pontos', y='Categoria', orientation='h', 
                                  title="Pontos Feitos Hoje", color_discrete_sequence=['#8a2be2'])
                st.plotly_chart(fig_hoje, use_container_width=True)
            else:
                st.info("Nenhum ponto registrado hoje ainda.")

        st.divider()
        if not df_mes_atual.empty:
            df_mes_dia = df_mes_atual.groupby('Data_Logica')['Pontos'].sum().reset_index().sort_values('Data_Logica')
            fig_evolucao = px.area(df_mes_dia, x='Data_Logica', y='Pontos', markers=True, 
                                   title="Evolução Diária (Este Mês)", color_discrete_sequence=['#8a2be2'])
            fig_evolucao.update_xaxes(title="Dia do Mês", tickformat="%d/%m")
            st.plotly_chart(fig_evolucao, use_container_width=True)

# --- ABA 2: LANÇAR PONTOS ---
with aba_lancar:
    st.subheader("Lançamento de Ganhos")
    with st.form("form_ganhos"):
        valores_input = {}
        dia_semana = hoje.weekday()
        
        # --- SEÇÃO BING ---
        st.markdown("#### 🌐 Buscas e Painel Bing")
        cols_b = st.columns(3)
        for i, cat in enumerate(cat_bing):
            with cols_b[i % 3]:
                if cat in sequencias_globais:
                    valores_input[cat] = st.selectbox(cat, options=sequencias_globais[cat], key=f"b_{i}")
                else:
                    padrao = 0
                    if cat == "PESQUISAS BING": padrao = 57 
                    elif cat == "LER E GANHAR":
                        if dia_semana < 5: padrao = 25
                        elif dia_semana == 5: padrao = 5
                    valores_input[cat] = st.number_input(cat, min_value=0, value=padrao, step=1, key=f"b_{i}")

        st.divider()
        
        # --- SEÇÃO XBOX ---
        st.markdown("#### 🎮 Aplicativo Xbox e Game Pass")
        cols_x = st.columns(3)
        for i, cat in enumerate(cat_xbox):
            if cat == "COMPRAR JOGOS": continue
            with cols_x[i % 3]:
                if cat in sequencias_globais:
                    valores_input[cat] = st.selectbox(cat, options=sequencias_globais[cat], key=f"x_{i}")
                else:
                    padrao = 0
                    if cat == "JOGAR JEWEL": padrao = 10
                    elif cat == "JOGAR NO CONSOLE": padrao = 20
                    elif cat == "JOGAR NO PC": padrao = 20
                    elif cat == "JOGAR UM JOGO DO XBOX GAME PASS": padrao = 20
                    valores_input[cat] = st.number_input(cat, min_value=0, value=padrao, step=1, key=f"x_{i}")

        st.divider()
        st.markdown("#### 🛒 Compras na Loja")
        valor_gasto_jogos = st.number_input("Valor gasto em jogos na loja (R$) - Opcional", min_value=0.0, value=0.0, step=1.0)
        pontos_compra = int((valor_gasto_jogos / 3.0) * 20) if valor_gasto_jogos > 0 else 0

        submit = st.form_submit_button("💾 Salvar Pontos do Dia", type="primary")
        
        if submit:
            valores_input["COMPRAR JOGOS"] = pontos_compra
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

# --- ABA 3: EDITAR DIA ---
with aba_editar:
    st.subheader("Editar Lançamentos de um Dia")
    st.caption("Selecione um dia para carregar os pontos salvos. Modifique o que precisar e salve novamente para substituir o dia inteiro.")
    
    # Filtra os dias que têm registros de ganhos dentro das categorias normais
    df_editavel = df[(df['Tipo'] == 'Ganho') & (df['Categoria'].isin(CATEGORIAS))].copy()
    dias_disponiveis = sorted(df_editavel['Data_Logica'].unique(), reverse=True)
    
    if not dias_disponiveis:
        st.info("Nenhum dia com lançamentos detalhados encontrado.")
    else:
        dia_selecionado = st.selectbox("Selecione a data que deseja editar:", dias_disponiveis, 
                                       format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))
        
        # Puxa os dados exatos do dia escolhido
        df_dia = df_editavel[df_editavel['Data_Logica'] == dia_selecionado]
        valores_atuais = dict(zip(df_dia['Categoria'], df_dia['Pontos']))
        
        with st.form("form_editar"):
            valores_edit = {}
            
            st.markdown("#### 🌐 Buscas e Painel Bing")
            cols_b_ed = st.columns(3)
            for i, cat in enumerate(cat_bing):
                with cols_b_ed[i % 3]:
                    val_atual = int(valores_atuais.get(cat, 0))
                    if cat in sequencias_globais:
                        idx = sequencias_globais[cat].index(val_atual) if val_atual in sequencias_globais[cat] else 0
                        valores_edit[cat] = st.selectbox(cat, options=sequencias_globais[cat], index=idx, key=f"eb_{i}")
                    else:
                        valores_edit[cat] = st.number_input(cat, min_value=0, value=val_atual, step=1, key=f"eb_{i}")
            
            st.divider()
            st.markdown("#### 🎮 Aplicativo Xbox e Game Pass")
            cols_x_ed = st.columns(3)
            for i, cat in enumerate(cat_xbox):
                if cat == "COMPRAR JOGOS": continue
                with cols_x_ed[i % 3]:
                    val_atual = int(valores_atuais.get(cat, 0))
                    if cat in sequencias_globais:
                        idx = sequencias_globais[cat].index(val_atual) if val_atual in sequencias_globais[cat] else 0
                        valores_edit[cat] = st.selectbox(cat, options=sequencias_globais[cat], index=idx, key=f"ex_{i}")
                    else:
                        valores_edit[cat] = st.number_input(cat, min_value=0, value=val_atual, step=1, key=f"ex_{i}")

            st.divider()
            st.markdown("#### 🛒 Compras na Loja (Edição Direta)")
            pts_compra_atual = int(valores_atuais.get("COMPRAR JOGOS", 0))
            valores_edit["COMPRAR JOGOS"] = st.number_input("Pontos ganhos com compras", min_value=0, value=pts_compra_atual, step=1, key="e_compra")

            submit_edit = st.form_submit_button("💾 Salvar Alterações do Dia", type="primary")
            
            if submit_edit:
                # 1. Remove apenas os lançamentos de ganhos operacionais deste dia específico
                condicao_manter = ~((df['Data_Logica'].astype(str) == str(dia_selecionado)) & 
                                    (df['Categoria'].isin(CATEGORIAS)) & 
                                    (df['Tipo'] == 'Ganho'))
                df_atualizado = df[condicao_manter].copy()
                
                # 2. Insere os novos dados corrigidos
                novos_registros_edit = []
                for cat, pts in valores_edit.items():
                    if pts > 0:
                        novos_registros_edit.append({
                            'ID': str(uuid.uuid4()), 'Data_Hora': agora, 'Data_Logica': dia_selecionado,
                            'Categoria': cat, 'Pontos': pts, 'Tipo': 'Ganho', 'Descricao': 'Lançamento Editado'
                        })
                
                if novos_registros_edit:
                    df_atualizado = pd.concat([df_atualizado, pd.DataFrame(novos_registros_edit)], ignore_index=True)
                
                salvar_dados(df_atualizado)
                st.success("O dia foi atualizado com sucesso!")
                st.rerun()

# --- ABA 4: RESGATES ---
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

# --- ABA 5: HISTÓRICO ---
with aba_historico:
    st.subheader("Resumo de Pontos por Dia")
    
    if not df.empty:
        # Tabela limpa agrupada por dia
        df_historico_limpo = df[df['Tipo'] == 'Ganho'].groupby('Data_Logica')['Pontos'].sum().reset_index()
        df_historico_limpo.columns = ['Data', 'Total de Pontos']
        df_historico_limpo = df_historico_limpo.sort_values(by="Data", ascending=False)
        df_historico_limpo['Data'] = pd.to_datetime(df_historico_limpo['Data']).dt.strftime('%d/%m/%Y')
        
        st.dataframe(df_historico_limpo, use_container_width=True, hide_index=True)
        
        st.divider()
        with st.expander("⚙️ Ver banco de dados bruto (Avançado)"):
            df_display = df.sort_values(by="Data_Hora", ascending=False).copy()
            df_display['Data_Logica'] = pd.to_datetime(df_display['Data_Logica']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_display[['Data_Logica', 'Categoria', 'Pontos', 'Tipo', 'Descricao']], use_container_width=True)
