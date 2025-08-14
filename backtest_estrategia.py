import backtrader as bt
import pandas as pd
import joblib
from datetime import datetime

# --- CLASSE DA ESTRATÉGIA PARA BACKTRADER ---
class EstrategiaIA(bt.Strategy):
    params = (
        ('ema_short', 50),
        ('ema_long', 200),
        ('atr_period', 14),
    )

    def __init__(self):
        """Inicializa a estratégia, indicadores e o modelo de IA."""
        print("--- Inicializando Estratégia para Backtest ---")
        # Carregar o modelo de IA treinado
        try:
            self.model = joblib.load('modelo_ia_trade.joblib')
            self.features_order = self.model.feature_names_in_
            print("Modelo de IA carregado com sucesso.")
        except FileNotFoundError:
            print("ERRO CRÍTICO: Arquivo 'modelo_ia_trade.joblib' não encontrado!")
            self.model = None

        # Referências para as linhas de dados
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # Indicadores do Backtrader
        self.ema50 = bt.indicators.EMA(self.datas[0], period=self.p.ema_short)
        self.ema200 = bt.indicators.EMA(self.datas[0], period=self.p.ema_long)
        self.atr14 = bt.indicators.ATR(self.datas[0], period=self.p.atr_period)
        
        # Padrões de vela (usaremos as colunas do CSV diretamente, pois são complexos de recriar)
        self.engulfing = self.datas[0].engulfing
        self.hammer = self.datas[0].hammer

        # Pivot points (também usaremos as colunas do CSV)
        self.s1 = self.datas[0].s1
        self.s2 = self.datas[0].s2
        self.r1 = self.datas[0].r1
        self.r2 = self.datas[0].r2

        self.order = None

    def notify_order(self, order):
        """Notificação de status da ordem."""
        if order.status in [order.Submitted, order.Accepted]:
            return # Ignora ordens submetidas/aceitas

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
            return # Se já temos uma ordem pendente ou o modelo não carregou, não faz nada

        # Apenas opera se não tiver posição aberta
        if not self.position:
            signal = 0
            atr_val = self.atr14[0]

            # Condições de Compra
            if (self.ema50[0] > self.ema200[0] and
               (self.engulfing[0] > 0 or self.hammer[0] > 0) and
               ((abs(self.datalow[0] - self.s1[0]) < atr_val * 0.7) or 
                (abs(self.datalow[0] - self.s2[0]) < atr_val * 0.7))):
                signal = 1

            # Condições de Venda
            elif (self.ema50[0] < self.ema200[0] and
                  self.engulfing[0] < 0 and
                  ((abs(self.datahigh[0] - self.r1[0]) < atr_val * 0.7) or 
                   (abs(self.datahigh[0] - self.r2[0]) < atr_val * 0.7))):
                signal = -1

            # Se um sinal técnico foi gerado, consultar a IA
            if signal != 0:
                # Montar o DataFrame com os dados da vela ATUAL para a previsão
                current_candle_data = {
                    'open': self.dataopen[0],
                    'high': self.datahigh[0],
                    'low': self.datalow[0],
                    'close': self.dataclose[0],
                    's1': self.s1[0], 's2': self.s2[0], 's3': self.datas[0].s3[0],
                    'r1': self.r1[0], 'r2': self.r2[0], 'r3': self.datas[0].r3[0],
                    'pivot': self.datas[0].pivot[0],
                    'ema50': self.ema50[0],
                    'ema200': self.ema200[0],
                    'atr14': self.atr14[0],
                    'engulfing': self.engulfing[0],
                    'hammer': self.hammer[0],
                    'hour': self.datas[0].datetime.time().hour,
                    'day_of_week': self.datas[0].datetime.date().weekday(),
                    'session_asia': 1 if 0 <= self.datas[0].datetime.time().hour <= 8 else 0,
                    'session_london': 1 if 7 <= self.datas[0].datetime.time().hour <= 16 else 0,
                    'session_ny': 1 if 12 <= self.datas[0].datetime.time().hour <= 21 else 0,
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

    # Carregar os dados com indicadores
    # CORREÇÃO: Usar a coluna 'time' como índice e parsear como datas
    df = pd.read_csv('dados_com_indicadores.csv', parse_dates=['time'], index_col='time')

    # Adicionar os dados ao Cerebro
    data = bt.feeds.PandasData(dataname=df)
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