# models/predictor.py
# ============================================================================
# PREDICTOR AVANÇADO COM APAC/CEMADEN - VERSÃO OTIMIZADA
# ============================================================================

import aiohttp
import asyncio
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APACDataProcessor:
    """Processador de dados da APAC para obter informações em tempo real"""
    
    def __init__(self):
        self.base_url = "http://dados.apac.pe.gov.br:41120"
        self.session = None
        self.cache_dados = {}
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutos
    
    async def init_session(self):
        """Inicializa sessão HTTP"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def get_dados_em_tempo_real(self) -> Dict[str, Any]:
        """Obtém todos os dados em tempo real da APAC"""
        
        # Verificar cache
        if (self.cache_timestamp and 
            (datetime.now() - self.cache_timestamp).seconds < self.cache_duration):
            logger.info("📦 Usando dados em cache")
            return self.cache_dados
        
        try:
            await self.init_session()
            
            # Buscar dados das APIs
            dados_meteorologia = await self._fetch_api_data("/meteorologia24h/")
            dados_cemaden = await self._fetch_api_data("/cemaden/")
            
            # Processar dados
            estacoes_processadas = self._processar_estacoes_meteorologia(dados_meteorologia)
            alertas_processados = self._processar_alertas_cemaden(dados_cemaden)
            
            self.cache_dados = {
                'estacoes_meteorologia': estacoes_processadas,
                'alertas_cemaden': alertas_processados,
                'timestamp': datetime.now().isoformat(),
                'fonte': 'APAC/CEMADEN'
            }
            self.cache_timestamp = datetime.now()
            
            logger.info(f"✅ Dados atualizados: {len(estacoes_processadas)} estações, {len(alertas_processados)} alertas")
            return self.cache_dados
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados APAC: {e}")
            return self._get_dados_fallback()
    
    async def _fetch_api_data(self, endpoint: str) -> List[Dict]:
        """Busca dados de uma API específica"""
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"⚠️ API {endpoint} retornou status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"❌ Erro na API {endpoint}: {e}")
            return []
    
    def _processar_estacoes_meteorologia(self, raw_data: List[Dict]) -> List[Dict]:
        """Processa dados das estações meteorológicas"""
        processed = []
        
        for station in raw_data:
            try:
                processed_station = {
                    'id': station.get('idEstacao'),
                    'nome': station.get('estacao', 'Desconhecida'),
                    'coordenadas': {
                        'lat': float(station.get('latitude', 0)),
                        'lng': float(station.get('longitude', 0))
                    },
                    'dados_pluviometricos': {
                        'precipitacao_atual': float(station.get('precipitacao', 0)),
                        'acumulado_24h': float(station.get('acumulado_24h', 0)),
                        'intensidade': float(station.get('intensidade', 0))
                    },
                    'dados_ambientais': {
                        'umidade': float(station.get('umidade', 0)),
                        'pressao': float(station.get('pressao', 1013)),
                        'temperatura': float(station.get('temperatura', 0))
                    },
                    'timestamp': station.get('dataHora', datetime.now().isoformat())
                }
                processed.append(processed_station)
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Erro processando estação {station.get('idEstacao')}: {e}")
                continue
        
        return processed
    
    def _processar_alertas_cemaden(self, raw_data: List[Dict]) -> List[Dict]:
        """Processa alertas do CEMADEN"""
        processed = []
        
        for alerta in raw_data:
            try:
                processed_alerta = {
                    'localidade': alerta.get('municipio', 'Desconhecida'),
                    'coordenadas': {
                        'lat': float(alerta.get('latitude', 0)),
                        'lng': float(alerta.get('longitude', 0))
                    },
                    'nivel_risco': alerta.get('nivelRisco', 'DESCONHECIDO'),
                    'tipo_alerta': alerta.get('tipoAlerta', 'DESCONHECIDO'),
                    'timestamp': alerta.get('dataHora', datetime.now().isoformat())
                }
                processed.append(processed_alerta)
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Erro processando alerta CEMADEN: {e}")
                continue
        
        return processed
    
    def encontrar_estacao_proxima(self, coordenadas_alvo: Dict, estacoes: List[Dict]) -> Optional[Dict]:
        """Encontra a estação mais próxima usando Haversine"""
        if not estacoes or not coordenadas_alvo:
            return None
        
        try:
            lat_alvo = coordenadas_alvo['lat']
            lng_alvo = coordenadas_alvo['lng']
            
            estacao_proxima = None
            menor_distancia = float('inf')
            
            for estacao in estacoes:
                est_coords = estacao['coordenadas']
                if est_coords['lat'] == 0 or est_coords['lng'] == 0:
                    continue
                
                distancia = self._calcular_distancia_haversine(
                    lat_alvo, lng_alvo, est_coords['lat'], est_coords['lng']
                )
                
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    estacao_proxima = estacao
            
            if estacao_proxima:
                logger.info(f"📍 Estação próxima: {estacao_proxima['nome']} ({menor_distancia:.1f}km)")
            return estacao_proxima
            
        except Exception as e:
            logger.error(f"❌ Erro ao encontrar estação próxima: {e}")
            return None
    
    def _calcular_distancia_haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distância entre coordenadas usando fórmula de Haversine"""
        R = 6371  # Raio da Terra em km
        
        try:
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * 
                 math.sin(delta_lon/2) * math.sin(delta_lon/2))
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            return R * c
        except Exception as e:
            logger.error(f"❌ Erro cálculo Haversine: {e}")
            return float('inf')
    
    def _get_dados_fallback(self) -> Dict[str, Any]:
        """Dados de fallback quando APIs estão indisponíveis"""
        logger.warning("🔄 Usando dados de fallback")
        return {
            'estacoes_meteorologia': [],
            'alertas_cemaden': [],
            'timestamp': datetime.now().isoformat(),
            'fonte': 'FALLBACK'
        }

