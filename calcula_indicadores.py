import pandas as pd
import talib as ta

# --- Arquivos ---
INPUT_FILE = "xauusd_h1_data.csv"
OUTPUT_FILE = "dados_com_indicadores.csv"

def calculate_indicators():
    """
    Lê os dados brutos, calcula indicadores técnicos (Pivots, EMAs, ATR, Padrões de Vela)
    e features de tempo, salvando o resultado em um novo arquivo CSV.
    """
    print(f"Lendo dados de {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, parse_dates=['time'])
    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")
        print("Por favor, execute o script 'coleta_dados.py' primeiro.")
        return

    print("Calculando indicadores e features de tempo...")

    # --- Cálculo dos Pivot Points ---
    df.set_index('time', inplace=True)
    daily_df = df.resample('D').agg({
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })

    prev_day = daily_df.shift(1)

    pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
    r1 = 2 * pivot - prev_day['low']
    s1 = 2 * pivot - prev_day['high']
    r2 = pivot + (prev_day['high'] - prev_day['low'])
    s2 = pivot - (prev_day['high'] - prev_day['low'])
    r3 = prev_day['high'] + 2 * (pivot - prev_day['low'])
    s3 = prev_day['low'] - 2 * (prev_day['high'] - prev_day['low'])

    pivots_df = pd.DataFrame({
        'pivot': pivot,
        'r1': r1, 's1': s1,
        'r2': r2, 's2': s2,
        'r3': r3, 's3': s3
    })
    
    df.sort_index(inplace=True)
    pivots_df.sort_index(inplace=True)
    df = pd.merge_asof(df, pivots_df, left_index=True, right_index=True)
    df.reset_index(inplace=True) # Traz a coluna 'time' de volta do índice

    # --- Cálculo de Indicadores TA-Lib ---
    # Certifique-se de que não há NaNs nas colunas usadas pelo TA-Lib
    df.dropna(inplace=True)
    if df.empty:
        print("O DataFrame ficou vazio após remover NaNs. Verifique os dados de entrada.")
        return

    df['ema50'] = ta.EMA(df['close'], timeperiod=50)
    df['ema200'] = ta.EMA(df['close'], timeperiod=200)
    df['atr14'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)

    # Padrões de Vela
    df['engulfing'] = ta.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    df['hammer'] = ta.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])

    # --- Features de Tempo e Sessão ---
    # Garante que 'time' é datetime para extrair hora e dia da semana
    df['time'] = pd.to_datetime(df['time'])
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    
    # Features de sessão (aproximado, GMT)
    df['session_asia'] = ((df['hour'] >= 0) & (df['hour'] <= 8)).astype(int)
    df['session_london'] = ((df['hour'] >= 7) & (df['hour'] <= 16)).astype(int)
    df['session_ny'] = ((df['hour'] >= 12) & (df['hour'] <= 21)).astype(int)

    # Remove quaisquer linhas com valores NaN que foram criadas pelos indicadores
    df.dropna(inplace=True)

    # --- Salvando o resultado ---
    try:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSucesso! {len(df)} registros processados e salvos em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")

if __name__ == "__main__":
    calculate_indicators()