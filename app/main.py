# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from data.areas_risco import gerar_json_previsao
import os
import asyncio
from datetime import datetime
import logging
import uvicorn

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mapa de Risco - Recife")

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cache
ULTIMA_PREVISAO = None

async def atualizar_cache():
    """Atualiza o cache periodicamente"""
    global ULTIMA_PREVISAO
    while True:
        try:
            ULTIMA_PREVISAO = gerar_json_previsao()
            logger.info(f"🔄 Cache atualizado - {len(ULTIMA_PREVISAO['bairros'])} bairros")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar cache: {e}")
        await asyncio.sleep(300)  # 5 minutos

@app.on_event("startup")
async def startup_event():
    """Inicializa na startup"""
    logger.info("🚀 Inicializando Mapa de Risco Recife...")
    asyncio.create_task(atualizar_cache())

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/previsao")
async def get_previsao():
    """Retorna dados para o mapa"""
    if ULTIMA_PREVISAO is None:
        # Se não há cache, gera dados na hora
        data = gerar_json_previsao()
    else:
        data = ULTIMA_PREVISAO
    
    logger.info(f"📦 Retornando {len(data['bairros'])} bairros")
    return data

@app.get("/health")
async def health_check():
    """Endpoint de saúde da aplicação"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_ativo": ULTIMA_PREVISAO is not None
    }

@app.get("/api/atualizar")
async def forcar_atualizacao():
    """Força atualização imediata do cache"""
    global ULTIMA_PREVISAO
    try:
        ULTIMA_PREVISAO = gerar_json_previsao()
        logger.info(f"🔄 Atualização forçada - {len(ULTIMA_PREVISAO['bairros'])} bairros")
        return {
            "status": "success",
            "message": f"Cache atualizado com {len(ULTIMA_PREVISAO['bairros'])} bairros",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erro na atualização forçada: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)