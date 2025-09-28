from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import os
import sys

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(__file__))

app = FastAPI(title="Sistema de Previsão de Alagamentos - Recife")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obter caminho absoluto para a pasta static
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Importações
try:
    from services.apac_client import APACClient
    from services.data_processor import DataProcessor
    from models.predictor import FloodPredictor
    from data.areas_risco import AREAS_RISCO_RECIFE, BAIRROS_CRITICOS, get_areas_com_risco_fallback
except ImportError as e:
    print(f"Erro de importação: {e}")
    APACClient = None
    DataProcessor = None
    FloodPredictor = None

APAC_URL = "http://dados.apac.pe.gov.br:41120/meteorologia24h/"

@app.get("/")
async def read_root():
    index_path = os.path.join(static_path, 'index.html')
    return FileResponse(index_path)

@app.get("/health")
async def health_check():
    return {"status": "online", "service": "Alagamentos Recife"}

@app.get("/api/areas-risco")
async def get_areas_risco():
    return {
        "areas": AREAS_RISCO_RECIFE,
        "bairros_criticos": BAIRROS_CRITICOS,
        "total_areas": len(AREAS_RISCO_RECIFE)
    }

@app.get("/api/previsao")
async def get_previsao_alagamentos():
    try:
        client = APACClient(APAC_URL)
        dados_apac = await client.get_dados_meteorologia()
        
        processor = DataProcessor()
        predictor = FloodPredictor()
        
        areas_com_previsao = []
        
        for area in AREAS_RISCO_RECIFE:
            risco_calculado = predictor.calcular_risco_area(area, dados_apac)
            
            area_com_previsao = {
                **area,
                "risco_atual": risco_calculado["score"],
                "nivel_risco": risco_calculado["nivel"],
                "cor_risco": risco_calculado["cor"],
                "probabilidade_alagamento": risco_calculado["probabilidade"]
            }
            areas_com_previsao.append(area_com_previsao)
        
        return {
            "previsao_gerada_em": processor.get_timestamp(),
            "areas": areas_com_previsao,
            "alerta_geral": predictor.determinar_alerta_geral(areas_com_previsao)
        }
        
    except Exception as e:
        print(f"Erro ao obter previsão: {e}")
        return get_areas_com_risco_fallback()

@app.get("/api/detalhes-area/{area_id}")
async def get_detalhes_area(area_id: int):
    if area_id < 0 or area_id >= len(AREAS_RISCO_RECIFE):
        raise HTTPException(status_code=404, detail="Área não encontrada")
    
    area = AREAS_RISCO_RECIFE[area_id]
    return {
        "area": area,
        "recomendacoes": [
            "⚠️ ALTO RISCO - Evitar deslocamento" if area.get("risco_base", 0.5) >= 0.7 else
            "🔶 ATENÇÃO - Ficar alerta" if area.get("risco_base", 0.5) >= 0.4 else
            "✅ Situação normal"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)