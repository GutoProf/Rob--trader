import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import talib as ta
import joblib
import time
from datetime import datetime

# --- PARÂMETROS GLOBAIS ---
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
VOLUME = 0.01  # Volume do lote. CUIDADO AO MUDAR!
MAGIC_NUMBER = 123456 # ID único para as ordens deste robô
MODEL_FILE = "modelo_ia_trade.joblib"

# --- FUNÇÕES AUXILIARES ---
def calculate_features(df):
    """Calcula todos os indicadores e features necessários para a IA."""
    # Pivots (simplificado para tempo real)
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    daily_df = df.resample('D').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    prev_day = daily_df.shift(1)
    pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
    r1 = 2 * pivot - prev_day['low']
    s1 = 2 * pivot - prev_day['high']
    r2 = pivot + (prev_day['high'] - prev_day['low'])
    s2 = pivot - (prev_day['high'] - prev_day['low'])
    r3 = prev_day['high'] + 2 * (pivot - prev_day['low'])
    s3 = prev_day['low'] - 2 * (pivot - prev_day['high'])
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
    df['time_dt'] = pd.to_datetime(df['time'], unit='s')
    df['hour'] = df['time_dt'].dt.hour
    df['day_of_week'] = df['time_dt'].dt.dayofweek
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
        "comment": "Robo IA Trader",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Falha ao enviar ordem: {result.comment}")
    else:
        print(f"Ordem enviada com sucesso: Ticket #{result.order}")
    return result

# --- LÓGICA PRINCIPAL DO ROBÔ ---
def run_bot():
    print("Iniciando Robô Trader com IA...")
    print("Carregando modelo de IA...")
    try:
        model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        print(f"Erro: Modelo '{MODEL_FILE}' não encontrado. Treine o modelo primeiro.")
        return

    features_order = model.feature_names_in_

    while True:
        try:
            if not mt5.initialize():
                print("Falha na conexão com MT5. Tentando novamente em 1 min...")
                time.sleep(60)
                continue

            # 1. Verificar se já existe uma posição aberta por este robô
            positions = mt5.positions_get(symbol=SYMBOL)
            if positions and any(p.magic == MAGIC_NUMBER for p in positions):
                print(f"Já existe uma posição aberta para {SYMBOL}. Aguardando...")
                mt5.shutdown()
                time.sleep(60)
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
            last_candle = df_features.iloc[-1]
            signal = 0
            atr = last_candle['atr14']

            # Condições de Compra
            if (last_candle['ema50'] > last_candle['ema200'] and \
               ((last_candle['engulfing'] > 0) or (last_candle['hammer'] > 0)) and \
               ((abs(last_candle['low'] - last_candle['s1']) < atr * 0.5) or \
                (abs(last_candle['low'] - last_candle['s2']) < atr * 0.5))):
                signal = 1

            # Condições de Venda
            elif (last_candle['ema50'] < last_candle['ema200'] and \
                  (last_candle['engulfing'] < 0) and \
                  ((abs(last_candle['high'] - last_candle['r1']) < atr * 0.5) or \
                   (abs(last_candle['high'] - last_candle['r2']) < atr * 0.5))):
                signal = -1

            # 4. Se houver sinal, consultar a IA
            if signal != 0:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sinal de {'COMPRA' if signal == 1 else 'VENDA'} detectado!")
                
                live_features = last_candle.to_dict()
                live_features['signal'] = signal
                features_df = pd.DataFrame([live_features])[features_order]

                prediction = model.predict(features_df)[0]
                probability = model.predict_proba(features_df)[0]

                print(f"IA prevê: {'SUCESSO' if prediction == 1 else 'FALHA'} com probabilidade de {max(probability)*100:.2f}%")

                # 5. Se a IA aprovar, enviar a ordem
                if prediction == 1:
                    if signal == 1:
                        sl = last_candle['s1']
                        tp = last_candle['r1']
                        place_order(SYMBOL, mt5.ORDER_TYPE_BUY, VOLUME, sl, tp)
                    elif signal == -1:
                        sl = last_candle['r1']
                        tp = last_candle['s1']
                        place_order(SYMBOL, mt5.ORDER_TYPE_SELL, VOLUME, sl, tp)
                else:
                    print("Decisão da IA: Não operar.")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sem sinal. Aguardando...", end='\r')

            mt5.shutdown()
            time.sleep(60) # Espera 1 minuto para a próxima verificação

        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
