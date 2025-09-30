# main.py (versão corrigida)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from data.areas_risco import gerar_json_previsao
import os
import asyncio
from datetime import datetime
import logging
import uvicorn
import sys

# Adiciona diretórios ao path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "models"))

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa FastAPI
app = FastAPI(title="Mapa de Probabilidade de Alagamento - Recife")

# Caminho para arquivos estáticos
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
    logger.warning(f"⚠️ Diretório {STATIC_DIR} criado. Adicione o index.html lá.")

# Monta static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Cache global
ULTIMA_PREVISAO = None

async def atualizar_cache():
    """Atualiza o cache periodicamente"""
    global ULTIMA_PREVISAO
    while True:
        try:
            ULTIMA_PREVISAO = gerar_json_previsao()  # função síncrona
            logger.info(f"🔄 Cache atualizado - {len(ULTIMA_PREVISAO['bairros'])} bairros")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar cache: {e}")
        await asyncio.sleep(300)  # 5 minutos

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Inicializando Mapa de Risco Recife...")
    asyncio.create_task(atualizar_cache())

@app.get("/")
async def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "index.html não encontrado. Coloque o arquivo em 'static/'."}

@app.get("/api/previsao")
async def get_previsao():
    global ULTIMA_PREVISAO
    if ULTIMA_PREVISAO is None:
        data = gerar_json_previsao()
    else:
        data = ULTIMA_PREVISAO
    logger.info(f"📦 Retornando {len(data['bairros'])} bairros")
    return data

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_ativo": ULTIMA_PREVISAO is not None
    }

@app.get("/api/atualizar")
async def forcar_atualizacao():
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
    PORT = int(os.environ.get("PORT", 8000))  # permite mudar a porta via variável de ambiente
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=True)
