## Robô Trader com IA para XAUUSD (com Aprendizado Contínuo)

Este diretório contém um projeto de robô de trading algorítmico para operar o par XAUUSD (Ouro) no timeframe de 1 hora (H1). Ele utiliza uma estratégia de confluência de indicadores técnicos e um modelo de Inteligência Artificial para tomar decisões de trading.

O projeto foi atualizado para incluir um **ciclo de aprendizado contínuo**, permitindo que o robô aprenda com suas próprias operações e melhore sua assertividade ao longo do tempo.

### Visão Geral do Projeto

*   **Propósito:** Automatizar a execução de trades no par XAUUSD com base em uma estratégia predefinida e um filtro de IA que é periodicamente retreinado com dados de trades reais.
*   **Tecnologias Principais:** Python, MetaTrader 5, pandas, scikit-learn, TA-Lib, joblib, backtrader.
*   **Arquitetura:** O projeto é modular. A principal característica é o ciclo de feedback:
    1.  `robo_trader.py` executa trades.
    2.  Ele salva os dados e o resultado de cada trade no arquivo `historico_trades_executados.csv`.
    3.  `treinamento_ia.py` usa esses dados históricos para retreinar o modelo, tornando-o mais inteligente.

### Arquitetura de Aprendizado Contínuo

*   `robo_trader.py`: Além de operar, este script agora detecta quando um trade é fechado, calcula o resultado (lucro/perda) e salva todas as features daquele trade no arquivo de histórico.
*   `treinamento_ia.py`: Este script agora combina o dataset simulado original com o histórico de trades reais para treinar uma nova versão do modelo de IA.
*   `historico_trades_executados.csv`: Arquivo CSV que armazena o histórico de todos os trades executados pelo robô, servindo como o principal dataset para o retreinamento.
*   `trades_abertos.json`: Arquivo temporário para que o robô rastreie as posições que ele abriu e que ainda não foram fechadas.

### Backtest da Estratégia

*   `backtest_estrategia.py`: Script para realizar backtest da estratégia de trading utilizando a biblioteca `backtrader`. Ele carrega os dados históricos, aplica a estratégia e gera métricas de desempenho como Sharpe Ratio, Drawdown, Calmar Ratio, Sortino Ratio, entre outras.

### Fluxo de Trabalho

1.  **Instalação e Treinamento Inicial:**
    *   Instale as dependências: `pip install -r requirements.txt`
    *   Crie o modelo inicial (necessário apenas uma vez):
        ```bash
        python coleta_dados.py
        python calcula_indicadores.py
        python gerador_de_sinais.py
        python treinamento_ia.py
        ```

2.  **Execução do Robô:**
    *   Execute o robô para que ele comece a operar e coletar dados:
        ```bash
        python robo_trader.py
        ```

3.  **Backtest da Estratégia:**
    *   Execute o backtest para avaliar o desempenho da estratégia:
        ```bash
        python backtest_estrategia.py
        ```

4.  **Retreinamento Periódico (Manual ou Automático):**
    *   Após o robô ter executado alguns trades, rode o script de treinamento novamente para criar um modelo melhorado:
        ```bash
        python treinamento_ia.py
        ```
    *   O robô passará a usar o novo modelo automaticamente.

### Automação do Retreinamento (Windows)

*   Para automatizar o processo de retreinamento, foi criado o script `retreinar_ia.bat`.
*   Este script pode ser agendado para execução periódica (ex: semanal) através do **Agendador de Tarefas do Windows**.
*   A tarefa agendada deve ser configurada para iniciar o programa `retreinar_ia.bat`.

### Convenções de Desenvolvimento

*   O código é escrito em Python e segue as convenções da PEP 8.
*   O modelo de IA treinado é salvo no arquivo `modelo_ia_trade.joblib`.
*   O sistema é projetado para ser um ciclo fechado: operar -> coletar dados -> aprender -> operar melhor.