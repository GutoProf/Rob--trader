# Robô Trader com IA para XAUUSD (Ouro) - com Aprendizado Contínuo

Este projeto é um robô de trading algorítmico completo para operar o par XAUUSD (Ouro) no timeframe de 1 hora (H1). Ele utiliza uma estratégia de confluência de indicadores técnicos clássicos e a filtra com um modelo de Inteligência Artificial (Machine Learning) que **aprende e evolui com as próprias operações**.

**AVISO:** Este é um projeto de fins educacionais. O trading financeiro envolve riscos significativos. Utilize este robô **exclusivamente em contas de demonstração (DEMO)**. O autor não se responsabiliza por quaisquer perdas financeiras.

---

## Estratégia de Trading

A lógica do robô é baseada em uma **confluência de três fatores**, com a decisão final sendo tomada por um modelo de IA.

1.  **Tendência (EMA):** A direção principal da tendência é definida pela posição das Médias Móveis Exponenciais (EMA) de 50 e 200 períodos.
2.  **Zonas de Interesse (Pivot Points):** Os pontos de entrada são procurados perto de níveis de suporte e resistência, calculados usando os Pivot Points clássicos.
3.  **Gatilho de Confirmação (Padrões de Vela):** A entrada no trade é confirmada por padrões de vela de reversão (Engolfo, Martelo).
4.  **Filtro de Inteligência Artificial (Random Forest):**
    *   Quando os três critérios acima geram um sinal, os dados do mercado são enviados para o modelo de IA.
    *   O modelo prevê se o trade tem uma alta ou baixa probabilidade de sucesso.
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
2.  `coleta_dados.py`: Script para baixar o histórico de preços do XAUUSD.
3.  `calcula_indicadores.py`: Calcula todos os indicadores técnicos necessários.
4.  `gerador_de_sinais.py`: Gera o dataset de treinamento inicial a partir de dados históricos.
5.  `treinamento_ia.py`: **(Retreinamento)** Script principal para treinar a IA. Ele combina os dados simulados com os dados de trades reais coletados pelo robô para criar um modelo cada vez mais preciso.
6.  `robo_trader.py`: **(Operação e Coleta de Dados)** O robô principal. Roda em loop, analisa o mercado, consulta a IA, envia ordens e, crucialmente, **salva o resultado de cada operação** para o retreinamento futuro.
7.  `historico_trades_executados.csv`: **(Novo)** Banco de dados com o histórico de todas as operações realizadas pelo robô, usado para o aprendizado contínuo.

---

## Como Utilizar

Siga os passos abaixo para configurar e executar o robô.

### 1. Pré-requisitos
*   Python 3.x instalado.
*   Conta na plataforma MetaTrader 5 (**use uma conta DEMO**).
*   Terminal MT5 instalado e logado.

### 2. Instalação

Clone o projeto e instale as dependências:
```bash
pip install -r requirements.txt
```

### 3. Treinamento Inicial

Antes de rodar o robô pela primeira vez, você precisa criar o modelo de IA inicial. Execute os scripts na seguinte ordem:

```bash
python coleta_dados.py
python calcula_indicadores.py
python gerador_de_sinais.py
python treinamento_ia.py
```

### 4. Execução do Robô

Com o modelo treinado e o terminal MT5 aberto, execute o robô:

```bash
python robo_trader.py
```
O robô começará a operar e a salvar os resultados de seus trades no arquivo `historico_trades_executados.csv`.

---

## Aprendizado Contínuo e Retreinamento

O grande diferencial deste robô é sua capacidade de aprender.

1.  **Coleta Automática:** Enquanto o `robo_trader.py` está em execução, cada trade fechado (seja com ganho ou perda) é automaticamente salvo com todos os seus parâmetros no arquivo `historico_trades_executados.csv`.

2.  **Retreinando a IA:** Após o robô ter executado várias operações, você pode melhorar a inteligência dele. Para isso, basta rodar novamente o script de treinamento:
    ```bash
    python treinamento_ia.py
    ```
    Este comando irá pegar todos os trades reais do histórico, combiná-los com os dados de simulação e gerar um novo arquivo `modelo_ia_trade.joblib`, mais experiente e adaptado às condições recentes do mercado.

3.  **Ciclo de Melhoria:** Repita o passo 2 periodicamente (ex: uma vez por semana) para manter seu modelo de IA sempre atualizado e aprendendo.