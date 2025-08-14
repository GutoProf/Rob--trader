import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib # Biblioteca para salvar o modelo treinado

# --- Arquivos ---
INPUT_FILE = "dataset_final_para_ia.csv"
MODEL_FILE = "modelo_ia_trade.joblib"

def train_model():
    """
    Carrega o dataset, treina um modelo de RandomForest, avalia sua performance
    e salva o modelo treinado em um arquivo.
    """
    print(f"Lendo dataset de {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")
        print("Por favor, execute o script 'gerador_de_sinais.py' primeiro.")
        return

    if df.empty:
        print("O dataset está vazio. Não há dados para treinar.")
        return

    print(f"Dataset carregado com {len(df)} amostras.")

    # --- 1. Preparação dos Dados ---
    # 'target' é o que queremos prever (0 = Loss, 1 = Win)
    # Features são todas as outras colunas que o modelo usará para aprender.
    X = df.drop('target', axis=1)
    y = df['target']

    # --- 2. Divisão em Treino e Teste ---
    # Usamos 80% dos dados para treinar e 20% para testar.
    # stratify=y garante que a proporção de vitórias/derrotas seja a mesma nos dois conjuntos.
    # random_state=42 garante que a divisão seja sempre a mesma, para resultados reprodutíveis.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Dados divididos em {len(X_train)} para treino e {len(X_test)} para teste.")

    # --- 3. Treinamento do Modelo ---
    print("\nTreinando o modelo RandomForestClassifier...")
    # n_estimators: número de "árvores" na floresta.
    # class_weight='balanced': ajusta o modelo para datasets onde uma classe (win/loss) é mais rara.
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    model.fit(X_train, y_train)
    print("Treinamento concluído.")

    # --- 4. Avaliação do Modelo ---
    print("\nAvaliando a performance do modelo no conjunto de teste...")
    y_pred = model.predict(X_test)

    # Acurácia: Percentual de previsões corretas.
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Acurácia: {accuracy:.2%}")

    # Matriz de Confusão: Mostra os erros e acertos em detalhe.
    # [[Verdadeiro Negativo, Falso Positivo],
    #  [Falso Negativo,    Verdadeiro Positivo]]
    print("\nMatriz de Confusão:")
    print(confusion_matrix(y_test, y_pred))

    # Relatório de Classificação: Métricas detalhadas por classe (Win/Loss).
    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred, target_names=['Loss (0)', 'Win (1)']))

    # --- 5. Salvando o Modelo Treinado ---
    try:
        joblib.dump(model, MODEL_FILE)
        print(f"\nModelo salvo com sucesso em: {MODEL_FILE}")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o modelo: {e}")

if __name__ == "__main__":
    train_model()
