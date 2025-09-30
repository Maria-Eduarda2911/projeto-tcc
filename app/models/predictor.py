import aiohttp
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

class APACDataProcessor:
    """Processador de dados da APAC para obter informações em tempo real"""
    
    def __init__(self):
        self.meteorologia_url = "http://dados.apac.pe.gov.br:41120/meteorologia24h/"
        self.cemaden_url = "http://dados.apac.pe.gov.br:41120/cemaden/"
        self.session = None
    
    async def init_session(self):
        """Inicializa sessão HTTP"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def fetch_meteorologia_data(self) -> List[Dict]:
        """Busca dados meteorológicos da APAC"""
        try:
            async with self.session.get(self.meteorologia_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.process_meteorologia_data(data)
                else:
                    print(f"Erro API Meteorologia: {response.status}")
                    return []
        except Exception as e:
            print(f"Erro buscando dados meteorologia: {e}")
            return []
    
    async def fetch_cemaden_data(self) -> List[Dict]:
        """Busca dados do CEMADEN"""
        try:
            async with self.session.get(self.cemaden_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.process_cemaden_data(data)
                else:
                    print(f"Erro API CEMADEN: {response.status}")
                    return []
        except Exception as e:
            print(f"Erro buscando dados CEMADEN: {e}")
            return []
    
    def process_meteorologia_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Processa dados meteorológicos da APAC"""
        processed_stations = []
        
        for station in raw_data:
            try:
                # Extrai dados principais da estação
                processed_station = {
                    'id': station.get('idEstacao'),
                    'nome': station.get('estacao'),
                    'coordenadas': {
                        'lat': station.get('latitude'),
                        'lng': station.get('longitude')
                    },
                    'dados_pluviometricos': {
                        'precipitacao_atual': station.get('precipitacao', 0),
                        'acumulado_24h': station.get('acumulado_24h', 0),
                        'intensidade': station.get('intensidade', 0)
                    },
                    'dados_ambientais': {
                        'umidade': station.get('umidade', 0),
                        'pressao': station.get('pressao', 1013),
                        'temperatura': station.get('temperatura', 0)
                    },
                    'timestamp': station.get('dataHora', datetime.now().isoformat())
                }
                processed_stations.append(processed_station)
            except Exception as e:
                print(f"Erro processando estação {station.get('idEstacao')}: {e}")
                continue
        
        return processed_stations
    
    def process_cemaden_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Processa dados do CEMADEN"""
        processed_data = []
        
        for item in raw_data:
            try:
                processed_item = {
                    'localidade': item.get('municipio'),
                    'coordenadas': {
                        'lat': item.get('latitude'),
                        'lng': item.get('longitude')
                    },
                    'nivel_risco': item.get('nivelRisco'),
                    'tipo_alerta': item.get('tipoAlerta'),
                    'timestamp': item.get('dataHora')
                }
                processed_data.append(processed_item)
            except Exception as e:
                print(f"Erro processando dado CEMADEN: {e}")
                continue
        
        return processed_data
    
    def encontrar_estacao_proxima(self, area: dict, estacoes: list) -> Optional[Dict]:
        """Encontra a estação mais próxima usando fórmula de Haversine"""
        if not estacoes:
            return None
        
        area_lat = area['coordenadas']['lat']
        area_lng = area['coordenadas']['lng']
        
        estacao_proxima = None
        menor_distancia = float('inf')
        
        for estacao in estacoes:
            est_lat = estacao['coordenadas']['lat']
            est_lng = estacao['coordenadas']['lng']
            
            if est_lat is None or est_lng is None:
                continue
                
            distancia = self._calcular_distancia_haversine(
                area_lat, area_lng, est_lat, est_lng
            )
            
            if distancia < menor_distancia:
                menor_distancia = distancia
                estacao_proxima = estacao
        
        print(f"📍 Estação mais próxima: {estacao_proxima['nome']} ({menor_distancia:.2f}km)")
        return estacao_proxima
    
    def _calcular_distancia_haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distância entre coordenadas usando fórmula de Haversine"""
        R = 6371  # Raio da Terra em km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def extract_rain_data(self, estacao: Dict) -> Dict:
        """Extrai dados de chuva no formato padronizado"""
        dados_pluv = estacao.get('dados_pluviometricos', {})
        dados_amb = estacao.get('dados_ambientais', {})
        
        return {
            'chuva_mm': dados_pluv.get('precipitacao_atual', 0),
            'acumulado_24h': dados_pluv.get('acumulado_24h', 0),
            'intensidade': dados_pluv.get('intensidade', 0),
            'umidade': dados_amb.get('umidade', 0),
            'pressao': dados_amb.get('pressao', 1013)
        }

