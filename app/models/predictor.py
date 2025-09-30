# models/predictor.py
# ============================================================================ 
# FLOOD PREDICTOR - Previsão de risco de alagamentos Recife
# ============================================================================ 

import math
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from shapely.geometry import Point
except ImportError:
    Point = None

try:
    from models.apac_processor import APACDataProcessor
    HAS_APAC = True
except ImportError:
    HAS_APAC = False

logger = logging.getLogger("models.predictor")

# ============================================================================ 
# FUNÇÕES AUXILIARES
# ============================================================================ 

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distância entre duas coordenadas (Haversine) em km"""
    R = 6371  # raio da Terra em km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classificar_risco(precipitacao: float, umidade: Optional[float]) -> str:
    """Define o risco baseado em chuva acumulada e umidade relativa"""
    if precipitacao >= 50:
        return "ALTO"
    elif precipitacao >= 20:
        return "MODERADO"
    else:
        if umidade is not None and umidade < 30:
            return "MODERADO"
        return "BAIXO"

# ============================================================================ 
# PREDITOR PRINCIPAL
# ============================================================================ 

class FloodPredictor:
    """Classe principal de previsão de risco de alagamentos"""

    def __init__(self, bairros_criticos: Optional[Dict[str, Dict]] = None):
        self.bairros_criticos = bairros_criticos or {}
        if HAS_APAC:
            self.apac = APACDataProcessor()
        else:
            self.apac = None
            logger.warning("❌ APACDataProcessor não disponível, usando simulação")

    async def analisar_bairros(self) -> List[Dict[str, Any]]:
        """
        Analisa os bairros usando dados da APAC/CEMADEN
        Retorna lista com risco por bairro
        """
        if self.apac:
            try:
                dados_apac = await self.apac.get_dados_em_tempo_real()
                estacoes = dados_apac.get("estacoes_meteorologia", [])
            except Exception as e:
                logger.error(f"❌ Erro ao obter dados da APAC: {e}")
                estacoes = []
        else:
            estacoes = []

        resultados = []

        for bairro, props in self.bairros_criticos.items():
            try:
                ponto_bairro = props.get("centroide")  # shapely Point
                if not ponto_bairro:
                    logger.warning(f"⚠️ Bairro {bairro} sem centroide definido")
                    resultados.append(self._simular_resultado(bairro, props))
                    continue

                # Procurar estação mais próxima
                estacao_proxima = None
                menor_dist = float("inf")

                for estacao in estacoes:
                    try:
                        lat = float(estacao.get("latitude"))
                        lon = float(estacao.get("longitude"))
                        dist = calcular_distancia(ponto_bairro.y, ponto_bairro.x, lat, lon)
                        if dist < menor_dist:
                            menor_dist = dist
                            estacao_proxima = estacao
                    except Exception:
                        continue

                if estacao_proxima:
                    dados = estacao_proxima.get("Dados_completos", {})
                    precipitacao = float(dados.get("precipitacao_acumulada", 0))
                    umidade = float(dados.get("umidade_relativa", 0)) if "umidade_relativa" in dados else None
                    risco = classificar_risco(precipitacao, umidade)
                    resultado = {
                        "bairro": bairro,
                        "rpa": props.get("rpa"),
                        "risco": risco,
                        "precipitacao": precipitacao,
                        "umidade": umidade,
                        "estacao": estacao_proxima.get("nome", "Desconhecida"),
                        "distancia_km": round(menor_dist, 2),
                        "atualizado": datetime.now().isoformat(),
                    }
                else:
                    resultado = self._simular_resultado(bairro, props)

                resultados.append(resultado)

            except Exception as e:
                logger.error(f"❌ Erro ao processar bairro {bairro}: {e}")
                resultados.append(self._simular_resultado(bairro, props))

        return resultados

    def _simular_resultado(self, bairro: str, props: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para simulação caso falhem os dados da APAC"""
        risco = random.choice(["BAIXO", "MODERADO", "ALTO"])
        return {
            "bairro": bairro,
            "rpa": props.get("rpa"),
            "risco": risco,
            "precipitacao": random.uniform(0, 60),
            "umidade": random.uniform(20, 90),
            "estacao": "SIMULADO",
            "distancia_km": None,
            "atualizado": datetime.now().isoformat(),
        }

# ============================================================================ 
# EXPORTS
# ============================================================================ 
__all__ = ["FloodPredictor"]
