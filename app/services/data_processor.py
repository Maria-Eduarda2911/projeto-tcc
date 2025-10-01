from typing import Dict, Any, List
from datetime import datetime
import math

class DataProcessor:
    def safe_float(self, val: Any, default: float = 0.0) -> float:
        """Converter para float de forma segura"""
        try:
            return float(val)
        except:
            return default
    
    def extract_rain_data(self, estacao: Dict[str, Any]) -> Dict[str, float]:
        """Extrair dados de chuva de uma estação"""
        return {
            "chuva_mm": self.safe_float(estacao.get('chuva_mm', 0)),
            "prob_chuva": self.safe_float(estacao.get('prob_chuva', 50)),
            "acumulado_24h": self.safe_float(estacao.get('acumulado_24h', 0)),
            "temperatura": self.safe_float(estacao.get('temperatura', 25.8))  # fallback médio
        }
    
    def calcular_distancia(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcular distância aproximada entre duas coordenadas em km"""
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 6371 * c
    
    def _calcular_centro_poligono(self, poligono: List[List[float]]) -> Dict[str, float]:
        """Calcular o centro de um polígono"""
        lats = [p[0] for p in poligono]
        lons = [p[1] for p in poligono]
        return {'lat': sum(lats) / len(lats), 'lon': sum(lons) / len(lons)}
    
    def interpolar_valor_por_area(
        self,
        area: Dict,
        estacoes: List[Dict],
        campo_valor: str = 'chuva_mm',
        epsilon: float = 0.001,
        valor_fallback: float = 0.0
    ) -> float:
        """
        Calcula valor interpolado para a área usando estações próximas.
        area: dict com chave 'poligono' do bairro
        estacoes: lista de dicts com latitude, longitude e campo_valor
        """
        centro = self._calcular_centro_poligono(area['poligono'])
        soma_pesos = 0.0
        valor_ponderado = 0.0

        for est in estacoes:
            if 'latitude' in est and 'longitude' in est:
                dist = self.calcular_distancia(centro['lat'], centro['lon'], est['latitude'], est['longitude'])
                dist = max(dist, epsilon)  # evita divisão por zero
                peso = 1 / dist
                valor = self.safe_float(est.get(campo_valor, valor_fallback))
                valor_ponderado += valor * peso
                soma_pesos += peso

        if soma_pesos == 0:
            return valor_fallback

        return round(valor_ponderado / soma_pesos, 2)
    
    def get_timestamp(self) -> str:
        return datetime.now().isoformat()
