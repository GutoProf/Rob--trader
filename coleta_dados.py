import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

# --- Parâmetros ---
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
YEARS_OF_DATA = 5

# --- Nome do Arquivo de Saída ---
# --- Nome do Arquivo de Saída ---
OUTPUT_FILE = f"xauusd_h1_data.csv"

def collect_data():
    """
    Conecta ao MetaTrader 5, baixa o histórico de preços para um símbolo
    e o salva em um arquivo CSV.
    """
    print("Iniciando processo de coleta de dados...")

    # Inicializa a conexão com o MetaTrader 5
    if not mt5.initialize():
        print("Falha na inicialização do MetaTrader 5. Verifique se o terminal está aberto.")
        mt5.shutdown()
        return

    print(f"Conectado com sucesso ao MetaTrader 5. Versão: {mt5.version()}")

    # Calcula a data de início
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * YEARS_OF_DATA)

    print(f"Buscando dados para {SYMBOL} de {start_date.date()} até {end_date.date()}...")

    # Busca os dados de preços
    rates = mt5.copy_rates_range(SYMBOL, TIMEFRAME, start_date, end_date)

    # Encerra a conexão
    mt5.shutdown()
    print("Conexão com o MetaTrader 5 encerrada.")

    if rates is None or len(rates) == 0:
        print(f"Não foi possível obter os dados para {SYMBOL}. Verifique o nome do símbolo e o período.")
        return

    # Converte para DataFrame do pandas
    df = pd.DataFrame(rates)

    # Converte a coluna 'time' para um formato de data legível
    df['time'] = pd.to_datetime(df['time'], unit='s')

    # Remove a coluna 'spread' se ela existir, pois geralmente não é útil para análise de backtest
    if 'spread' in df.columns:
        df = df.drop(columns=['spread'])
        
    # Salva em um arquivo CSV
    try:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSucesso! {len(df)} registros de dados foram salvos em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")

if __name__ == "__main__":
    collect_data()
