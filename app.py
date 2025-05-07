# app.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import re

# Configurações da página
st.set_page_config(page_title="ContFlow Finance", layout="wide")

# Gerenciamento de conexão com o banco de dados
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('dados_financeiros.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()
c = conn.cursor()

# Criar tabela se não existir
c.execute('''CREATE TABLE IF NOT EXISTS lancamentos (
                Data DATE, 
                Valor REAL, 
                Descricao TEXT, 
                Tipo TEXT, 
                Categoria TEXT, 
                Subcategoria TEXT,
                UNIQUE(Data, Valor, Descricao)
            )''')
conn.commit()

# Upload do extrato
st.title("📤 ContFlow Finance - Upload de Extrato")
uploaded_file = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

if uploaded_file:
    extrato_df = pd.read_csv(uploaded_file)

    # Padronização de dados
    extrato_df.columns = ['Data', 'Valor', 'Identificador', 'Descricao']
    extrato_df = extrato_df.drop(columns=['Identificador'])
    
    # Converter data e valor
    extrato_df['Data'] = pd.to_datetime(extrato_df['Data'], dayfirst=True).dt.strftime('%Y-%m-%d')
    extrato_df['Valor'] = extrato_df['Valor'].astype(float).round(2)
    
    # Carregar plano de contas
    plano = pd.read_csv("plano_de_contas_contflow.csv")
    plano['Subcategoria'] = plano['Subcategoria'].str.strip().str.upper()
    
    # Função de classificação melhorada
    def classificar(descricao):
        descricao = str(descricao).upper()
        for _, row in plano.iterrows():
            pattern = re.compile(r'\b' + re.escape(row['Subcategoria']) + r'\b', re.IGNORECASE)
            if pattern.search(descricao):
                return row['Tipo'], row['Categoria'], row['Subcategoria']
        return ('Não Classificado', 'Não Classificado', 'Não Classificado')
    
    # Aplicar classificação
    extrato_df[['Tipo', 'Categoria', 'Subcategoria']] = extrato_df['Descricao'].apply(
        lambda d: pd.Series(classificar(d))
    )
    
    # Remover duplicatas usando SQL
    query = '''INSERT OR IGNORE INTO lancamentos 
               (Data, Valor, Descricao, Tipo, Categoria, Subcategoria) 
               VALUES (?, ?, ?, ?, ?, ?)'''
    
    for _, row in extrato_df.iterrows():
        c.execute(query, (
            row['Data'],
            row['Valor'],
            row['Descricao'],
            row['Tipo'],
            row['Categoria'],
            row['Subcategoria']
        ))
    
    conn.commit()
    st.success(f"✅ {len(extrato_df)} lançamentos processados. Novos registros adicionados!")

# Relatórios e Análises
st.title("📊 Relatório Financeiro")

# Filtros
df = pd.read_sql('''SELECT * FROM lancamentos''', conn)
df['Data'] = pd.to_datetime(df['Data'])

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data inicial", df['Data'].min())
with col2:
    end_date = st.date_input("Data final", df['Data'].max())

filtered_df = df[(df['Data'] >= pd.to_datetime(start_date)) & 
                (df['Data'] <= pd.to_datetime(end_date))]

# Métricas principais
total_entradas = filtered_df[filtered_df['Valor'] > 0]['Valor'].sum()
total_saidas = filtered_df[filtered_df['Valor'] < 0]['Valor'].sum()
saldo = total_entradas + total_saidas

st.subheader("Resumo Financeiro")
col1, col2, col3 = st.columns(3)
col1.metric("Total Entradas", f"R$ {total_entradas:,.2f}")
col2.metric("Total Saídas", f"R$ {total_saidas:,.2f}")
col3.metric("Saldo", f"R$ {saldo:,.2f}")

# Gráficos
st.subheader("Análise por Categoria")

tab1, tab2 = st.tabs(["Gráfico de Pizza", "Gráfico de Barras"])

with tab1:
    fig, ax = plt.subplots()
    filtered_df.groupby('Categoria')['Valor'].sum().plot(
        kind='pie', 
        autopct='%1.1f%%',
        ax=ax,
        labels=None
    )
    ax.set_ylabel('')
    st.pyplot(fig)

with tab2:
    fig, ax = plt.subplots()
    filtered_df.groupby('Categoria')['Valor'].sum().sort_values().plot(
        kind='barh',
        ax=ax,
        color='skyblue'
    )
    ax.set_xlabel("Valor Total (R$)")
    st.pyplot(fig)

# Tabela detalhada
st.subheader("Detalhamento por Subcategoria")
categoria_selecionada = st.selectbox(
    "Selecione uma Categoria:",
    options=filtered_df['Categoria'].unique()
)

tabela = filtered_df[filtered_df['Categoria'] == categoria_selecionada]
tabela = tabela.groupby(['Subcategoria'])['Valor'].sum().reset_index()
st.dataframe(tabela.sort_values('Valor', ascending=True))

conn.close()