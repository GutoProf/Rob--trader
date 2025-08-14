## Robô Trader com IA para XAUUSD

Este diretório contém um projeto de robô de trading algorítmico para operar o par XAUUSD (Ouro) no timeframe de 1 hora (H1). Ele utiliza uma estratégia de confluência de indicadores técnicos e um modelo de Inteligência Artificial para tomar decisões de trading.

### Visão Geral do Projeto

*   **Propósito:** Automatizar a execução de trades no par XAUUSD com base em uma estratégia predefinida e um filtro de IA.
*   **Tecnologias Principais:** Python, MetaTrader 5, pandas, scikit-learn, TA-Lib.
*   **Arquitetura:** O projeto é modular, com scripts separados para coleta de dados, cálculo de indicadores, geração de sinais, treinamento do modelo de IA e a execução do robô.

### Construindo e Executando

1.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *Observação: A instalação da biblioteca `ta-lib` pode exigir passos adicionais dependendo do seu sistema operacional.*

2.  **Treine o modelo de IA (primeira execução):**
    Execute os scripts na seguinte ordem para treinar o modelo:
    ```bash
    python coleta_dados.py
    python calcula_indicadores.py
    python gerador_de_sinais.py
    python treinamento_ia.py
    ```

3.  **Execute o robô:**
    Com o MetaTrader 5 aberto e logado em uma conta DEMO, execute o robô:
    ```bash
    python robo_trader.py
    ```

### Convenções de Desenvolvimento

*   O código é escrito em Python e segue as convenções da PEP 8.
*   O projeto é dividido em módulos com responsabilidades bem definidas.
*   O modelo de IA treinado é salvo no arquivo `modelo_ia_trade.joblib`.
*   Os dados históricos e com indicadores são salvos em arquivos CSV.