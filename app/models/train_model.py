import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

# Carregar dados históricos
df = pd.read_csv("dados_historicos.csv")

features = ["chuva_mm", "acumulado_24h", "prob_chuva", "saturacao"]

# Modelo de score de risco
X = df[features]
y_risco = df["risco_score"]
model_risco = RandomForestRegressor(n_estimators=100, random_state=42)
model_risco.fit(X, y_risco)
joblib.dump(model_risco, "modelo_risco.pkl")

# Modelo de inundação em mm
y_inundacao = df["possibilidade_inundacao_mm"]
model_inundacao = RandomForestRegressor(n_estimators=100, random_state=42)
model_inundacao.fit(X, y_inundacao)
joblib.dump(model_inundacao, "modelo_inundacao.pkl")

print("Treino finalizado, modelos salvos!")