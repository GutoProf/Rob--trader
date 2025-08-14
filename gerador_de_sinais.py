import pandas as pd
import numpy as np
import talib as ta

# --- Arquivos ---
INPUT_FILE = "dados_com_indicadores.csv"
OUTPUT_FILE = "dataset_final_para_ia.csv"

# --- Parâmetros da Simulação ---
# Quantas velas no futuro olhamos para ver se o trade deu certo/errado
LOOK_FORWARD_BARS = 24 # 24 horas

def get_trade_outcome(df, index, signal):
    """
    Verifica o resultado de um trade iniciado em um determinado índice.
    Retorna 1 para vitória (Take Profit), 0 para derrota (Stop Loss).
    Retorna np.nan se o resultado não for decidido dentro de LOOK_FORWARD_BARS.
    """
    entry_price = df.at[index, 'close']
    
    if signal == 1: # Sinal de Compra
        take_profit = df.at[index, 'r1'] # Alvo no R1
        stop_loss = df.at[index, 's1']   # Stop no S1
        # Se o preço já está acima do R1 ou abaixo do S1, o sinal é inválido
        if entry_price >= take_profit or entry_price <= stop_loss:
            return np.nan

        future_bars = df.iloc[index + 1 : index + 1 + LOOK_FORWARD_BARS]
        for i, bar in future_bars.iterrows():
            if bar['high'] >= take_profit: return 1 # Vitória
            if bar['low'] <= stop_loss: return 0   # Derrota

    elif signal == -1: # Sinal de Venda
        take_profit = df.at[index, 's1'] # Alvo no S1
        stop_loss = df.at[index, 'r1']   # Stop no R1
        # Se o preço já está abaixo do S1 ou acima do R1, o sinal é inválido
        if entry_price <= take_profit or entry_price >= stop_loss:
            return np.nan

        future_bars = df.iloc[index + 1 : index + 1 + LOOK_FORWARD_BARS]
        for i, bar in future_bars.iterrows():
            if bar['low'] <= take_profit: return 1  # Vitória
            if bar['high'] >= stop_loss: return 0  # Derrota
            
    return np.nan # Trade não resolvido

def generate_signals():
    """
    Gera o dataset final com sinais de trading e o resultado (target) para a IA.
    """
    print(f"Lendo dados de {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, parse_dates=['time'])
    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")
        return

    print("Gerando sinais da estratégia base...")

    # --- 1. Identificar Padrões de Vela ---
    df['engulfing'] = ta.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    df['hammer'] = ta.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    # Adicione outros padrões se desejar (ex: CDLMORNINGSTAR, CDLEVENINGSTAR)

    # --- 2. Definir Condições de Confluência ---
    atr = df['atr14']
    
    # Condições de Compra
    buy_trend = df['ema50'] > df['ema200']
    buy_candle = (df['engulfing'] > 0) | (df['hammer'] > 0)
    # Preço próximo a um suporte (S1, S2, ou S3)
    buy_near_support = (abs(df['low'] - df['s1']) < atr * 0.5) | \
                       (abs(df['low'] - df['s2']) < atr * 0.5) | \
                       (abs(df['low'] - df['s3']) < atr * 0.5)

    # Condições de Venda
    sell_trend = df['ema50'] < df['ema200']
    sell_candle = (df['engulfing'] < 0) # Engolfo de baixa
    # Preço próximo a uma resistência (R1, R2, ou R3)
    sell_near_resistance = (abs(df['high'] - df['r1']) < atr * 0.5) | \
                         (abs(df['high'] - df['r2']) < atr * 0.5) | \
                         (abs(df['high'] - df['r3']) < atr * 0.5)

    # --- 3. Criar a coluna de Sinais ---
    df['signal'] = 0
    df.loc[buy_trend & buy_candle & buy_near_support, 'signal'] = 1
    df.loc[sell_trend & sell_candle & sell_near_resistance, 'signal'] = -1

    # --- 4. Calcular o Resultado (Target) para cada Sinal ---
    print("Calculando resultado dos trades (target para a IA)...")
    signal_indices = df[df['signal'] != 0].index
    outcomes = [get_trade_outcome(df, i, df.at[i, 'signal']) for i in signal_indices]
    df.loc[signal_indices, 'target'] = outcomes

    # --- 5. Preparar o Dataset Final ---
    # Filtramos apenas os momentos em que houve um sinal e o resultado foi definido
    final_df = df[df['target'].notna()].copy()
    final_df['target'] = final_df['target'].astype(int)

    # Adicionar features de tempo, que podem ser úteis para a IA
    final_df['hour'] = final_df['time'].dt.hour
    final_df['day_of_week'] = final_df['time'].dt.dayofweek

    # Selecionar colunas que a IA usará como features
    feature_columns = [
        'open', 'high', 'low', 'close', 'real_volume', # Dados do preço
        'pivot', 'r1', 's1', 'r2', 's2', 'r3', 's3', # Níveis de Pivot
        'ema50', 'ema200', 'atr14', # Indicadores
        'engulfing', 'hammer', # Sinais de vela
        'hour', 'day_of_week', # Features de tempo
        'signal', # O sinal que a estratégia deu
        'target' # O resultado que a IA deve prever
    ]
    final_df = final_df[feature_columns]

    print(f"Foram encontrados {len(final_df)} sinais de trade válidos.")

    # --- Salvando o resultado ---
    try:
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSucesso! Dataset final para IA salvo em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")

if __name__ == "__main__":
    generate_signals()
