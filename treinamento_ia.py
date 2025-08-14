import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os

# --- Arquivos ---
DATASET_SIMULADO = "dataset_final_para_ia.csv"
DATASET_REAL = "historico_trades_executados.csv"
MODEL_FILE = "modelo_ia_trade.joblib"

def train_model():
    """
    Carrega o dataset simulado e o histórico de trades reais, combina-os,
    treina um novo modelo de IA e o salva, substituindo a versão antiga.
    """
    print("--- INICIANDO PROCESSO DE RETREINAMENTO DA IA ---")

    # --- 1. Carregar Datasets ---
    try:
        df_simulado = pd.read_csv(DATASET_SIMULADO)
        print(f"Dataset simulado '{DATASET_SIMULADO}' carregado com {len(df_simulado)} amostras.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de simulação '{DATASET_SIMULADO}' não encontrado. Execute os scripts de geração de dados primeiro.")
        return

    df_real = None
    if os.path.exists(DATASET_REAL):
        try:
            df_real = pd.read_csv(DATASET_REAL)
            if not df_real.empty:
                print(f"Histórico de trades reais '{DATASET_REAL}' carregado com {len(df_real)} amostras.")
            else:
                df_real = None # Trata como se não existisse se estiver vazio
        except pd.errors.EmptyDataError:
            print(f"Aviso: O arquivo de histórico '{DATASET_REAL}' está vazio.")
            df_real = None
    else:
        print("Nenhum histórico de trades reais encontrado. Usando apenas dados simulados.")

    # --- 2. Combinar Datasets ---
    if df_real is not None:
        # Garante que ambos os dataframes tenham as mesmas colunas, na mesma ordem
        # Usa as colunas do df_simulado como referência
        cols_simulado = df_simulado.columns
        cols_real = df_real.columns
        
        # Alinha as colunas do df_real com as do df_simulado
        df_real_aligned = df_real.reindex(columns=cols_simulado, fill_value=0)
        
        # Remove colunas do df_real que não existem no df_simulado
        df_real_aligned = df_real_aligned[cols_simulado]

        df_combinado = pd.concat([df_simulado, df_real_aligned], ignore_index=True)
        print(f"Datasets combinados. Tamanho total do novo dataset: {len(df_combinado)} amostras.")
    else:
        df_combinado = df_simulado

    # --- 3. Preparação dos Dados ---
    # Remove colunas que não devem ser usadas como features
    features_to_drop = ['time', 'time_dt', 'target']
    X = df_combinado.drop(columns=features_to_drop, errors='ignore')
    y = df_combinado['target']

    # Guarda a ordem das colunas para o robô usar
    model_features = X.columns.tolist()

    # --- 4. Divisão em Treino e Teste ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Dados divididos em {len(X_train)} para treino e {len(X_test)} para teste.")

    # --- 5. Treinamento do Modelo ---
    print("\nTreinando o novo modelo RandomForestClassifier...")
    model = RandomForestClassifier(n_estimators=150, random_state=42, class_weight='balanced', n_jobs=-1, max_depth=10)
    model.fit(X_train, y_train)
    # Adiciona os nomes das features ao modelo, para referência no robô
    model.feature_names_in_ = model_features
    print("Treinamento concluído.")

    # --- 6. Avaliação do Modelo ---
    print("\nAvaliando a performance do novo modelo...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Acurácia: {accuracy:.2%}")
    print("\nMatriz de Confusão:")
    print(confusion_matrix(y_test, y_pred))
    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred, target_names=['Loss/BreakEven (0)', 'Win (1)']))

    # --- 7. Salvando o Modelo Treinado ---
    try:
        joblib.dump(model, MODEL_FILE)
        print(f"\nModelo atualizado e salvo com sucesso em: {MODEL_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o modelo: {e}")

if __name__ == "__main__":
    train_model()