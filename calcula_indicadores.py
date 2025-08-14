import pandas as pd

# --- Arquivos ---
INPUT_FILE = "xauusd_h1_data.csv"
OUTPUT_FILE = "dados_com_indicadores.csv"

def calculate_indicators():
    """
    Lê os dados brutos e salva apenas as colunas OHLCV e volume em um novo arquivo CSV.
    """
    print(f"Lendo dados de {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, parse_dates=['time'])
    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")
        print("Por favor, execute o script 'coleta_dados.py' primeiro.")
        return

    print("Preparando dados brutos para backtest...")

    # Seleciona apenas as colunas necessárias para o backtest (OHLCV + volumes)
    df_output = df[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'real_volume']]

    # Remove quaisquer linhas com valores NaN
    df_output.dropna(inplace=True)

    # --- Salvando o resultado ---
    try:
        df_output.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSucesso! {len(df_output)} registros processados e salvos em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")

if __name__ == "__main__":
    calculate_indicators()
