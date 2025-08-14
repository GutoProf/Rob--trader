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

## Estrutura dos Arquivos

*   `robo_trader.py`: **(Operação e Coleta de Dados)** O robô principal. Roda em loop, analisa o mercado, consulta a IA, envia ordens e, crucialmente, **salva o resultado de cada operação** para o retreinamento futuro.
*   `treinamento_ia.py`: **(Retreinamento)** Script principal para treinar a IA. Ele combina os dados simulados com os dados de trades reais coletados pelo robô para criar um modelo cada vez mais preciso.
*   `historico_trades_executados.csv`: Banco de dados com o histórico de todas as operações realizadas pelo robô.
*   `retreinar_ia.bat`: Script de lote para automatizar a execução do retreinamento no Windows.
*   Outros: `coleta_dados.py`, `calcula_indicadores.py`, `gerador_de_sinais.py` (usados para a criação do dataset inicial).

---

## Como Utilizar

### 1. Instalação
Clone o projeto e instale as dependências:
```bash
pip install -r requirements.txt
```

### 2. Treinamento Inicial
Antes de rodar o robô pela primeira vez, crie o modelo de IA inicial:
```bash
python coleta_dados.py
python calcula_indicadores.py
python gerador_de_sinais.py
python treinamento_ia.py
```

### 3. Execução do Robô
Com o modelo treinado e o terminal MT5 aberto, execute o robô:
```bash
python robo_trader.py
```
O robô começará a operar e a salvar os resultados de seus trades no arquivo `historico_trades_executados.csv`.

---

## Aprendizado Contínuo e Retreinamento

O grande diferencial deste robô é sua capacidade de aprender.

1.  **Coleta Automática:** Enquanto o `robo_trader.py` está em execução, cada trade fechado é automaticamente salvo no arquivo `historico_trades_executados.csv`.

2.  **Retreinando a IA Manualmente:** A qualquer momento, você pode melhorar a inteligência do robô executando:
    ```bash
    python treinamento_ia.py
    ```
    Isso irá gerar um novo arquivo `modelo_ia_trade.joblib`, mais experiente e adaptado às condições recentes do mercado.

### Automação do Retreinamento (Opcional, Windows)

Para que o modelo aprenda sozinho periodicamente, você pode agendar a execução.

1.  **Abra o Agendador de Tarefas** do Windows.
2.  No menu à direita, clique em **"Criar Tarefa Básica..."**.
3.  **Nomeie a tarefa** (ex: "Retreinamento do Robô Trader") e avance.
4.  **Escolha o gatilho** (ex: "Semanalmente") e configure o dia e a hora (ex: todo Domingo às 18:00).
5.  **Escolha a ação "Iniciar um programa"**.
6.  **Aponte para o script:** Clique em "Procurar..." e selecione o arquivo `retreinar_ia.bat` na pasta do projeto.
7.  **Conclua** a criação da tarefa.

Agora, o retreinamento será executado automaticamente na frequência que você definiu.