class FloodPredictor:
    """Predictor principal para previsão de alagamentos"""
    
    def __init__(self):
        self.data_processor = APACDataProcessor()
        self.modelo_carregado = False
    
    async def initialize(self):
        """Inicializa o predictor"""
        try:
            await self.data_processor.init_session()
            self.modelo_carregado = True
            logger.info("✅ FloodPredictor inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro inicializando predictor: {e}")
            self.modelo_carregado = False
    
    async def predict_for_area(self, bairro_nome: str, rpa: str, coordenadas: List[List[float]] = None) -> Dict[str, Any]:
        """Faz previsão para uma área específica"""
        
        logger.info(f"🔍 Analisando {bairro_nome} (RPA {rpa})")
        
        try:
            # 1. Obter dados em tempo real
            dados_reais = await self.data_processor.get_dados_em_tempo_real()
            
            # 2. Calcular centro da área
            centro = self._calcular_centro_area(coordenadas) if coordenadas else {'lat': -8.0631, 'lng': -34.8711}
            
            # 3. Encontrar estação mais próxima
            estacao_proxima = self.data_processor.encontrar_estacao_proxima(
                centro, dados_reais['estacoes_meteorologia']
            )
            
            # 4. Calcular risco
            if estacao_proxima:
                risco_data = self._calcular_risco_avancado(estacao_proxima, bairro_nome, rpa, dados_reais['alertas_cemaden'])
            else:
                risco_data = self._calcular_risco_fallback(bairro_nome, rpa)
            
            # 5. Preparar resposta
            return self._formatar_resposta(risco_data, estacao_proxima, dados_reais['fonte'])
            
        except Exception as e:
            logger.error(f"❌ Erro na previsão para {bairro_nome}: {e}")
            return self._previsao_erro(bairro_nome, str(e))
    
    def _calcular_centro_area(self, coordenadas: List[List[float]]) -> Dict[str, float]:
        """Calcula o centro geográfico de uma área"""
        if not coordenadas:
            return {'lat': -8.0631, 'lng': -34.8711}
        
        try:
            lats = [p[0] for p in coordenadas]
            lngs = [p[1] for p in coordenadas]
            return {
                'lat': sum(lats) / len(lats),
                'lng': sum(lngs) / len(lngs)
            }
        except Exception as e:
            logger.error(f"❌ Erro calculando centro: {e}")
            return {'lat': -8.0631, 'lng': -34.8711}
    
    def _calcular_risco_avancado(self, estacao: Dict, bairro_nome: str, rpa: str, alertas_cemaden: List[Dict]) -> Dict[str, Any]:
        """Calcula risco avançado usando dados reais"""
        
        # Extrair dados da estação
        dados_pluv = estacao['dados_pluviometricos']
        dados_amb = estacao['dados_ambientais']
        
        chuva_atual = dados_pluv['precipitacao_atual']
        acumulado_24h = dados_pluv['acumulado_24h']
        intensidade = dados_pluv['intensidade']
        umidade = dados_amb['umidade']
        pressao = dados_amb['pressao']
        
        logger.info(f"🌧️ Dados reais: {chuva_atual}mm | Acum: {acumulado_24h}mm | Int: {intensidade}mm/h")
        
        # 1. Fatores meteorológicos
        fator_chuva = self._normalizar_chuva(chuva_atual)
        fator_acumulado = self._normalizar_acumulado(acumulado_24h)
        fator_intensidade = self._normalizar_intensidade(intensidade)
        fator_umidade = self._calcular_fator_umidade(umidade)
        fator_pressao = self._calcular_fator_pressao(pressao)
        
        # 2. Fator de vulnerabilidade da RPA
        fator_vulnerabilidade = self._get_fator_vulnerabilidade_rpa(rpa)
        
        # 3. Fator do bairro (áreas críticas conhecidas)
        fator_bairro = self._get_fator_bairro(bairro_nome)
        
        # 4. Cálculo do risco base
        pesos = {
            'chuva': 0.25,
            'acumulado': 0.20,
            'intensidade': 0.15,
            'umidade': 0.10,
            'pressao': 0.05,
            'vulnerabilidade': 0.15,
            'bairro': 0.10
        }
        
        risco_base = (
            fator_chuva * pesos['chuva'] +
            fator_acumulado * pesos['acumulado'] +
            fator_intensidade * pesos['intensidade'] +
            fator_umidade * pesos['umidade'] +
            fator_pressao * pesos['pressao'] +
            fator_vulnerabilidade * pesos['vulnerabilidade'] +
            fator_bairro * pesos['bairro']
        )
        
        # 5. Ajustar por alertas CEMADEN
        risco_ajustado = self._ajustar_por_cemaden(risco_base, estacao['coordenadas'], alertas_cemaden)
        
        return {
            'risco_calculado': min(0.95, max(0.1, risco_ajustado)),
            'fatores': {
                'chuva_atual': chuva_atual,
                'acumulado_24h': acumulado_24h,
                'intensidade': intensidade,
                'umidade': umidade,
                'pressao': pressao,
                'fator_vulnerabilidade': fator_vulnerabilidade
            }
        }
    
    def _normalizar_chuva(self, chuva_mm: float) -> float:
        """Normaliza precipitação atual"""
        if chuva_mm <= 0:
            return 0.0
        elif chuva_mm <= 2:
            return 0.2
        elif chuva_mm <= 5:
            return 0.4
        elif chuva_mm <= 10:
            return 0.6
        elif chuva_mm <= 20:
            return 0.8
        else:
            return 1.0
    
    def _normalizar_acumulado(self, acumulado_mm: float) -> float:
        """Normaliza acumulado 24h"""
        if acumulado_mm <= 10:
            return 0.2
        elif acumulado_mm <= 25:
            return 0.4
        elif acumulado_mm <= 50:
            return 0.6
        elif acumulado_mm <= 80:
            return 0.8
        else:
            return 1.0
    
    def _normalizar_intensidade(self, intensidade_mmh: float) -> float:
        """Normaliza intensidade da chuva"""
        if intensidade_mmh <= 5:
            return 0.2
        elif intensidade_mmh <= 15:
            return 0.4
        elif intensidade_mmh <= 30:
            return 0.6
        elif intensidade_mmh <= 50:
            return 0.8
        else:
            return 1.0
    
    def _calcular_fator_umidade(self, umidade: float) -> float:
        """Calcula fator baseado na umidade"""
        if umidade >= 90:
            return 0.8
        elif umidade >= 80:
            return 0.6
        elif umidade >= 60:
            return 0.4
        else:
            return 0.2
    
    def _calcular_fator_pressao(self, pressao: float) -> float:
        """Calcula fator baseado na pressão"""
        if pressao < 1005:
            return 0.8  # Baixa pressão = mau tempo
        elif pressao < 1015:
            return 0.5
        else:
            return 0.2
    
    def _get_fator_vulnerabilidade_rpa(self, rpa: str) -> float:
        """Retorna fator de vulnerabilidade baseado na RPA"""
        fatores = {
            "1": 0.9,  # Centro - alta vulnerabilidade
            "2": 0.7,  # Zona Norte
            "3": 0.8,  # Zona Sul (influência marítima)
            "4": 0.5,  # Zona Oeste
            "5": 0.6,  # Zona Oeste
            "6": 0.4   # Zona Norte
        }
        return fatores.get(rpa, 0.5)
    
    def _get_fator_bairro(self, bairro_nome: str) -> float:
        """Retorna fator específico do bairro"""
        bairros_criticos = {
            "RECIFE ANTIGO": 0.9,
            "SANTO AMARO": 0.8,
            "BOA VISTA": 0.8,
            "SÃO JOSÉ": 0.9,
            "COELHOS": 0.7,
            "SOLEDADE": 0.7,
            "ARRUDA": 0.6,
            "ÁGUA FRIA": 0.6
        }
        return bairros_criticos.get(bairro_nome.upper(), 0.5)
    
    def _ajustar_por_cemaden(self, risco_base: float, coordenadas: Dict, alertas_cemaden: List[Dict]) -> float:
        """Ajusta risco baseado em alertas do CEMADEN"""
        risco_ajustado = risco_base
        
        for alerta in alertas_cemaden:
            if self._esta_proximo(coordenadas, alerta['coordenadas']):
                if alerta['nivel_risco'] in ['ALTO', 'CRÍTICO']:
                    risco_ajustado = min(risco_ajustado + 0.2, 1.0)
                elif alerta['nivel_risco'] == 'MÉDIO':
                    risco_ajustado = min(risco_ajustado + 0.1, 1.0)
        
        return risco_ajustado
    
    def _esta_proximo(self, coord1: Dict, coord2: Dict, limite_km: float = 15.0) -> bool:
        """Verifica se coordenadas estão próximas"""
        try:
            distancia = self.data_processor._calcular_distancia_haversine(
                coord1['lat'], coord1['lng'], coord2['lat'], coord2['lng']
            )
            return distancia <= limite_km
        except:
            return False
    
    def _calcular_risco_fallback(self, bairro_nome: str, rpa: str) -> Dict[str, Any]:
        """Calcula risco de fallback quando não há dados reais"""
        logger.warning(f"🔄 Usando cálculo fallback para {bairro_nome}")
        
        fator_vulnerabilidade = self._get_fator_vulnerabilidade_rpa(rpa)
        fator_bairro = self._get_fator_bairro(bairro_nome)
        
        # Risco base moderado para fallback
        risco_base = (fator_vulnerabilidade + fator_bairro) / 2
        
        return {
            'risco_calculado': risco_base,
            'fatores': {
                'chuva_atual': 0,
                'acumulado_24h': 0,
                'intensidade': 0,
                'umidade': 0,
                'pressao': 1013,
                'fator_vulnerabilidade': fator_vulnerabilidade,
                'fallback': True
            }
        }
    
    def _formatar_resposta(self, risco_data: Dict, estacao: Optional[Dict], fonte: str) -> Dict[str, Any]:
        """Formata a resposta final do predictor"""
        
        risco = risco_data['risco_calculado']
        fatores = risco_data['fatores']
        
        # Classificar risco
        if risco >= 0.7:
            nivel = "ALTO"
            cor = "#FF4444"
            probabilidade = "Alta probabilidade de alagamento"
        elif risco >= 0.4:
            nivel = "MODERADO"
            cor = "#FFA500"
            probabilidade = "Risco moderado de alagamento"
        else:
            nivel = "BAIXO"
            cor = "#4CAF50"
            probabilidade = "Baixo risco de alagamento"
        
        return {
            'probabilidade_chuva': int(fatores.get('chuva_atual', 0) * 10),  # Converter mm para %
            'intensidade_chuva': fatores.get('intensidade', 0),
            'probabilidade_alagamento': int(risco * 100),
            'nivel_risco': nivel,
            'cor_risco': cor,
            'risco_atual': round(risco, 3),
            'fonte': fonte,
            'dados_utilizados': {
                'estacao_proxima': estacao['nome'] if estacao else 'Nenhuma',
                'precipitacao_atual': fatores.get('chuva_atual', 0),
                'acumulado_24h': fatores.get('acumulado_24h', 0),
                'intensidade_chuva': fatores.get('intensidade', 0),
                'timestamp': datetime.now().isoformat()
            },
            'probabilidade_descricao': probabilidade
        }
    
    def _previsao_erro(self, bairro_nome: str, erro: str) -> Dict[str, Any]:
        """Retorna previsão de erro"""
        return {
            'probabilidade_chuva': 0,
            'intensidade_chuva': 0,
            'probabilidade_alagamento': 0,
            'nivel_risco': 'INDETERMINADO',
            'cor_risco': '#CCCCCC',
            'risco_atual': 0,
            'fonte': 'ERRO',
            'erro': erro,
            'probabilidade_descricao': f'Erro na previsão: {erro}'
        }

# Instância global do predictor
flood_predictor = FloodPredictor()

async def initialize_predictor():
    """Inicializa o predictor global"""
    await flood_predictor.initialize()

# Exemplo de uso rápido
async def test_predictor():
    """Testa o predictor"""
    await initialize_predictor()
    
    # Teste com um bairro
    resultado = await flood_predictor.predict_for_area(
        bairro_nome="Recife Antigo",
        rpa="1",
        coordenadas=[[-8.0631, -34.8711], [-8.0620, -34.8700]]
    )
    
    print(f"🔍 Resultado do teste:")
    print(f"   Bairro: Recife Antigo")
    print(f"   Risco: {resultado['nivel_risco']} ({resultado['probabilidade_alagamento']}%)")
    print(f"   Fonte: {resultado['fonte']}")

if __name__ == "__main__":
    asyncio.run(test_predictor())