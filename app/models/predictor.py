# models/predictor.py
import math
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("models.predictor")

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    import math as m
    phi1, phi2 = m.radians(lat1), m.radians(lat2)
    dphi = m.radians(lat2 - lat1)
    dlambda = m.radians(lon2 - lon1)
    a = m.sin(dphi / 2) ** 2 + m.cos(phi1) * m.cos(phi2) * m.sin(dlambda / 2) ** 2
    return 2 * R * m.atan2(m.sqrt(a), m.sqrt(1 - a))

def _nivel_e_cor(precipitacao: float, umidade: Optional[float]) -> Dict[str, str]:
    # Padronize aqui para "medio" se seu front usa essa string (em vez de "MODERADO")
    if precipitacao >= 50:
        return {"nivel_risco": "alto", "cor_risco": "#FF000086"}
    elif precipitacao >= 20:
        return {"nivel_risco": "medio", "cor_risco": "#FFC40087"}
    else:
        # Umidade muito baixa pode indicar risco medio mesmo com pouca chuva
        if umidade is not None and umidade < 30:
            return {"nivel_risco": "medio", "cor_risco": "#FFC40087"}
        return {"nivel_risco": "baixo", "cor_risco": "#3CBD408A"}

class FloodPredictor:
    def __init__(self, bairros_criticos: Optional[Dict[str, Dict]] = None):
        self.bairros_criticos = bairros_criticos or {}
        try:
            from models.apac_processor import APACDataProcessor
            self.apac = APACDataProcessor()
            logger.info("✅ APACDataProcessor inicializado")
        except Exception as e:
            self.apac = None
            logger.warning(f"❌ APACDataProcessor indisponível, usando fallback: {e}")

    async def analisar_bairros(self) -> List[Dict[str, Any]]:
        estacoes = []
        if self.apac:
            try:
                dados_apac = await self.apac.get_dados_em_tempo_real()
                estacoes = dados_apac.get("estacoes_meteorologia", [])
                logger.info(f"📡 Estações recebidas da APAC: {len(estacoes)}")
            except Exception as e:
                logger.error(f"❌ Erro ao obter dados da APAC: {e}")

        resultados = []
        for bairro, props in self.bairros_criticos.items():
            ponto = props.get("centroide")
            if not ponto:
                logger.warning(f"⚠️ Bairro sem centroide: {bairro} → fallback")
                resultados.append(self._fallback_unificado(bairro, props))
                continue

            estacao_proxima, menor_dist = None, float("inf")
            for est in estacoes:
                try:
                    lat = float(est.get("latitude"))
                    lon = float(est.get("longitude"))
                    dist = calcular_distancia(ponto.y, ponto.x, lat, lon)
                    if dist < menor_dist:
                        menor_dist = dist
                        estacao_proxima = est
                except Exception:
                    continue

            if estacao_proxima:
                dados = estacao_proxima.get("Dados_completos", {}) or {}
                precipitacao = float(dados.get("precipitacao_acumulada", 0) or 0)
                umidade = float(dados.get("umidade_relativa")) if "umidade_relativa" in dados else None
                cls = _nivel_e_cor(precipitacao, umidade)
                resultado = {
                    "bairro": bairro,
                    "rpa": props.get("rpa"),
                    "nivel_risco": cls["nivel_risco"],
                    "cor_risco": cls["cor_risco"],
                    "probabilidade_alagamento": 80 if cls["nivel_risco"] == "alto" else (60 if cls["nivel_risco"] == "medio" else 30),
                    "precipitacao": precipitacao,
                    "umidade": umidade,
                    "estacao": estacao_proxima.get("nome", "Desconhecida"),
                    "distancia_km": round(menor_dist, 2),
                    "atualizado": datetime.now().isoformat(),
                    "fonte": "APAC/CEMADEN",
                }
                logger.info(f"✅ Predictor usado: {bairro} via {resultado['estacao']} ({resultado['distancia_km']} km)")
                resultados.append(resultado)
            else:
                logger.info(f"🔄 Sem estação próxima para {bairro} → fallback")
                resultados.append(self._fallback_unificado(bairro, props))

        return resultados

    def _fallback_unificado(self, bairro: str, props: Dict[str, Any]) -> Dict[str, Any]:
        # Fallback determinístico mínimo (sem aleatoriedade, se quiser, integre seu histórico por RPA aqui)
        rpa = str(props.get("rpa"))
        # Perfil base por RPA (ajuste com seu histórico real)
        perfil = {"1": 0.70, "2": 0.60, "3": 0.65, "4": 0.50, "5": 0.55, "6": 0.45}
        risco = perfil.get(rpa, 0.55)
        cls = (
            {"nivel_risco": "alto", "cor_risco": "#FF000086"}
            if risco >= 0.8 else
            {"nivel_risco": "medio", "cor_risco": "#FFC40087"} if risco >= 0.5
            else {"nivel_risco": "baixo", "cor_risco": "#3CBD408A"}
        )
        return {
            "bairro": bairro,
            "rpa": rpa,
            "nivel_risco": cls["nivel_risco"],
            "cor_risco": cls["cor_risco"],
            "probabilidade_alagamento": int(risco * 100),
            "precipitacao": None,
            "umidade": None,
            "estacao": "SEM DADOS",
            "distancia_km": None,
            "atualizado": datetime.now().isoformat(),
            "fonte": "FALLBACK",
        }

# Se você quer importar uma instância pronta:
flood_predictor = FloodPredictor()
__all__ = ["FloodPredictor", "flood_predictor"]
