import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import talib as ta
import joblib
import time
from datetime import datetime, timedelta
import os
import json

# --- PARÂMETROS GLOBAIS ---
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
VOLUME = 0.01  # Volume do lote. CUIDADO AO MUDAR!
MAGIC_NUMBER = 123456 # ID único para as ordens deste robô
MODEL_FILE = "modelo_ia_trade.joblib"

# --- ARQUIVOS DE HISTÓRICO PARA APRENDIZADO CONTÍNUO ---
HISTORICO_FILE = "historico_trades_executados.csv"
OPEN_TRADES_FILE = "trades_abertos.json"

# --- FUNÇÕES AUXILIARES ---
def calculate_features(df):
    """Calcula todos os indicadores e features necessários para a IA."""
    df['time_dt'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time_dt', inplace=True)

    # Pivots
    daily_df = df.resample('D').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    prev_day = daily_df.shift(1)
    pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
    r1 = 2 * pivot - prev_day['low']
    s1 = 2 * pivot - prev_day['high']
    r2 = pivot + (prev_day['high'] - prev_day['low'])
    s2 = pivot - (prev_day['high'] - prev_day['low'])
    r3 = prev_day['high'] + 2 * (pivot - prev_day['low'])
    s3 = prev_day['low'] - 2 * (prev_day['high'] - prev_day['low'])
    pivots_df = pd.DataFrame({'pivot': pivot, 'r1': r1, 's1': s1, 'r2': r2, 's2': s2, 'r3': r3, 's3': s3})
    df = pd.merge_asof(df, pivots_df, left_index=True, right_index=True)
    df.reset_index(inplace=True)

    # Indicadores TA-Lib
    df['ema50'] = ta.EMA(df['close'], timeperiod=50)
    df['ema200'] = ta.EMA(df['close'], timeperiod=200)
    df['atr14'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    df['engulfing'] = ta.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    df['hammer'] = ta.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    
    # Features de tempo
    df['hour'] = df['time_dt'].dt.hour
    df['day_of_week'] = df['time_dt'].dt.dayofweek
    
    # Features de sessão (aproximado, GMT)
    df['session_asia'] = ((df['hour'] >= 0) & (df['hour'] <= 8)).astype(int)
    df['session_london'] = ((df['hour'] >= 7) & (df['hour'] <= 16)).astype(int)
    df['session_ny'] = ((df['hour'] >= 12) & (df['hour'] <= 21)).astype(int)
    
    return df.dropna()

def place_order(symbol, order_type, volume, sl, tp):
    """Envia uma ordem de mercado para o MT5."""
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid,
        "sl": sl,
        "tp": tp,
        "magic": MAGIC_NUMBER,
        "comment": "Robo IA Trader v2",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Falha ao enviar ordem: {result.comment}")
        return None
    else:
        print(f"Ordem enviada com sucesso: Ticket #{result.order}")
        return result

def check_and_save_closed_trades():
    """Verifica trades fechados e salva seus dados para retreinamento."""
    if not os.path.exists(OPEN_TRADES_FILE):
        return

    try:
        with open(OPEN_TRADES_FILE, 'r') as f:
            open_trades = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        open_trades = {}

    if not open_trades:
        return

    # Busca por transações (deals) no histórico recente
    from_date = datetime.now() - timedelta(days=7) # Busca na última semana
    deals = mt5.history_deals_get(from_date, datetime.now())
    
    if deals is None or len(deals) == 0:
        return

    closed_tickets = set()
    for deal in deals:
        # entry=1 significa uma transação de saída (fechamento de posição)
        if deal.entry == 1 and deal.magic == MAGIC_NUMBER:
            ticket_id = str(deal.position_id)
            if ticket_id in open_trades:
                print(f"TRADE FECHADO DETECTADO: Ticket #{ticket_id}. Salvando resultado...")
                
                trade_data = open_trades[ticket_id]
                # Adiciona o resultado real: 1 para lucro, 0 para prejuízo/breakeven
                trade_data['target'] = 1 if deal.profit > 0 else 0
                
                # Converte para DataFrame para salvar no CSV
                df_historico = pd.DataFrame([trade_data])
                
                # Garante que o arquivo de histórico tenha cabeçalho apenas na primeira vez
                file_exists = os.path.exists(HISTORICO_FILE)
                df_historico.to_csv(HISTORICO_FILE, mode='a', header=not file_exists, index=False)
                
                print(f"Resultado do trade #{ticket_id} salvo em {HISTORICO_FILE}")
                closed_tickets.add(ticket_id)

    # Limpa o JSON, removendo os trades que já foram processados
    remaining_trades = {k: v for k, v in open_trades.items() if k not in closed_tickets}
    with open(OPEN_TRADES_FILE, 'w') as f:
        json.dump(remaining_trades, f, indent=4)

# --- LÓGICA PRINCIPAL DO ROBÔ ---
def run_bot():
    print("Iniciando Robô Trader com IA (v2 - Aprendizado Contínuo)...")
    print(f"Carregando modelo de IA de '{MODEL_FILE}'...")
    try:
        model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        print(f"ERRO: Modelo '{MODEL_FILE}' não encontrado. Treine o modelo primeiro.")
        return

    features_order = model.feature_names_in_

    while True:
        try:
            if not mt5.initialize():
                print("Falha na conexão com MT5. Tentando novamente em 1 min...")
                time.sleep(60)
                continue
            
            # --- APRENDIZADO CONTÍNUO: VERIFICAR TRADES FECHADOS ---
            check_and_save_closed_trades()

            # 1. Verificar se já existe uma posição aberta por este robô
            positions = mt5.positions_get(symbol=SYMBOL)
            my_positions = [p for p in positions if p.magic == MAGIC_NUMBER] if positions else []
            if my_positions:
                print(f"Já existe uma posição aberta para {SYMBOL} (Ticket: {my_positions[0].ticket}). Aguardando...")
                mt5.shutdown()
                time.sleep(300) # Espera 5 minutos se já tem trade aberto
                continue

            # 2. Obter e processar dados
            rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 300)
            df = pd.DataFrame(rates)
            df_features = calculate_features(df)

            if df_features.empty:
                print("Não há dados suficientes para calcular features. Aguardando...")
                mt5.shutdown()
                time.sleep(60)
                continue

            # 3. Verificar o sinal na última vela completa
            last_candle = df_features.iloc[-2] # Usamos a penúltima vela (a última fechada)
            signal = 0
            atr = last_candle['atr14']

            # Condições de Compra
            if (last_candle['ema50'] > last_candle['ema200'] and
               ((last_candle['engulfing'] > 0) or (last_candle['hammer'] > 0)) and
               ((abs(last_candle['low'] - last_candle['s1']) < atr * 0.7) or
                (abs(last_candle['low'] - last_candle['s2']) < atr * 0.7))):
                signal = 1

            # Condições de Venda
            elif (last_candle['ema50'] < last_candle['ema200'] and
                  (last_candle['engulfing'] < 0) and
                  ((abs(last_candle['high'] - last_candle['r1']) < atr * 0.7) or
                   (abs(last_candle['high'] - last_candle['r2']) < atr * 0.7))):
                signal = -1

            # 4. Se houver sinal, consultar a IA
            if signal != 0:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sinal de {'COMPRA' if signal == 1 else 'VENDA'} detectado!")
                
                live_features_dict = last_candle.to_dict()
                features_df = pd.DataFrame([live_features_dict])[features_order]

                prediction = model.predict(features_df)[0]
                probability = model.predict_proba(features_df)[0]

                print(f"IA prevê: {'SUCESSO' if prediction == 1 else 'FALHA'} com probabilidade de {max(probability)*100:.2f}%")

                # 5. Se a IA aprovar, enviar a ordem
                if prediction == 1:
                    price_info = mt5.symbol_info_tick(SYMBOL)
                    if signal == 1: # Compra
                        sl = last_candle['low'] - atr
                        tp = price_info.ask + (price_info.ask - sl) * 1.5 # Risco/Retorno 1:1.5
                        result = place_order(SYMBOL, mt5.ORDER_TYPE_BUY, VOLUME, sl, tp)
                    elif signal == -1: # Venda
                        sl = last_candle['high'] + atr
                        tp = price_info.bid - (sl - price_info.bid) * 1.5 # Risco/Retorno 1:1.5
                        result = place_order(SYMBOL, mt5.ORDER_TYPE_SELL, VOLUME, sl, tp)
                    
                    # --- APRENDIZADO CONTÍNUO: SALVAR TRADE ABERTO ---
                    if result:
                        try:
                            with open(OPEN_TRADES_FILE, 'r') as f:
                                open_trades = json.load(f)
                        except (json.JSONDecodeError, FileNotFoundError):
                            open_trades = {}
                        
                        ticket_id = str(result.order)
                        # Remove colunas que não são features para salvar
                        features_to_save = {k: v for k, v in live_features_dict.items() if k in features_order}
                        open_trades[ticket_id] = features_to_save
                        
                        with open(OPEN_TRADES_FILE, 'w') as f:
                            json.dump(open_trades, f, indent=4)
                        print(f"Trade #{ticket_id} salvo em {OPEN_TRADES_FILE} para futuro rastreamento.")

                else:
                    print("Decisão da IA: Não operar.")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sem sinal. Aguardando...", end='\r')

            mt5.shutdown()
            time.sleep(60)

        except Exception as e:
            print(f"\nOcorreu um erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)

if __name__ == "__main__":
    run_bot()