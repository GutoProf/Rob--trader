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
        # Inicializando variáveis para armazenar os valores dos pivot points
        self.pivot_val = 0
        self.r1_val = 0
        self.s1_val = 0
        self.r2_val = 0
        self.s2_val = 0
        self.r3_val = 0
        self.s3_val = 0

        self.order = None
        
        # Variáveis para cálculo de métricas personalizadas
        self.trades = []
        self.won_trades = 0
        self.lost_trades = 0
        self.total_pnl = 0
        self.gross_profit = 0
        self.gross_loss = 0
        self.won_pnl_list = []
        self.lost_pnl_list = []

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

    def notify_trade(self, trade):
        """Notificação quando um trade é aberto ou fechado."""
        if trade.isclosed:
            # Um trade foi fechado
            pnl = trade.pnlcomm  # Lucro ou perda com comissão
            self.trades.append(pnl)
            self.total_pnl += pnl
            
            if pnl > 0:
                self.won_trades += 1
                self.gross_profit += pnl
                self.won_pnl_list.append(pnl)
            else:
                self.lost_trades += 1
                self.gross_loss += abs(pnl)
                self.lost_pnl_list.append(abs(pnl))
                
            print(f'{self.datas[0].datetime.date(0)}: Trade fechado, PNL: {pnl:.2f}')

    def next(self):
        """Lógica principal da estratégia, executada a cada vela."""
        if self.order or self.model is None:
            return

        # Garante que temos dados suficientes para todos os indicadores
        if len(self.dataopen) < max(self.p.ema_long, self.p.atr_period, 2): # 2 para pivots
            return

        # --- Cálculo de Padrões de Vela (usando TA-Lib diretamente) ---
        # backtrader tem alguns, mas TA-Lib é mais completo e já estamos usando
        # É importante passar arrays numpy para o TA-Lib
        import numpy as np
        open_arr = np.array(self.dataopen.get(size=max(self.p.ema_long, self.p.atr_period, 2)))
        high_arr = np.array(self.datahigh.get(size=max(self.p.ema_long, self.p.atr_period, 2)))
        low_arr = np.array(self.datalow.get(size=max(self.p.ema_long, self.p.atr_period, 2)))
        close_arr = np.array(self.dataclose.get(size=max(self.p.ema_long, self.p.atr_period, 2)))

        engulfing = ta.CDLENGULFING(open_arr, high_arr, low_arr, close_arr)[-1]
        hammer = ta.CDLHAMMER(open_arr, high_arr, low_arr, close_arr)[-1]

        # --- Cálculo de Pivot Points (diário) ---
        # Aqui calculamos os pivot points diretamente
        # Para simplificar, vamos assumir que os dados são de 1 hora e calcular os pivots diários
        # com base nos dados das últimas 24 horas (24 velas de 1 hora)
        if len(self.dataopen) >= 24:
            daily_high = max(self.datahigh.get(size=24))
            daily_low = min(self.datalow.get(size=24))
            daily_close = self.dataclose[0]
            
            self.pivot_val = (daily_high + daily_low + daily_close) / 3
            self.r1_val = 2 * self.pivot_val - daily_low
            self.s1_val = 2 * self.pivot_val - daily_high
            self.r2_val = self.pivot_val + (daily_high - daily_low)
            self.s2_val = self.pivot_val - (daily_high - daily_low)
            self.r3_val = daily_high + 2 * (self.pivot_val - daily_low)
            self.s3_val = daily_low - 2 * (daily_high - self.pivot_val)
        else:
            # Se não tivermos dados suficientes, definimos os pivots como 0
            self.pivot_val = 0
            self.r1_val = 0
            self.s1_val = 0
            self.r2_val = 0
            self.s2_val = 0
            self.r3_val = 0
            self.s3_val = 0

        signal = 0
        atr_val = self.atr14[0]

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
           ((abs(self.datalow[0] - self.s1_val) < atr_val * 0.7) or 
            (abs(self.datalow[0] - self.s2_val) < atr_val * 0.7))):
            signal = 1

        # --- Condições de Venda ---
        elif (self.ema50[0] < self.ema200[0] and
              engulfing < 0 and
              ((abs(self.datahigh[0] - self.r1_val) < atr_val * 0.7) or 
               (abs(self.datahigh[0] - self.r2_val) < atr_val * 0.7))):
            signal = -1

        # --- Se um sinal técnico foi gerado, consultar a IA ---
        if signal != 0:
            current_candle_data = {
                'open': self.dataopen[0],
                'high': self.datahigh[0],
                'low': self.datalow[0],
                'close': self.dataclose[0],
                'real_volume': 0,  # Adicionando real_volume com valor 0
                's1': self.s1_val, 's2': self.s2_val, 's3': self.s3_val,
                'r1': self.r1_val, 'r2': self.r2_val, 'r3': self.r3_val,
                'pivot': self.pivot_val,
                'ema50': self.ema50[0],
                'ema200': self.ema200[0],
                'atr14': self.atr14[0],
                'engulfing': engulfing,
                'hammer': hammer,
                'hour': current_hour,
                'day_of_week': current_day_of_week,
                'signal': signal,  # Adicionando signal
            }
            features_df = pd.DataFrame([current_candle_data])[self.features_order]
            
            prediction = self.model.predict(features_df)[0]

            # Se a IA prever sucesso (1), envia a ordem
            if prediction == 1:
                # Fechar posições opostas, se houver
                if self.position.size > 0 and signal == -1:  # Temos uma posição comprada e o sinal é de venda
                    print(f'{self.datas[0].datetime.date(0)}: Fechando posição comprada')
                    self.close()  # Fechar a posição comprada
                elif self.position.size < 0 and signal == 1:  # Temos uma posição vendida e o sinal é de compra
                    print(f'{self.datas[0].datetime.date(0)}: Fechando posição vendida')
                    self.close()  # Fechar a posição vendida
                
                # Abrir nova posição, se não houver posição ou se a posição for na mesma direção
                if (self.position.size == 0) or (self.position.size > 0 and signal == 1) or (self.position.size < 0 and signal == -1):
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
        
        # Garantir que o volume seja tratado como uma série numérica
        def _load(self):
            ret = super()._load()
            if ret:
                # Certifique-se de que o volume é numérico
                self.lines.volume[0] = float(self.lines.volume[0])
            return ret

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
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')  # System Quality Number

    print("--- Iniciando Backtest da Estratégia ---")
    # Executar o backtest
    results = cerebro.run()
    strat = results[0]

    # Imprimir os resultados
    print("\n--- Resultados do Backtest ---")
    initial_cash = 10000.0
    final_value = cerebro.broker.getvalue()
    print(f"Valor Inicial do Portfólio: {initial_cash:.2f}")
    print(f"Valor Final do Portfólio: {final_value:.2f}")
    total_return = (final_value - initial_cash) / initial_cash
    print(f"Retorno Total: {total_return * 100:.2f}%")
    
    # Resultados dos analisadores
    sharpe = strat.analyzers.sharpe_ratio.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    sqn_analysis = strat.analyzers.sqn.get_analysis()

    print(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A')}")
    print(f"Drawdown Máximo: {drawdown.max.drawdown:.2f}%")
    print(f"Drawdown Máximo em Valor: {drawdown.max.moneydown:.2f}")
    
    # Calcular Calmar Ratio
    annual_return = returns_analysis.get('rnorm', 0)
    max_drawdown = abs(drawdown.max.drawdown / 100)  # Converter para decimal
    calmar_ratio = annual_return / max_drawdown if max_drawdown != 0 else 0
    print(f"Calmar Ratio: {calmar_ratio:.2f}")
    
    # SQN (System Quality Number)
    print(f"SQN: {sqn_analysis.get('sqn', 'N/A')}")
    
    # Métricas personalizadas
    total_trades = strat.won_trades + strat.lost_trades
    print(f"Total de Trades: {total_trades}")
    print(f"Trades Vencedores: {strat.won_trades}")
    print(f"Trades Perdedores: {strat.lost_trades}")
    
    if total_trades > 0:
        # Percentual de Acerto
        win_rate = (strat.won_trades / total_trades) * 100
        print(f"Percentual de Acerto: {win_rate:.2f}%")
        
        # Média de Lucro por Trade Vencedor
        avg_won = sum(strat.won_pnl_list) / len(strat.won_pnl_list) if strat.won_pnl_list else 0
        print(f"Média de Lucro por Trade: {avg_won:.2f}")
        
        # Média de Perda por Trade Perdedor
        avg_lost = sum(strat.lost_pnl_list) / len(strat.lost_pnl_list) if strat.lost_pnl_list else 0
        print(f"Média de Perda por Trade: {avg_lost:.2f}")
        
        # Payoff Ratio
        payoff_ratio = avg_won / avg_lost if avg_lost != 0 else 0
        print(f"Payoff Ratio: {payoff_ratio:.2f}")
        
        # Fator de Lucro
        profit_factor = strat.gross_profit / strat.gross_loss if strat.gross_loss != 0 else 0
        print(f"Fator de Lucro: {profit_factor:.2f}")
        
        # Lucro Médio por Trade (incluindo perdas)
        average_trade_pnl = strat.total_pnl / total_trades if total_trades > 0 else 0
        print(f"Lucro Médio por Trade: {average_trade_pnl:.2f}")
        
        # Expectativa Matemática
        expectancy = (win_rate / 100) * payoff_ratio - (1 - win_rate / 100) if win_rate != 0 else 0
        print(f"Expectativa Matemática: {expectancy:.2f}")
        
        # Perda Média por Trade (já calculada como avg_lost)
        print(f"Perda Média por Trade: {avg_lost:.2f}")
    else:
        print("Nenhum trade foi fechado.")

    # Plotar o gráfico
    # print("\nGerando gráfico do backtest...")
    # cerebro.plot(style='candlestick')