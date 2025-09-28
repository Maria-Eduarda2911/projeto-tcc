import aiohttp
from typing import Dict, Any

class APACClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=15.0)
    
    async def get_dados_meteorologia(self) -> Dict[str, Any]:
        """Obter dados meteorológicos da APAC"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.base_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return self._get_dados_exemplo()
        except Exception as e:
            print(f"Erro APAC: {e}")
            return self._get_dados_exemplo()
    
    def _get_dados_exemplo(self) -> Dict[str, Any]:
        """Dados de exemplo quando a APAC está offline"""
        return {
            "estacoes": [
                {
                    "nome": "Estação Centro",
                    "latitude": -8.0631,
                    "longitude": -34.8713,
                    "chuva_mm": 25.5,
                    "prob_chuva": 80.0,
                    "acumulado_24h": 68.2
                },
                {
                    "nome": "Estação Zona Norte", 
                    "latitude": -8.0285,
                    "longitude": -34.9043,
                    "chuva_mm": 18.3,
                    "prob_chuva": 75.0,
                    "acumulado_24h": 45.7
                }
            ]
        }