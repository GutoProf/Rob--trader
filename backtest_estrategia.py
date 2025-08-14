import backtrader as bt
import pandas as pd
import joblib
from datetime import datetime
import talib as ta # Usado para padrões de vela, pois backtrader não tem todos

# --- CLASSE DA ESTRATÉGIA PARA BACKTRADER ---
class EstrategiaIA(bt.Strategy):
    params = (
        ('ema_short', 50),
        ('ema_long', 200),
        ('atr_period', 14),
    )

    def __init__(self):
        """Inicializa a estratégia, indicadores e o modelo de IA."""
        print("--- Inicializando Estratégia para Backtest (Recalculando Indicadores) ---")
        # Carregar o modelo de IA treinado
        try:
            self.model = joblib.load('modelo_ia_trade.joblib')
            self.features_order = self.model.feature_names_in_
            print("Modelo de IA carregado com sucesso.")
        except FileNotFoundError:
            print("ERRO CRÍTICO: Arquivo 'modelo_ia_trade.joblib' não encontrado!")
            self.model = None

        # Referências para as linhas de dados OHLCV
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # --- Indicadores Backtrader ---
        self.ema50 = bt.indicators.EMA(self.datas[0], period=self.p.ema_short)
        self.ema200 = bt.indicators.EMA(self.datas[0], period=self.p.ema_long)
        self.atr14 = bt.indicators.ATR(self.datas[0], period=self.p.atr_period)

        # --- Variáveis para cálculo de Pivot Points (diário) ---
        # Removido '_name' pois causava TypeError
        self.daily_high = bt.indicators.Highest(self.datahigh, period=1, timeframe=bt.TimeFrame.Days)
        self.daily_low = bt.indicators.Lowest(self.datalow, period=1, timeframe=bt.TimeFrame.Days)
        self.daily_close = bt.indicators.Close(self.datas[0], timeframe=bt.TimeFrame.Days)

        self.pivot_val = bt.indicators.Generic(lambda x, y, z: (x + y + z) / 3, self.daily_high, self.daily_low, self.daily_close)
        self.r1_val = bt.indicators.Generic(lambda p, l: 2 * p - l, self.pivot_val, self.daily_low)
        self.s1_val = bt.indicators.Generic(lambda p, h: 2 * p - h, self.pivot_val, self.daily_high)
        self.r2_val = bt.indicators.Generic(lambda p, h, l: p + (h - l), self.pivot_val, self.daily_high, self.daily_low)
        self.s2_val = bt.indicators.Generic(lambda p, h, l: p - (h - l), self.pivot_val, self.daily_high, self.daily_low)
        self.r3_val = bt.indicators.Generic(lambda h, p, l: h + 2 * (p - l), self.daily_high, self.pivot_val, self.daily_low)
        self.s3_val = bt.indicators.Generic(lambda l, p, h: l - 2 * (h - p), self.daily_low, self.pivot_val, self.daily_high)

        self.order = None

    def notify_order(self, order):
        """Notificação de status da ordem."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                print(f'{self.datas[0].datetime.date(0)}: COMPRA EXECUTADA, Preço: {order.executed.price:.2f}')
            elif order.issell():
                print(f'{self.datas[0].datetime.date(0)}: VENDA EXECUTADA, Preço: {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'{self.datas[0].datetime.date(0)}: Ordem Cancelada/Rejeitada')

        self.order = None

    def next(self):
        """Lógica principal da estratégia, executada a cada vela."""
        if self.order or self.model is None:
            return

        # Garante que temos dados suficientes para todos os indicadores
        if len(self.dataopen) < max(self.p.ema_long, self.p.atr_period, 2): # 2 para pivots
            return

        signal = 0
        atr_val = self.atr14[0]

        # --- Cálculo de Padrões de Vela (usando TA-Lib diretamente) ---
        # backtrader tem alguns, mas TA-Lib é mais completo e já estamos usando
        # É importante passar arrays numpy para o TA-Lib
        open_arr = self.dataopen.get(size=max(self.p.ema_long, self.p.atr_period, 2))
        high_arr = self.datahigh.get(size=max(self.p.ema_long, self.p.atr_period, 2))
        low_arr = self.datalow.get(size=max(self.p.ema_long, self.p.atr_period, 2))
        close_arr = self.dataclose.get(size=max(self.p.ema_long, self.p.atr_period, 2))

        engulfing = ta.CDLENGULFING(open_arr, high_arr, low_arr, close_arr)[-1]
        hammer = ta.CDLHAMMER(open_arr, high_arr, low_arr, close_arr)[-1]

        # --- Features de Tempo e Sessão ---
        current_datetime = self.datas[0].datetime.datetime(0)
        current_hour = current_datetime.hour
        current_day_of_week = current_datetime.weekday()
        session_asia = 1 if 0 <= current_hour <= 8 else 0
        session_london = 1 if 7 <= current_hour <= 16 else 0
        session_ny = 1 if 12 <= current_hour <= 21 else 0

        # --- Condições de Compra ---
        if (self.ema50[0] > self.ema200[0] and
           (engulfing > 0 or hammer > 0) and
           ((abs(self.datalow[0] - self.s1_val[0]) < atr_val * 0.7) or 
            (abs(self.datalow[0] - self.s2_val[0]) < atr_val * 0.7))):
            signal = 1

        # --- Condições de Venda ---
        elif (self.ema50[0] < self.ema200[0] and
              engulfing < 0 and
              ((abs(self.datahigh[0] - self.r1_val[0]) < atr_val * 0.7) or 
               (abs(self.datahigh[0] - self.r2_val[0]) < atr_val * 0.7))):
            signal = -1

        # --- Se um sinal técnico foi gerado, consultar a IA ---
        if signal != 0:
            current_candle_data = {
                'open': self.dataopen[0],
                'high': self.datahigh[0],
                'low': self.datalow[0],
                'close': self.dataclose[0],
                's1': self.s1_val[0], 's2': self.s2_val[0], 's3': self.s3_val[0],
                'r1': self.r1_val[0], 'r2': self.r2_val[0], 'r3': self.r3_val[0],
                'pivot': self.pivot_val[0],
                'ema50': self.ema50[0],
                'ema200': self.ema200[0],
                'atr14': self.atr14[0],
                'engulfing': engulfing,
                'hammer': hammer,
                'hour': current_hour,
                'day_of_week': current_day_of_week,
                'session_asia': session_asia,
                'session_london': session_london,
                'session_ny': session_ny,
            }
            features_df = pd.DataFrame([current_candle_data])[self.features_order]
            
            prediction = self.model.predict(features_df)[0]

            # Se a IA prever sucesso (1), envia a ordem
            if prediction == 1:
                if signal == 1:
                    self.order = self.buy()
                elif signal == -1:
                    self.order = self.sell()

# --- FUNÇÃO PRINCIPAL PARA EXECUTAR O BACKTEST ---
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Carregar os dados brutos
    df = pd.read_csv('dados_com_indicadores.csv', parse_dates=['time'], index_col='time')
    
    # Renomear 'tick_volume' para 'volume' para compatibilidade com Backtrader
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)

    # Definir o feed de dados PandasData com uma subclasse explícita
    class CustomPandasData(bt.feeds.PandasData):
        # Apenas as colunas *adicionais* que não são OHLCV padrão
        lines = (
            # 'real_volume', # Removido
        )

        # Mapeamento de colunas padrão do Backtrader para os nomes no seu DataFrame
        # 'datetime' é tratado por index_col='time'
        # 'open', 'high', 'low', 'close' são assumidos como padrão
        volume = 'volume' # Já renomeado 'tick_volume' para 'volume' no df
        openinterest = -1 # Indica que não há 'openinterest'

    # Adicionar os dados ao Cerebro usando o feed personalizado
    data = CustomPandasData(dataname=df)
    cerebro.adddata(data)

    # Adicionar a estratégia
    cerebro.addstrategy(EstrategiaIA)

    # Configurações do Broker
    cerebro.broker.setcash(10000.0) # Saldo inicial
    cerebro.broker.setcommission(commission=0.0002) # Comissão de 0.02%
    cerebro.addsizer(bt.sizers.FixedSize, stake=1) # Tamanho fixo da posição

    # Adicionar Analisadores
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

    print("--- Iniciando Backtest da Estratégia ---")
    # Executar o backtest
    results = cerebro.run()
    strat = results[0]

    # Imprimir os resultados
    print("\n--- Resultados do Backtest ---")
    print(f"Valor Final do Portfólio: {cerebro.broker.getvalue():.2f}")
    
    # Resultados dos analisadores
    sharpe = strat.analyzers.sharpe_ratio.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trade_analysis = strat.analyzers.trade_analyzer.get_analysis()

    print(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A')}")
    print(f"Drawdown Máximo: {drawdown.max.drawdown:.2f}%")
    
    if trade_analysis.total.total > 0:
        print(f"Total de Trades: {trade_analysis.total.total}")
        print(f"Trades Vencedores: {trade_analysis.won.total}")
        print(f"Trades Perdedores: {trade_analysis.lost.total}")
        print(f"Média de Lucro por Trade: {trade_analysis.won.pnl.average:.2f}")
        print(f"Média de Perda por Trade: {trade_analysis.lost.pnl.average:.2f}")

    # Plotar o gráfico
    print("\nGerando gráfico do backtest...")
    cerebro.plot(style='candlestick')