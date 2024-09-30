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

# Criação das colunas de valores por KG
def feature_engineering(df):
    df['Valor por KG FOB'] = df['VL_FOB'] / df['KG_LIQUIDO']
    df['Valor por KG FOB com Frete'] = (df['VL_FOB'] + df['VL_FRETE']) / df['KG_LIQUIDO']
    df['Valor por KG FOB com Seguro'] = (df['VL_FOB'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG FOB com Frete e Seguro'] = (df['VL_FOB'] + df['VL_FRETE'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG com Frete e Seguro'] = (df['VL_FRETE'] + df['VL_SEGURO']) / df['KG_LIQUIDO']
    df['Valor por KG Frete'] = df['VL_FRETE'] / df['KG_LIQUIDO']
    df['Valor por KG Seguro'] = df['VL_SEGURO'] / df['KG_LIQUIDO']
    return df

# Função para conversão de dólar para real
def convert_to_brl(row, value_column):
    try:
        return c.convert(row[value_column], 'USD', 'BRL', date=row['data'])
    except Exception:
        return float('nan')

# Função para realizar o download do CSV diretamente do site do governo
@st.cache
def get_df_23_24(url_23, url_24, sep):
    df_1 = pd.read_csv(StringIO(requests.get(url_23, verify=False).text), sep=sep)
    df_2 = pd.read_csv(StringIO(requests.get(url_24, verify=False).text), sep=sep)
    return pd.concat([df_1, df_2])

# Filtrar os dados para apenas o produto e estado solicitados
def filter_data(df):
    return df[(df['CO_NCM'] == 33030010) & (df['SG_UF_NCM'] == 'SP')].copy()

# Filtros de seleção
def apply_filters(df):
    co_via_options = df['CO_VIA'].unique()
    co_pais_options = df['CO_PAIS'].unique()
    selected_co_via = st.sidebar.selectbox("Selecione o código da via de transporte:", co_via_options)
    selected_co_pais = st.sidebar.selectbox("Selecione o código do país exportador:", co_pais_options)
    return df[(df['CO_VIA'] == selected_co_via) & (df['CO_PAIS'] == selected_co_pais)]

# Agrupando os valores por data
def create_grouped_data(df):
    df['data'] = pd.to_datetime(df['CO_ANO'].astype(str) + '-' + df['CO_MES'].astype(str) + '-01')
    return df.groupby('data').sum().reset_index()


def plot_data(grouped_data, selected_variable):
    plt.figure(figsize=(40, 20))
    sns.set(style="whitegrid")

    # Gráfico de linha
    sns.lineplot(data=grouped_data, x='data', y=selected_variable, marker='o', color='lightblue', linewidth=2.5)

    # Anotando os pontos com ajuste de posição
    for index, row in grouped_data.iterrows():
        plt.text(row['data'], row[selected_variable] + (index % 2) * 0.5, f'{row[selected_variable]:.2f}',
                 horizontalalignment='left', size=16, color='black', weight='semibold')

    plt.title(f'{selected_variable} de Perfume (extratos) Importado para São Paulo', fontsize=30, weight='bold')
    plt.xlabel('Data', fontsize=26)
    plt.ylabel(selected_variable, fontsize=26)
    plt.xticks(rotation=45)
    plt.xticks(fontsize=22, rotation=45)
    plt.yticks(fontsize=22)
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.grid(color='grey', linestyle='--', linewidth=0.7, alpha=0.7)
    plt.tight_layout()

    # Exibindo o gráfico
    st.pyplot(plt)


def main():
    url_23 = 'https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2023.csv'
    url_24 = 'https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2024.csv'
    
    df = get_df_23_24(url_23, url_24, ';')

    if st.sidebar.button("Atualizar Dados"):
        df = get_df_23_24(url_23, url_24, ';')
        st.success("Dados atualizados com sucesso!")

    df_filtered = filter_data(df)
    df_filtered = apply_filters(df_filtered)
    df_filtered = feature_engineering(df_filtered)
    grouped_data = create_grouped_data(df_filtered)

    variables = [
        'Valor por KG FOB',
        'Valor por KG FOB com Frete',
        'Valor por KG FOB com Seguro',
        'Valor por KG FOB com Frete e Seguro',
        'Valor por KG com Frete e Seguro',
        'Valor por KG Frete',
        'Valor por KG Seguro'
    ]
    
    selected_variable = st.sidebar.selectbox("Selecione a variável para plotar:", variables)
    currency_option = st.sidebar.selectbox("Escolha a moeda:", ["Dólar (USD)", "Real (BRL)"])

    if currency_option == "Real (BRL)":
        for variable in variables:
            grouped_data[variable] = grouped_data.apply(convert_to_brl, value_column=variable, axis=1)

    plot_data(grouped_data, selected_variable)

if __name__ == "__main__":
    main()

