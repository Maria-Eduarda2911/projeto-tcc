from fastapi import FastAPI
from pydantic import BaseModel
import requests
from typing import Dict, Any
from math import isfinite

app = FastAPI(title="Previsão de Alagamentos - Recife (APAC)")

# Endpoints da APAC
CEMADEN_URL = "http://dados.apac.pe.gov.br:41120/cemaden/"
METEOROLOGIA_URL = "http://dados.apac.pe.gov.br:41120/meteorologia24h/"

# Estado em memória para saturação
STATION_STATE: Dict[str, float] = {}

# -----------------------------
# MODELO DE SIMULAÇÃO
# -----------------------------
class SimulacaoInput(BaseModel):
    nome: str = "Estação Simulada"
    latitude: float
    longitude: float
    chuva_mm: float
    prob_chuva: float = 50.0
    acumulado_24h: float = 0.0

def safe_float(val: Any, default: float = 0.0) -> float:
    try:
        f = float(val)
        return f if isfinite(f) else default
    except:
        return default

def update_saturation(station_id: str, chuva_mm: float) -> float:
    prev = STATION_STATE.get(station_id, 0.2)
    input_norm = max(min(chuva_mm / 50.0, 1.0), 0.0)
    sat = 0.85 * prev + 0.15 * input_norm
    sat = max(min(sat, 1.0), 0.0)
    STATION_STATE[station_id] = sat
    return sat

def risk_from_features(chuva_mm: float, sat: float, prob: float, acumulado: float) -> Dict[str, Any]:
    intensity = max(min(chuva_mm / 40.0, 1.0), 0.0)
    f_prob = max(min(prob / 100.0, 1.0), 0.0)
    f_24 = max(min(acumulado / 60.0, 1.0), 0.0)
    score = 0.6 * intensity + 0.3 * sat + 0.1 * (0.5*f_prob + 0.5*f_24)
    if score >= 0.7:
        nivel, cor = "ALTO", "vermelho"
    elif score >= 0.4:
        nivel, cor = "MODERADO", "laranja"
    else:
        nivel, cor = "BAIXO", "verde"
    return {"score": round(score, 3), "nivel": nivel, "cor": cor}

# -----------------------------
# ENDPOINTS
# -----------------------------
@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}

@app.get("/mapa", tags=["Dados Reais"])
def mapa():
    try:
        cemaden = requests.get(CEMADEN_URL, timeout=10).json()
        previsao = requests.get(METEOROLOGIA_URL, timeout=10).json()
        pontos = []
        for est in cemaden:
            lat = safe_float(est.get("latitude"))
            lon = safe_float(est.get("longitude"))
            if lat == 0 or lon == 0:
                continue
            nome = str(est.get("nome", "Estação"))
            chuva = safe_float(est.get("chuva_mm", 0))
            sat = update_saturation(nome, chuva)
            risco = risk_from_features(chuva, sat, 50, 0)
            pontos.append({
                "nome": nome,
                "latitude": lat,
                "longitude": lon,
                "chuva_mm": chuva,
                "risco": risco["nivel"],
                "cor": risco["cor"],
                "score": risco["score"]
            })
        return {"pontos": pontos, "previsao_24h": previsao}
    except Exception as e:
        return {"erro": str(e)}

@app.get("/regioes", tags=["Dados Reais"])
def regioes():
    return {"mensagem": "Agregação por regiões ainda não implementada neste exemplo"}

@app.post("/simular", tags=["Simulação"])
def simular(dados: SimulacaoInput):
    sat = update_saturation(dados.nome, dados.chuva_mm)
    risco = risk_from_features(dados.chuva_mm, sat, dados.prob_chuva, dados.acumulado_24h)
    return {
        "nome": dados.nome,
        "latitude": dados.latitude,
        "longitude": dados.longitude,
        "chuva_mm": dados.chuva_mm,
        "prob_chuva": dados.prob_chuva,
        "acumulado_24h": dados.acumulado_24h,
        "risco": risco["nivel"],
        "cor": risco["cor"],
        "score": risco["score"]
    }
