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
            "acumulado_24h": self.safe_float(estacao.get('acumulado_24h', 0))
        }
    
    def calcular_distancia(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcular distância aproximada entre duas coordenadas"""
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 6371 * c
    
    def encontrar_estacao_proxima(self, area: Dict, estacoes: List[Dict]) -> Dict:
        """Encontrar a estação mais próxima de uma área"""
        if not estacoes:
            return {}
        
        centro = self._calcular_centro_poligono(area['poligono'])
        estacao_proxima = None
        menor_distancia = float('inf')
        
        for estacao in estacoes:
            if 'latitude' in estacao and 'longitude' in estacao:
                dist = self.calcular_distancia(
                    centro['lat'], centro['lon'],
                    estacao['latitude'], estacao['longitude']
                )
                if dist < menor_distancia:
                    menor_distancia = dist
                    estacao_proxima = estacao
        
        return estacao_proxima or {}
    
    def _calcular_centro_poligono(self, poligono: List[List[float]]) -> Dict[str, float]:
        """Calcular o centro de um polígono"""
        lats = [p[0] for p in poligono]
        lons = [p[1] for p in poligono]
        return {'lat': sum(lats) / len(lats), 'lon': sum(lons) / len(lons)}
    
    def get_timestamp(self) -> str:
        return datetime.now().isoformat()