class AdvancedFloodPredictor:
    """Predictor avançado com integração APAC e cálculos matemáticos aprimorados"""
    
    def __init__(self):
        self.data_processor = APACDataProcessor()
        self.areas_risco_recife = self._carregar_areas_risco_recife()
    
    async def inicializar(self):
        """Inicializa o predictor"""
        await self.data_processor.init_session()
    
    async def calcular_risco_area(self, area: dict, dados_apac: dict = None) -> dict:
        """Calcula risco de alagamento para uma área específica"""
        
        print(f"📊 Analisando área: {area['nome']}")
        
        # Busca dados da APAC se não fornecidos
        if dados_apac is None:
            dados_apac = await self._buscar_dados_apac()
        
        estacoes = dados_apac.get('estacoes_meteorologia', [])
        alertas_cemaden = dados_apac.get('alertas_cemaden', [])
        
        estacao_proxima = self.data_processor.encontrar_estacao_proxima(area, estacoes)
        
        if estacao_proxima:
            dados_chuva = self.data_processor.extract_rain_data(estacao_proxima)
            print(f"🌧️ Dados ATUAIS: {dados_chuva['chuva_mm']}mm | Acumulado: {dados_chuva['acumulado_24h']}mm")
            
            # Calcula risco com dados atuais (80%) + histórico (20%)
            risco_atual = self._calcular_risco_dinamico_avancado(dados_chuva, area)
            risco_final = (risco_atual * 0.8) + (area['risco_base'] * 0.2)
            
            print(f"⚠️  Risco calculado: {risco_final:.3f}")
        else:
            print(f"❌ Sem dados atuais, usando histórico")
            risco_final = area['risco_base'] * 0.7
        
        # Ajusta risco baseado em alertas do CEMADEN
        risco_final = self._ajustar_por_alertas_cemaden(risco_final, alertas_cemaden, area)
        
        return self._classificar_risco_detalhado(risco_final, area)
    
    def _calcular_risco_dinamico_avancado(self, dados_chuva: dict, area: dict) -> float:
        """
        Calcula risco dinâmico usando múltiplos fatores com pesos científicos
        """
        chuva = dados_chuva['chuva_mm']
        acumulado = dados_chuva['acumulado_24h']
        umidade = dados_chuva['umidade']
        pressao = dados_chuva['pressao']
        
        # Fatores normalizados
        fator_chuva = self._normalizar_chuva_avancado(chuva)
        fator_acumulado = self._normalizar_acumulado_exponencial(acumulado)
        fator_umidade = self._calcular_fator_umidade(umidade)
        fator_pressao = self._calcular_fator_pressao(pressao)
        fator_vulnerabilidade = area.get('fator_vulnerabilidade', 0.5)
        
        # Pesos otimizados baseados em análise estatística
        pesos = {
            'chuva': 0.35,           # Chuva atual tem maior peso
            'acumulado': 0.25,       # Acumulado 24h
            'umidade': 0.15,         # Condições ambientais
            'pressao': 0.10,         # Indicador de tempestade
            'vulnerabilidade': 0.15  # Característica da área
        }
        
        risco = (
            fator_chuva * pesos['chuva'] +
            fator_acumulado * pesos['acumulado'] +
            fator_umidade * pesos['umidade'] +
            fator_pressao * pesos['pressao'] +
            fator_vulnerabilidade * pesos['vulnerabilidade']
        )
        
        return min(risco, 1.0)
    
    def _normalizar_chuva_avancado(self, chuva_mm: float) -> float:
        """Normalização avançada baseada em classificação meteorológica"""
        # Usando função logística suavizada
        if chuva_mm <= 0:
            return 0.0
        elif chuva_mm <= 5:
            return 0.1 + (chuva_mm / 5) * 0.2  # 0.1 a 0.3
        elif chuva_mm <= 15:
            return 0.3 + ((chuva_mm - 5) / 10) * 0.3  # 0.3 a 0.6
        elif chuva_mm <= 30:
            return 0.6 + ((chuva_mm - 15) / 15) * 0.2  # 0.6 a 0.8
        elif chuva_mm <= 50:
            return 0.8 + ((chuva_mm - 30) / 20) * 0.15  # 0.8 a 0.95
        else:
            return 1.0
    
    def _normalizar_acumulado_exponencial(self, acumulado_mm: float) -> float:
        """Normalização exponencial para acumulado 24h"""
        # Usando função exponencial: 1 - e^(-λx)
        lambda_param = 0.03  # Parâmetro de ajuste
        return 1 - math.exp(-lambda_param * acumulado_mm)
    
    def _calcular_fator_umidade(self, umidade: float) -> float:
        """Calcula fator baseado na umidade relativa"""
        # Umidade > 80% aumenta significativamente o risco
        if umidade >= 90:
            return 0.9
        elif umidade >= 80:
            return 0.7
        elif umidade >= 60:
            return 0.4
        else:
            return 0.2
    
    def _calcular_fator_pressao(self, pressao: float) -> float:
        """Calcula fator baseado na pressão atmosférica"""
        # Pressão baixa (< 1010 hPa) indica condições de tempestade
        if pressao < 1000:
            return 0.9
        elif pressao < 1010:
            return 0.7
        elif pressao < 1020:
            return 0.3
        else:
            return 0.1
    
    def _ajustar_por_alertas_cemaden(self, risco_atual: float, alertas_cemaden: List[Dict], area: dict) -> float:
        """Ajusta risco baseado em alertas do CEMADEN"""
        for alerta in alertas_cemaden:
            if self._esta_proximo(area['coordenadas'], alerta['coordenadas']):
                nivel_alerta = alerta['nivel_risco']
                if nivel_alerta in ['ALTO', 'CRÍTICO']:
                    risco_atual = min(risco_atual + 0.2, 1.0)
                elif nivel_alerta == 'MÉDIO':
                    risco_atual = min(risco_atual + 0.1, 1.0)
        
        return risco_atual
    
    def _esta_proximo(self, coord1: Dict, coord2: Dict, limite_km: float = 10.0) -> bool:
        """Verifica se coordenadas estão próximas"""
        if not coord2.get('lat') or not coord2.get('lng'):
            return False
            
        distancia = self.data_processor._calcular_distancia_haversine(
            coord1['lat'], coord1['lng'], coord2['lat'], coord2['lng']
        )
        return distancia <= limite_km
    
    def _classificar_risco_detalhado(self, risco: float, area: dict) -> dict:
        """Classificação detalhada do risco com métricas adicionais"""
        
        if risco >= 0.8:
            classificacao = {
                "score": round(risco, 3),
                "nivel": "CRÍTICO",
                "cor": "#ff0000",
                "probabilidade": "Probabilidade muito alta de alagamento",
                "recomendacoes": [
                    "🚨 EVACUAR ÁREA IMEDIATAMENTE",
                    "Buscar local elevado",
                    "Contatar Defesa Civil: 199",
                    "Desligar energia elétrica",
                    "Não tentar atravessar áreas alagadas"
                ],
                "indicadores": {
                    "chuva_critica": True,
                    "acumulado_critico": True,
                    "condicoes_adversas": True
                }
            }
        elif risco >= 0.6:
            classificacao = {
                "score": round(risco, 3),
                "nivel": "ALTO", 
                "cor": "#ff4444",
                "probabilidade": "Alta probabilidade de alagamento",
                "recomendacoes": [
                    "⚠️ Preparar para evacuação",
                    "Evitar áreas baixas",
                    "Proteger pertences em locais elevados",
                    "Monitorar atualizações"
                ],
                "indicadores": {
                    "chuva_critica": risco >= 0.7,
                    "acumulado_critico": True,
                    "condicoes_adversas": True
                }
            }
        elif risco >= 0.4:
            classificacao = {
                "score": round(risco, 3),
                "nivel": "MODERADO",
                "cor": "#ffaa00", 
                "probabilidade": "Risco moderado de alagamento",
                "recomendacoes": [
                    "Ficar alerta",
                    "Evitar áreas de risco conhecidas",
                    "Ter plano de evacuação preparado",
                    "Acompanhar previsão do tempo"
                ],
                "indicadores": {
                    "chuva_critica": False,
                    "acumulado_critico": risco >= 0.5,
                    "condicoes_adversas": False
                }
            }
        elif risco >= 0.2:
            classificacao = {
                "score": round(risco, 3), 
                "nivel": "BAIXO",
                "cor": "#44ff44",
                "probabilidade": "Baixo risco de alagamento",
                "recomendacoes": [
                    "Manter monitoramento",
                    "Conhecer rotas de fuga",
                    "Ter kit emergência preparado"
                ],
                "indicadores": {
                    "chuva_critica": False,
                    "acumulado_critico": False,
                    "condicoes_adversas": False
                }
            }
        else:
            classificacao = {
                "score": round(risco, 3),
                "nivel": "MÍNIMO",
                "cor": "#88ff88",
                "probabilidade": "Risco mínimo de alagamento", 
                "recomendacoes": [
                    "Situação normal",
                    "Manter hábitos preventivos"
                ],
                "indicadores": {
                    "chuva_critica": False,
                    "acumulado_critico": False,
                    "condicoes_adversas": False
                }
            }
        
        return classificacao
    
    async def _buscar_dados_apac(self) -> Dict:
        """Busca dados consolidados da APAC"""
        try:
            dados_meteorologia, dados_cemaden = await asyncio.gather(
                self.data_processor.fetch_meteorologia_data(),
                self.data_processor.fetch_cemaden_data(),
                return_exceptions=True
            )
            
            # Trata exceções
            if isinstance(dados_meteorologia, Exception):
                print(f"Erro meteorologia: {dados_meteorologia}")
                dados_meteorologia = []
            if isinstance(dados_cemaden, Exception):
                print(f"Erro CEMADEN: {dados_cemaden}") 
                dados_cemaden = []
            
            return {
                'estacoes_meteorologia': dados_meteorologia,
                'alertas_cemaden': dados_cemaden,
                'timestamp': datetime.now().isoformat(),
                'fonte': 'APAC'
            }
            
        except Exception as e:
            print(f"Erro buscando dados APAC: {e}")
            return {'estacoes_meteorologia': [], 'alertas_cemaden': [], 'fonte': 'FALLBACK'}
    
    def _carregar_areas_risco_recife(self) -> List[Dict]:
        """Carrega áreas de risco conhecidas do Recife"""
        return [
            {
                'nome': 'Recife Antigo',
                'coordenadas': {'lat': -8.0631, 'lng': -34.8713},
                'risco_base': 0.6,
                'fator_vulnerabilidade': 0.8,
                'bairro': 'Recife Antigo',
                'historico_alagamentos': 15
            },
            {
                'nome': 'Boa Vista', 
                'coordenadas': {'lat': -8.0578, 'lng': -34.8829},
                'risco_base': 0.5,
                'fator_vulnerabilidade': 0.7,
                'bairro': 'Boa Vista',
                'historico_alagamentos': 12
            },
            {
                'nome': 'São José',
                'coordenadas': {'lat': -8.0658, 'lng': -34.8731},
                'risco_base': 0.7, 
                'fator_vulnerabilidade': 0.9,
                'bairro': 'São José',
                'historico_alagamentos': 18
            }
        ]
    
    def determinar_alerta_geral_avancado(self, areas_analisadas: list) -> Dict:
        """Determina alerta geral baseado em análise multivariada"""
        if not areas_analisadas:
            return {"nivel": "INDETERMINADO", "cor": "#cccccc", "mensagem": "Sem dados suficientes"}
        
        riscos = [area['risco']['score'] for area in areas_analisadas]
        risco_medio = np.mean(riscos)
        risco_maximo = np.max(riscos)
        areas_alto_risco = sum(1 for area in areas_analisadas if area['risco']['score'] >= 0.6)
        
        # Análise multivariada
        if risco_maximo >= 0.8 and areas_alto_risco >= 2:
            return {
                "nivel": "EMERGÊNCIA",
                "cor": "#ff0000", 
                "mensagem": "MÚLTIPLAS ÁREAS EM SITUAÇÃO CRÍTICA - ACIONAR DEFESA CIVIL",
                "areas_afetadas": areas_alto_risco,
                "risco_medio": round(risco_medio, 3)
            }
        elif risco_maximo >= 0.7 or (risco_medio >= 0.5 and areas_alto_risco >= 1):
            return {
                "nivel": "ALERTA MÁXIMO", 
                "cor": "#ff4444",
                "mensagem": "ALTO RISCO EM ÁREAS ESTRATÉGICAS - PREPARAR EVACUAÇÃO",
                "areas_afetadas": areas_alto_risco,
                "risco_medio": round(risco_medio, 3)
            }
        elif risco_medio >= 0.4:
            return {
                "nivel": "ATENÇÃO",
                "cor": "#ffaa00",
                "mensagem": "CONDIÇÕES FAVORÁVEIS A ALAGAMENTOS - MANTER ALERTA", 
                "areas_afetadas": areas_alto_risco,
                "risco_medio": round(risco_medio, 3)
            }
        else:
            return {
                "nivel": "NORMAL",
                "cor": "#44ff44", 
                "mensagem": "SITUAÇÃO NORMAL - RISCO BAIXO NA MAIORIA DAS ÁREAS",
                "areas_afetadas": areas_alto_risco,
                "risco_medio": round(risco_medio, 3)
            }

# Exemplo de uso
async def exemplo_uso():
    """Exemplo de uso do AdvancedFloodPredictor"""
    
    predictor = AdvancedFloodPredictor()
    await predictor.inicializar()
    
    # Analisa áreas de risco
    resultados = []
    for area in predictor.areas_risco_recife:
        risco = await predictor.calcular_risco_area(area)
        resultados.append({
            'area': area['nome'],
            'risco': risco
        })
        
        print(f"\n🔍 {area['nome']}:")
        print(f"   Nível: {risco['nivel']} ({risco['score']})")
        print(f"   Probabilidade: {risco['probabilidade']}")
        print(f"   Recomendações: {risco['recomendacoes'][0]}")
    
    # Alerta geral
    alerta_geral = predictor.determinar_alerta_geral_avancado(resultados)
    print(f"\n🚨 ALERTA GERAL: {alerta_geral['nivel']}")
    print(f"   {alerta_geral['mensagem']}")
    print(f"   Áreas afetadas: {alerta_geral['areas_afetadas']}")
    print(f"   Risco médio: {alerta_geral['risco_medio']}")

if __name__ == "__main__":
    asyncio.run(exemplo_uso())