import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import matplotlib.dates as mdates
import requests
from io import StringIO
from currency_converter import CurrencyConverter

# Inicializando o conversor de câmbio. O parâmetro "fallback_on_missing_rate" foi utilizado para,
 # caso o câmbio não seja encontrado na data, seja utilizado uma interpolação linear dos valores mais próximos.
c = CurrencyConverter(fallback_on_missing_rate=True)

# Função de criação de variáveis
def feature_engineering(df):
    df['Valor por KG FOB'] = df['VL_FOB'] / df['KG_LIQUIDO']
    df['Valor por KG FOB com Frete'] = (df['VL_FOB'] + df['VL_FRETE']) / df['KG_LIQUIDO']
    df['Valor por KG FOB com Seguro'] = (df['VL_FOB'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG FOB com Frete e Seguro'] = (df['VL_FOB'] + df['VL_FRETE'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG com Frete e Seguro'] = (df['VL_FRETE'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG Frete'] = df['VL_FRETE'] / df['KG_LIQUIDO']
    df['Valor por KG Seguro'] = df['VL_SEGURO'] / df['KG_LIQUIDO']
    return df

# Função para converter valores de USD para BRL
def convert_to_brl(row, value_column):
    try:
        return c.convert(row[value_column], 'USD', 'BRL', date=row['data'])
    except Exception as e:
        # Se não conseguir converter, retornar NaN
        return float('nan')


@st.cache
def get_df_23_24(url_23, url_24, sep):
    response_1 = requests.get(url_23, verify=False)
    data_1 = StringIO(response_1.text)
    df_1 = pd.read_csv(data_1, sep=sep)

    response_2 = requests.get(url_24, verify=False)
    data_2 = StringIO(response_2.text)
    df_2 = pd.read_csv(data_2, sep=sep)

    df = pd.concat([df_1, df_2])
    return df

# URLs dos dados
url_23 = 'https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2023.csv'
url_24 = 'https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2024.csv'

# Carregar os dados inicialmente com cache
df = get_df_23_24(url_23, url_24, ';')

# Botão para atualizar os dados
if st.sidebar.button("Atualizar Dados"):
    df = get_df_23_24(url_23, url_24, ';')
    st.success("Dados atualizados com sucesso!")

# Filtros
co_via_options = df['CO_VIA'].unique()
co_pais_options = df['CO_PAIS'].unique()

selected_co_via = st.sidebar.selectbox("Selecione o código da via de transporte:", co_via_options)
selected_co_pais = st.sidebar.selectbox("Selecione o código do país exportador:", co_pais_options)

# Aplicando os filtros ao DataFrame
df_filtered = df[
    (df['CO_NCM'] == 33030010) &
    (df['SG_UF_NCM'] == 'SP') &
    (df['CO_VIA'] == selected_co_via) &
    (df['CO_PAIS'] == selected_co_pais)
].copy()

df_filtered = feature_engineering(df_filtered)
df_filtered['data'] = pd.to_datetime(df_filtered['CO_ANO'].astype(str) + '-' + df_filtered['CO_MES'].astype(str) + '-01')

# Agrupando os dados por data
grouped_data = df_filtered.groupby('data').sum().reset_index()

# Lista de variáveis para o filtro
variables = [
    'Valor por KG FOB',
    'Valor por KG FOB com Frete',
    'Valor por KG FOB com Seguro',
    'Valor por KG FOB com Frete e Seguro',
    'Valor por KG com Frete e Seguro',
    'Valor por KG Frete',
    'Valor por KG Seguro'
]

# Filtro para seleção da variável na barra lateral
selected_variable = st.sidebar.selectbox("Selecione a variável para plotar:", variables)

# Filtro para selecionar a moeda
currency_option = st.sidebar.selectbox("Escolha a moeda:", ["Dólar (USD)", "Real (BRL)"])

# Se a moeda selecionada for Real, converter os valores
if currency_option == "Real (BRL)":
    for variable in variables:
        grouped_data[variable] = grouped_data.apply(convert_to_brl, value_column=variable, axis=1)

# Criando o gráfico
plt.figure(figsize=(12, 6))
sns.set(style="whitegrid")  # Estilo do gráfico
sns.lineplot(data=grouped_data, x='data', y=selected_variable, marker='o', color='lightblue', linewidth=2.5)

# Adicionando os valores nos pontos
for index, row in grouped_data.iterrows():
    plt.text(row['data'], row[selected_variable] + 0.5, f'{row[selected_variable]:.2f}',
             horizontalalignment='left', size='medium', color='black', weight='semibold')

plt.title(f'{selected_variable} de Perfume (extratos) por Ano e Mês', fontsize=25)
plt.xlabel('Data', fontsize=14)
plt.ylabel(selected_variable, fontsize=14)

# Definindo todos os meses como ticks no eixo x
plt.xticks(grouped_data['data'], rotation=45)

# Ajustando o formato do eixo x para exibir corretamente as datas
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))

plt.grid()
plt.tight_layout()

# Exibindo o gráfico no Streamlit
st.pyplot(plt)
