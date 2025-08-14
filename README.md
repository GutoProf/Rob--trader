# Robô Trader com IA para XAUUSD (Ouro)

Este projeto é um robô de trading algorítmico completo para operar o par XAUUSD (Ouro) no timeframe de 1 hora (H1). Ele utiliza uma estratégia de confluência de indicadores técnicos clássicos e a filtra com um modelo de Inteligência Artificial (Machine Learning) para decidir se deve ou não entrar em uma operação.

**AVISO:** Este é um projeto de fins educacionais. O trading financeiro envolve riscos significativos. Utilize este robô **exclusivamente em contas de demonstração (DEMO)**. O autor não se responsabiliza por quaisquer perdas financeiras.

---

## Estratégia de Trading

A lógica do robô é baseada em uma **confluência de três fatores**, com a decisão final sendo tomada por um modelo de IA.

1.  **Tendência (EMA):** A direção principal da tendência é definida pela posição das Médias Móveis Exponenciais (EMA) de 50 e 200 períodos.
    *   **Tendência de Alta:** `EMA 50 > EMA 200`
    *   **Tendência de Baixa:** `EMA 50 < EMA 200`

2.  **Zonas de Interesse (Pivot Points):** Os pontos de entrada são procurados perto de níveis de suporte e resistência, calculados usando os Pivot Points clássicos. A proximidade é medida dinamicamente usando o indicador de volatilidade ATR (Average True Range).
    *   **Sinais de Compra:** O preço deve estar próximo a um nível de Suporte (S1, S2, S3).
    *   **Sinais de Venda:** O preço deve estar próximo a um nível de Resistência (R1, R2, R3).

3.  **Gatilho de Confirmação (Padrões de Vela):** A entrada no trade é confirmada por padrões de vela de reversão.
    *   **Sinais de Compra:** Martelo (Hammer), Engolfo de Alta (Bullish Engulfing).
    *   **Sinais de Venda:** Engolfo de Baixa (Bearish Engulfing).

4.  **Filtro de Inteligência Artificial (Random Forest):**
    *   Quando os três critérios acima geram um sinal, os dados do mercado naquele momento são enviados para um modelo de `RandomForestClassifier` treinado.
    *   O modelo prevê se o trade tem uma alta ou baixa probabilidade de atingir o take profit antes do stop loss.
    *   **O robô só executa a ordem se o modelo de IA prever "Sucesso".**

---

## Tecnologias Utilizadas

*   **Linguagem:** Python 3
*   **Plataforma de Execução:** MetaTrader 5 (MT5)
*   **Bibliotecas Principais:**
    *   `metatrader5`: Para integração e envio de ordens ao MT5.
    *   `pandas` / `numpy`: Para manipulação e análise de dados.
    *   `scikit-learn`: Para treinar e avaliar o modelo de Machine Learning.
    *   `TA-Lib`: Para o cálculo de indicadores técnicos.
    *   `joblib`: Para salvar e carregar o modelo de IA treinado.

---

## Estrutura dos Arquivos

O projeto é dividido em módulos, cada um com uma responsabilidade específica:

1.  `requirements.txt`: Lista todas as dependências Python do projeto.
2.  `coleta_dados.py`: Script para conectar ao MT5 e baixar o histórico de preços do XAUUSD.
3.  `calcula_indicadores.py`: Lê os dados brutos e calcula todos os indicadores técnicos necessários (Pivots, EMAs, ATR, etc.).
4.  `gerador_de_sinais.py`: Aplica a lógica da estratégia, gera os sinais de compra/venda e simula o resultado de cada trade para criar o dataset de treinamento para a IA.
5.  `treinamento_ia.py`: Treina o modelo de RandomForest com o dataset gerado e salva o modelo final no arquivo `modelo_ia_trade.joblib`.
6.  `robo_trader.py`: O robô principal. Roda em loop, analisa o mercado em tempo real, consulta a IA e envia as ordens de operação.

---

## Como Utilizar

Siga os passos abaixo para configurar e executar o robô.

### 1. Pré-requisitos
*   Python 3.x instalado.
*   Conta na plataforma MetaTrader 5 (**use uma conta DEMO**).
*   Terminal MT5 instalado e logado.

### 2. Instalação

Clone ou baixe os arquivos do projeto para um diretório em seu computador.

Abra um terminal nesse diretório e instale as dependências:
```bash
pip install -r requirements.txt
```
> **Nota:** A instalação da biblioteca `ta-lib` no Windows pode ser complexa. Se encontrar erros, procure por um arquivo `.whl` pré-compilado compatível com sua versão do Python e Windows.

### 3. Treinamento do Modelo (Primeira Execução)

Antes de rodar o robô, você precisa gerar o dataset e treinar o modelo de IA. Execute os scripts na seguinte ordem:

```bash
# Passo 1: Baixar os dados históricos (requer MT5 aberto)
python coleta_dados.py

# Passo 2: Calcular os indicadores
python calcula_indicadores.py

# Passo 3: Gerar o dataset com os sinais da estratégia
python gerador_de_sinais.py

# Passo 4: Treinar o modelo de IA
python treinamento_ia.py
```

Ao final deste processo, você terá o arquivo `modelo_ia_trade.joblib` no seu diretório.

### 4. Execução do Robô

Com o modelo treinado e o terminal MT5 aberto (logado em uma conta **DEMO**), execute o robô:

```bash
python robo_trader.py
```

O terminal começará a exibir os logs do robô, mostrando seu status e decisões.
