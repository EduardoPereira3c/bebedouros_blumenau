import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Gestão de Bebedouros - PMB", layout="centered", page_icon="🚰")

# --- CONEXÃO COM BANCO DE DADOS LOCAL ---
conn = sqlite3.connect("bebedouros_blumenau.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS bebedouros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        predio TEXT,
        local_exato TEXT,
        modelo_bebedouro TEXT,
        tipo_filtro TEXT,
        data_instalacao TEXT,
        proxima_troca TEXT,
        foto BLOB,
        observacoes TEXT
    )
''')
conn.commit()

st.title("🚰 Controle de Bebedouros - PMB")

menu = st.sidebar.radio("Menu Principal", ["➕ Novo Cadastro", "📋 Bebedouros Mapeados", "📊 Exportar Relatório"])

# --- BUSCAR PRÉDIOS JÁ CADASTRADOS PARA BUSCA RÁPIDA ---
c.execute("SELECT DISTINCT predio FROM bebedouros WHERE predio IS NOT NULL AND predio != '' ORDER BY predio ASC")
predios_cadastrados = [r[0] for r in c.fetchall()]

# --- ABA 1: NOVO CADASTRO ---
if menu == "➕ Novo Cadastro":
    st.subheader("Cadastrar Bebedouro em Campo")

    opcoes_predio = ["➕ Digitar Novo Prédio / Escola / ESF"] + predios_cadastrados
    selecao_predio = st.selectbox("Selecione um Prédio Cadastrado (ou digite um novo)", opcoes_predio, key="select_predio_key")

    if selecao_predio == "➕ Digitar Novo Prédio / Escola / ESF":
        predio = st.text_input("Nome do Prédio / Escola / ESF *", placeholder="Ex: EBM Machado de Assis", key="input_novo_predio_key")
    else:
        predio = selecao_predio
        st.info(f"📍 Cadastrando bebedouro para: **{predio}**")

    with st.form("form_bebedouro", clear_on_submit=True):
        local_exato = st.text_input("Localização Exata no Prédio *", placeholder="Ex: Bloco B, ao lado da coordenação", key="local_exato_key")
        
        col1, col2 = st.columns(2)
        with col1:
            modelo_bebedouro = st.text_input("Modelo do Bebedouro", placeholder="Ex: Coluna Inox IBBL", key="modelo_key")
        with col2:
            tipo_filtro = st.text_input("Modelo do Refil / Filtro *", placeholder="Ex: Refil CZ+7 / PP 10\"", key="filtro_key")

        data_troca = st.date_input("Data da Troca / Instalação", datetime.now(), key="data_troca_key")
        meses_validade = st.number_input("Validade do Filtro (em meses)", min_value=1, max_value=24, value=6, key="validade_key")
        data_proxima = data_troca + timedelta(days=meses_validade * 30)
        
        st.caption(f"📅 Previsão da próxima troca: **{data_proxima.strftime('%d/%m/%Y')}**")

        # Campo de foto sem estruturas condicionais no formulário para evitar erros de DOM
        foto_arquivo = st.file_uploader("📸 Tirar / Carregar Foto do Bebedouro ou Refil", type=["jpg", "jpeg", "png"], key="foto_key")

        observacoes = st.text_area("Observações Técnicas", placeholder="Ex: Troca de mangueira executada; pressão normal.", key="obs_key")

        salvar = st.form_submit_button("💾 Salvar Cadastro")

        if salvar:
            if not predio or not local_exato or not tipo_filtro:
                st.error("Preencha todos os campos obrigatórios (*).")
            else:
                foto_bytes = foto_arquivo.read() if foto_arquivo is not None else None
                
                c.execute('''
                    INSERT INTO bebedouros 
                    (predio, local_exato, modelo_bebedouro, tipo_filtro, data_instalacao, proxima_troca, foto, observacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (predio, local_exato, modelo_bebedouro, tipo_filtro, str(data_troca), str(data_proxima), foto_bytes, observacoes))
                conn.commit()
                st.success(f"✅ Bebedouro em '{predio}' registrado com sucesso!")

# --- ABA 2: CONSULTA EM CAMPO ---
elif menu == "📋 Bebedouros Mapeados":
    st.subheader("Bebedouros Registrados")
    
    df = pd.read_sql_query("SELECT id, predio, local_exato, modelo_bebedouro, tipo_filtro, data_instalacao, proxima_troca, observacoes FROM bebedouros", conn)

    if df.empty:
        st.info("Nenhum bebedouro cadastrado até o momento.")
    else:
        predios_unicos = ["Todos"] + list(df['predio'].unique())
        filtro_predio = st.selectbox("Filtrar por Prédio / Escola / ESF", predios_unicos, key="filtro_consulta_key")

        df_filtrado = df if filtro_predio == "Todos" else df[df['predio'] == filtro_predio]

        for _, row in df_filtrado.iterrows():
            with st.expander(f"📍 {row['predio']} - {row['local_exato']}"):
                st.write(f"**Equipamento:** {row['modelo_bebedouro']}")
                st.write(f"**Elemento Filtrante:** `{row['tipo_filtro']}`")
                st.write(f"**Última Troca:** {row['data_instalacao']} | **Próxima Troca:** {row['proxima_troca']}")
                
                c.execute("SELECT foto FROM bebedouros WHERE id = ?", (row['id'],))
                res = c.fetchone()
                if res and res[0]:
                    st.image(res[0], caption="Foto Registrada", use_column_width=True)
                    
                if row['observacoes']:
                    st.info(f"Obs: {row['observacoes']}")

# --- ABA 3: EXPORTAÇÃO DE RELATÓRIO ---
elif menu == "📊 Exportar Relatório":
    st.subheader("Relatório e Exportação")
    df = pd.read_sql_query("SELECT id, predio, local_exato, modelo_bebedouro, tipo_filtro, data_instalacao, proxima_troca, observacoes FROM bebedouros", conn)

    if not df.empty:
        st.metric("Total de Bebedouros Mapeados", len(df))
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Planilha para a Prefeitura (CSV)",
            data=csv,
            file_name="mapeamento_bebedouros_blumenau.csv",
            mime="text/csv",
            key="btn_download_csv_key"
        )
    else:
        st.info("Cadastre bebedouros para gerar o relatório.")
