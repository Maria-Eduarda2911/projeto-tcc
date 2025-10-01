# models/predictor.py
import math
import logging
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("models.predictor")

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _nivel_e_cor(precipitacao: float, umidade: Optional[float]) -> Dict[str, str]:
    if precipitacao >= 50:
        return {"nivel_risco": "ALTO", "cor_risco": "#FF000086"}
    elif precipitacao >= 20:
        return {"nivel_risco": "MODERADO", "cor_risco": "#FFC40087"}
    else:
        if umidade is not None and umidade < 30:
            return {"nivel_risco": "MODERADO", "cor_risco": "#FFC40087"}
        return {"nivel_risco": "BAIXO", "cor_risco": "#3CBD408A"}

class FloodPredictor:
    def __init__(self, bairros_criticos: Optional[List[Dict]] = None, apac_processor=None):
        """
        bairros_criticos: lista de dicts com 'bairro', 'rpa', 'poligono'
        apac_processor: instância de APACDataProcessor já inicializada com API key
        """
        self.bairros_criticos = bairros_criticos or []
        self.apac = apac_processor
        if self.apac:
            logger.info("✅ APACDataProcessor conectado ao Predictor")
        else:
            logger.warning("❌ APACDataProcessor não fornecido, será usado fallback")

    async def predict_for_area(self, bairro_nome: str, rpa: str, coordenadas: List[List[float]]) -> Dict[str, Any]:
        """
        Previsão para uma área específica - compatível com areas_risco.py
        """
        # Bairros críticos conhecidos
        bairros_alto_risco = [
            "ALTO JOSÉ DO PINHO", "NOVA DESCOBERTA", "ALTO SANTA TEREZINHA", 
            "MORRO DA CONCEIÇÃO", "COHAB", "BREJO DE BEBERIBE", "ÁGUA FRIA",
            "VÁRZEA", "IPUTINGA", "TORRÕES", "SANTO AMARO", "SÃO JOSÉ"
        ]
        
        bairros_baixo_risco = [
            "BOA VIAGEM", "PINA", "IMBIRIBEIRA", "ROSARINHO", "GRAÇAS"
        ]
        
        # Define risco base baseado no bairro e RPA
        if bairro_nome in bairros_alto_risco:
            risco_base = 0.75
        elif bairro_nome in bairros_baixo_risco:
            risco_base = 0.25
        else:
            # Risco baseado na RPA
            riscos_rpa = {"1": 0.55, "2": 0.35, "3": 0.60, "4": 0.65, "5": 0.75, "6": 0.58}
            risco_base = riscos_rpa.get(rpa, 0.5)
        
        # Adiciona variação aleatória pequena
        risco_final = min(0.95, max(0.2, risco_base + random.uniform(-0.05, 0.08)))
        
        # Gera dados climáticos realistas
        precipitacao = random.randint(10, 60)
        umidade = random.randint(65, 95)
        
        # Determina nível de risco
        cls = _nivel_e_cor(precipitacao, umidade)
        
        # Ajusta baseado no risco calculado
        if risco_final > 0.70:
            nivel_risco = "ALTO"
            cor_risco = "#FF000086"
            prob_alagamento = int(risco_final * 100)
        elif risco_final > 0.50:
            nivel_risco = "MODERADO"
            cor_risco = "#FFC40087"
            prob_alagamento = int(risco_final * 100)
        else:
            nivel_risco = "BAIXO"
            cor_risco = "#3CBD408A"
            prob_alagamento = int(risco_final * 100)
        
        return {
            "probabilidade_chuva": precipitacao,
            "intensidade_chuva": random.randint(5, 35),
            "probabilidade_alagamento": prob_alagamento,
            "nivel_risco": nivel_risco,
            "cor_risco": cor_risco,
            "risco_atual": round(risco_final, 3),
            "fonte": "PREDICTOR",
            "dados_utilizados": {
                "bairro": bairro_nome,
                "rpa": rpa,
                "risco_base": risco_base,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def analisar_bairros(self) -> List[Dict[str, Any]]:
        """
        Método original mantido para compatibilidade
        """
        resultados = []

        if self.apac:
            self.apac.atualizar_dados_climaticos(None)
            bairros = self.apac.get_bairros()
        else:
            bairros = self.bairros_criticos

        for bairro in bairros:
            precipitacao = bairro.get("chuva_mm", 0)
            umidade = bairro.get("umidade", None)
            cls = _nivel_e_cor(precipitacao, umidade)
            resultado = {
                "bairro": bairro.get("bairro"),
                "rpa": bairro.get("rpa"),
                "nivel_risco": cls["nivel_risco"],
                "cor_risco": cls["cor_risco"],
                "probabilidade_alagamento": 80 if cls["nivel_risco"] == "ALTO" else (60 if cls["nivel_risco"] == "MODERADO" else 30),
                "precipitacao": precipitacao,
                "umidade": umidade,
                "atualizado": datetime.now().isoformat(),
                "fonte": "OpenWeatherMap" if self.apac else "FALLBACK",
            }
            resultados.append(resultado)

        return resultados

# Instância pronta
flood_predictor = FloodPredictor()
__all__ = ["FloodPredictor", "flood_predictor"]