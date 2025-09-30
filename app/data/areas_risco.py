# areas_risco.py
# ============================================================================ 
# SISTEMA DE PREVISÃO USANDO PREDICTOR COM DADOS REAIS APAC/CEMADEN
# ============================================================================

import os
import csv
import random
import asyncio
import aiohttp
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any

try:
    import shapefile
    HAS_SHAPEFILE = True
    print("✅ PyShp carregado com sucesso")
except ImportError:
    print("❌ pip install pyshp")
    HAS_SHAPEFILE = False

# Importar predictor real
try:
    from models.predictor import flood_predictor, initialize_predictor
    HAS_PREDICTOR = True
    print("✅ Predictor carregado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao carregar predictor: {e}")
    HAS_PREDICTOR = False
    flood_predictor = None

# Importar bairros críticos de módulo separado
try:
    from data.bairros_criticos import BAIRROS_CRITICOS
except ImportError:
    BAIRROS_CRITICOS = {}
    print("⚠️ BAIRROS_CRITICOS não encontrado, usando fallback")

# Cache global
_CACHE_DADOS = None
_CACHE_TIMESTAMP = None
_CACHE_DADOS_REAIS = None
_CACHE_DADOS_REAIS_TIMESTAMP = None

# ============================================================================ 
# CONSTANTES DAS APIS
# ============================================================================

# URLs das APIs
API_CEMADEN_ACUMULADOS = "https://sws.cemaden.gov.br/PED/api/ui/#/Acumulados/getAccum"
API_APAC_CEMADEN = "http://dados.apac.pe.gov.br:41120/cemaden/"
API_APAC_METEOROLOGIA = "http://dados.apac.pe.gov.br:41120/meteorologia24h/"

# Headers para as requisições
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json'
}

# ============================================================================ 
# FUNÇÕES PARA CONSUMO DAS APIS
# ============================================================================

async def buscar_dados_cemaden_acumulados():
    """Busca dados acumulados do CEMADEN"""
    try:
        async with aiohttp.ClientSession() as session:
            # A URL fornecida parece ser uma documentação, vamos tentar a API real
            url = "https://sws.cemaden.gov.br/PED/api/Accumulated/GetAccumulated"
            params = {
                'lat': '-8.0631',
                'lon': '-34.8711',
                'radius': '50'
            }
            
            async with session.get(url, params=params, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ CEMADEN Acumulados: Status {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Erro CEMADEN Acumulados: {e}")
        return None

async def buscar_dados_apac_cemaden():
    """Busca dados da APAC/CEMADEN"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_APAC_CEMADEN, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ APAC CEMADEN: Status {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Erro APAC CEMADEN: {e}")
        return None

async def buscar_dados_apac_meteorologia():
    """Busca dados meteorológicos da APAC"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_APAC_METEOROLOGIA, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ APAC Meteorologia: Status {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Erro APAC Meteorologia: {e}")
        return None

async def buscar_dados_reais_todas_fontes():
    """Busca dados de todas as fontes em paralelo"""
    try:
        # Executa todas as requisições em paralelo
        resultados = await asyncio.gather(
            buscar_dados_cemaden_acumulados(),
            buscar_dados_apac_cemaden(),
            buscar_dados_apac_meteorologia(),
            return_exceptions=True
        )
        
        dados_consolidados = {
            'cemaden_acumulados': resultados[0] if not isinstance(resultados[0], Exception) else None,
            'apac_cemaden': resultados[1] if not isinstance(resultados[1], Exception) else None,
            'apac_meteorologia': resultados[2] if not isinstance(resultados[2], Exception) else None,
            'timestamp_coleta': datetime.now().isoformat(),
            'hora_atualizacao': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        
        # Log do status
        fontes_ativas = sum(1 for key, value in dados_consolidados.items() 
                           if value is not None and key not in ['timestamp_coleta', 'hora_atualizacao'])
        print(f"📡 Fontes ativas: {fontes_ativas}/3")
        
        return dados_consolidados
        
    except Exception as e:
        print(f"❌ Erro geral na coleta de dados: {e}")
        return await gerar_dados_simulados()

async def gerar_dados_simulados():
    """Gera dados simulados quando as APIs não estão disponíveis"""
    print("⚠️ Usando dados simulados - APIs não disponíveis")
    
    # Simula dados realistas baseados em padrões reais
    return {
        'cemaden_acumulados': {
            'estacoes': [
                {
                    'codigo': '3304557',
                    'nome': 'Recife Centro',
                    'municipio': 'Recife',
                    'acumulado_chuva_1h': round(random.uniform(5, 25), 1),
                    'acumulado_chuva_24h': round(random.uniform(15, 80), 1),
                    'latitude': -8.0631,
                    'longitude': -34.8711,
                    'dataHora': datetime.now().isoformat()
                }
            ],
            'totalEstacoes': 1
        },
        'apac_cemaden': {
            'nivel_rios': [
                {
                    'nome': 'Rio Capibaribe',
                    'local': 'Recife',
                    'nivel_atual': round(random.uniform(1.5, 3.5), 2),
                    'status': 'NORMAL' if random.random() > 0.3 else 'ALERTA',
                    'coordenadas': [-8.0631, -34.8711]
                }
            ],
            'alertas': []
        },
        'apac_meteorologia': {
            'tempo_atual': {
                'temperatura': round(random.uniform(25, 32), 1),
                'umidade': random.randint(65, 95),
                'pressao': round(random.uniform(1010, 1015), 1),
                'vento_velocidade': round(random.uniform(5, 15), 1),
                'vento_direcao': random.choice(['NE', 'E', 'SE', 'S']),
                'condicao': random.choice(['Chuvoso', 'Nublado', 'Parcialmente Nublado'])
            },
            'previsao_24h': []
        },
        'timestamp_coleta': datetime.now().isoformat(),
        'hora_atualizacao': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'fonte': 'SIMULAÇÃO'
    }

def processar_dados_reais_para_bairros(dados_reais, bairro_nome):
    """Processa dados reais para enriquecer a previsão por bairro"""
    if not dados_reais or dados_reais.get('fonte') == 'SIMULAÇÃO':
        return {
            'dados_reais': False,
            'acumulado_chuva_1h': round(random.uniform(0, 20), 1),
            'acumulado_chuva_24h': round(random.uniform(10, 60), 1),
            'temperatura_atual': round(random.uniform(25, 32), 1),
            'umidade': random.randint(70, 95),
            'vazao_rios': round(random.uniform(1.0, 4.0), 2),
            'hora_atualizacao': datetime.now().strftime("%H:%M:%S")
        }
    
    # Processa dados reais quando disponíveis
    resultado = {
        'dados_reais': True,
        'hora_atualizacao': dados_reais.get('hora_atualizacao', datetime.now().strftime("%H:%M:%S"))
    }
    
    # Processa acumulados do CEMADEN
    if dados_reais.get('cemaden_acumulados'):
        cemaden = dados_reais['cemaden_acumulados']
        if cemaden.get('estacoes') and len(cemaden['estacoes']) > 0:
            estacao = cemaden['estacoes'][0]
            resultado['acumulado_chuva_1h'] = estacao.get('acumulado_chuva_1h', 0)
            resultado['acumulado_chuva_24h'] = estacao.get('acumulado_chuva_24h', 0)
            resultado['coordenadas_estacao'] = [estacao.get('latitude'), estacao.get('longitude')]
    
    # Processa dados meteorológicos
    if dados_reais.get('apac_meteorologia'):
        meteo = dados_reais['apac_meteorologia']
        if meteo.get('tempo_atual'):
            tempo = meteo['tempo_atual']
            resultado['temperatura_atual'] = tempo.get('temperatura')
            resultado['umidade'] = tempo.get('umidade')
            resultado['pressao'] = tempo.get('pressao')
            resultado['vento'] = {
                'velocidade': tempo.get('vento_velocidade'),
                'direcao': tempo.get('vento_direcao')
            }
            resultado['condicao'] = tempo.get('condicao')
    
    # Processa vazão dos rios
    if dados_reais.get('apac_cemaden'):
        apac = dados_reais['apac_cemaden']
        if apac.get('nivel_rios') and len(apac['nivel_rios']) > 0:
            rio = apac['nivel_rios'][0]
            resultado['vazao_rios'] = rio.get('nivel_atual')
            resultado['status_rio'] = rio.get('status')
            resultado['coordenadas_rio'] = rio.get('coordenadas')
    
    # Preenche valores faltantes com simulação
    defaults = {
        'acumulado_chuva_1h': round(random.uniform(0, 20), 1),
        'acumulado_chuva_24h': round(random.uniform(10, 60), 1),
        'temperatura_atual': round(random.uniform(25, 32), 1),
        'umidade': random.randint(70, 95),
        'vazao_rios': round(random.uniform(1.0, 4.0), 2),
        'condicao': 'Dados não disponíveis'
    }
    
    for key, default in defaults.items():
        if key not in resultado:
            resultado[key] = default
    
    return resultado

# ============================================================================ 
# FUNÇÕES AUXILIARES
# ============================================================================

def carregar_rpas_csv():
    """Carrega mapeamento de bairros para RPAs do CSV"""
    rpa_por_bairro = {}
    csv_path = os.path.join(os.path.dirname(__file__), 'bairros_recife.csv')
    
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    bairro_nome = row['bairro_n_1'].strip().upper()
                    rpa = row['rpa']
                    rpa_por_bairro[bairro_nome] = rpa
            print(f"📊 CSV carregado: {len(rpa_por_bairro)} bairros mapeados")
        except Exception as e:
            print(f"⚠️ Erro no CSV: {e}")
    else:
        print(f"❌ Arquivo CSV não encontrado: {csv_path}")
    
    return rpa_por_bairro

def calcular_centro(poligono):
    """Calcula centro geográfico do polígono"""
    if not poligono:
        return [-8.0631, -34.8711]  # Centro do Recife
    lats = [p[0] for p in poligono]
    lngs = [p[1] for p in poligono]
    return [round(sum(lats)/len(lats),6), round(sum(lngs)/len(lngs),6)]

def calcular_area(poligono):
    """Calcula área aproximada em km²"""
    if len(poligono) < 3:
        return round(random.uniform(1.0,5.0),2)
    area = 0.0
    n = len(poligono)
    for i in range(n):
        j = (i+1)%n
        area += poligono[i][1]*poligono[j][0]
        area -= poligono[i][0]*poligono[j][1]
    area_graus = abs(area)/2.0
    area_km2 = area_graus*111.32*111.32
    return round(max(0.5, area_km2),2)

def gerar_recomendacoes(nivel_risco: str, dados_meteorologicos: Dict) -> List[str]:
    """Gera recomendações baseadas no nível de risco e dados meteorológicos"""
    base_recomendacoes = {
        "ALTO": [
            "🚨 ALTO RISCO - Evitar deslocamentos",
            "📞 Acionar Defesa Civil se necessário", 
            "🏠 Permanecer em local seguro",
            "⚡ Desligar equipamentos elétricos em áreas baixas",
            "🌊 Evitar proximidade com rios e canais"
        ],
        "MODERADO": [
            "⚠️ Monitorar condições meteorológicas",
            "📱 Ficar atento a alertas oficiais",
            "🚗 Evitar vias conhecidamente alagáveis",
            "🏢 Verificar pontos de alagamento no trajeto",
            "💧 Verificar sistema de drenagem local"
        ],
        "BAIXO": [
            "✅ Situação sob controle",
            "🌧️ Manter atenção em caso de mudança no tempo", 
            "📊 Continuar monitorando previsões",
            "🏘️ Conhecer rotas alternativas"
        ],
        "INDETERMINADO": [
            "🔍 Aguardando dados atualizados",
            "📡 Verificar conexão com serviços meteorológicos",
            "⚠️ Manter precauções básicas"
        ]
    }
    recomendacoes = base_recomendacoes.get(nivel_risco, base_recomendacoes["INDETERMINADO"])
    intensidade = dados_meteorologicos.get('intensidade_chuva',0)
    if intensidade>30:
        recomendacoes.append("🌊 Chuva intensa prevista - risco elevado de alagamentos rápidos")
    precipitacao = dados_meteorologicos.get('probabilidade_chuva',0)
    if precipitacao>80:
        recomendacoes.append("💦 Alta precipitação esperada - monitorar níveis de água")
    return recomendacoes

def previsao_fallback(bairro_nome: str, rpa: str) -> Dict[str, Any]:
    """Fallback simples se predictor não estiver disponível"""
    fatores_risco = {"1":0.70,"2":0.60,"3":0.65,"4":0.50,"5":0.55,"6":0.45}
    risco_base = fatores_risco.get(rpa,0.5)
    bairros_criticos = list(BAIRROS_CRITICOS.keys())
    if bairro_nome in bairros_criticos:
        risco_base += 0.15
    risco_final = min(0.9,max(0.3,risco_base+random.uniform(-0.05,0.08)))
    if risco_final>0.72:
        nivel="ALTO"; cor="#FF000086"
    elif risco_final>0.58:
        nivel="MODERADO"; cor="#FFC40087"
    else:
        nivel="BAIXO"; cor="#3CBD408A"
    return {
        "probabilidade_chuva": random.randint(40,80),
        "intensidade_chuva": random.randint(10,35),
        "probabilidade_alagamento": int(risco_final*100),
        "nivel_risco": nivel,
        "cor_risco": cor,
        "risco_atual": round(risco_final,3),
        "fonte": "SIMULAÇÃO",
        "dados_utilizados": {"risco_base":risco_base,"bairro_critico":bairro_nome in bairros_criticos,"timestamp":datetime.now().isoformat()}
    }

# ============================================================================ 
# FUNÇÕES PRINCIPAIS
# ============================================================================

async def inicializar_sistema():
    if HAS_PREDICTOR and flood_predictor:
        from models.predictor import initialize_predictor
        await initialize_predictor()
        print("✅ Sistema de previsão inicializado")

async def carregar_shapefile_com_previsor():
    bairros_data=[]
    shapefile_path=os.path.join(os.path.dirname(__file__),'bairros-polygon.shp')
    print(f"📁 Verificando shapefile: {shapefile_path}")
    if not os.path.exists(shapefile_path):
        print("❌ Shapefile não encontrado! Usando fallback")
        return await carregar_fallback()
    if not HAS_SHAPEFILE:
        print("❌ PyShp não disponível! Usando fallback")
        return await carregar_fallback()
    
    # Busca dados reais das APIs
    global _CACHE_DADOS_REAIS, _CACHE_DADOS_REAIS_TIMESTAMP
    if not _CACHE_DADOS_REAIS or not _CACHE_DADOS_REAIS_TIMESTAMP or (datetime.now() - _CACHE_DADOS_REAIS_TIMESTAMP).total_seconds() > 300:
        print("🔄 Atualizando dados das APIs...")
        _CACHE_DADOS_REAIS = await buscar_dados_reais_todas_fontes()
        _CACHE_DADOS_REAIS_TIMESTAMP = datetime.now()
    
    try:
        sf=shapefile.Reader(shapefile_path)
        rpa_por_bairro=carregar_rpas_csv()
        if HAS_PREDICTOR:
            await inicializar_sistema()
        for i, shape_record in enumerate(sf.shapeRecords()):
            props=shape_record.record
            bairro_nome=None
            for f in props:
                s=str(f).strip().upper()
                if s and s not in ["NONE","NULL"] and len(s)>2 and not s.isdigit():
                    bairro_nome=s
                    break
            if not bairro_nome and len(props)>1:
                bairro_nome=str(props[1]).strip().upper()
            rpa=rpa_por_bairro.get(bairro_nome,"1")
            coordenadas=[[round(p[1],6),round(p[0],6)] for p in shape_record.shape.points]
            if not bairro_nome or bairro_nome=="DESCONHECIDO" or not coordenadas:
                continue
            # Previsão
            if HAS_PREDICTOR and flood_predictor:
                try:
                    previsao = await flood_predictor.predict_for_area(
                        bairro_nome=bairro_nome,
                        rpa=rpa,
                        coordenadas=coordenadas
                    )
                except Exception as e:
                    print(f"❌ Erro no predictor para {bairro_nome}: {e}")
                    previsao=previsao_fallback(bairro_nome,rpa)
            else:
                previsao=previsao_fallback(bairro_nome,rpa)
            
            # Adiciona dados reais das APIs
            dados_reais = processar_dados_reais_para_bairros(_CACHE_DADOS_REAIS, bairro_nome)
            
            bairro_data={
                "id":len(bairros_data)+1,
                "nome":bairro_nome,
                "regiao":f"RPA {rpa}",
                "nivel_risco":previsao["nivel_risco"],
                "probabilidade_alagamento":previsao["probabilidade_alagamento"],
                "cor_risco":previsao["cor_risco"],
                "risco_atual":previsao["risco_atual"],
                "centro":calcular_centro(coordenadas),
                "poligono":coordenadas,
                "area_km2":calcular_area(coordenadas),
                "dados_meteorologicos":{
                    "probabilidade_chuva":previsao.get("probabilidade_chuva",0),
                    "intensidade_chuva":previsao.get("intensidade_chuva",0),
                    "fonte":previsao.get("fonte","APAC/CEMADEN"),
                    "timestamp":previsao.get("dados_utilizados",{}).get("timestamp",datetime.now().isoformat())
                },
                "dados_reais_tempo": dados_reais,
                "detalhes_calculo":previsao.get("dados_utilizados",{}),
                "recomendacoes":gerar_recomendacoes(previsao["nivel_risco"],previsao),
                "timestamp_analise":datetime.now().isoformat()
            }
            bairros_data.append(bairro_data)
        return bairros_data
    except Exception as e:
        print(f"❌ Erro shapefile: {e}")
        return await carregar_fallback()

async def carregar_fallback():
    """Fallback hardcoded"""
    from data.bairros_criticos import BAIRROS_CRITICOS
    bairros=[]
    for i, (nome,dados) in enumerate(BAIRROS_CRITICOS.items(),start=1):
        # Processa dados reais mesmo no fallback
        dados_reais = processar_dados_reais_para_bairros(_CACHE_DADOS_REAIS, nome)
        
        bairros.append({
            "id":i,
            "nome":nome,
            "regiao":f"RPA {dados.get('rpa','1')}",
            "nivel_risco":"ALTO",
            "probabilidade_alagamento":85,
            "cor_risco":"#FF4444",
            "risco_atual":0.85,
            "centro":[dados.get('centroide').y,dados.get('centroide').x] if dados.get('centroide') else [-8.0631,-34.8711],
            "poligono":[],
            "area_km2":2.5,
            "dados_meteorologicos":{"probabilidade_chuva":80,"intensidade_chuva":35,"fonte":"SIMULAÇÃO"},
            "dados_reais_tempo": dados_reais,
            "recomendacoes":["🚨 Área crítica - evitar deslocamentos","📞 Contatar Defesa Civil se necessário","🏠 Permanecer em local seguro"],
            "timestamp_analise":datetime.now().isoformat()
        })
    return bairros

async def gerar_json_mapa_async():
    """Gera JSON completo para frontend"""
    bairros=await carregar_shapefile_com_previsor()
    alto=len([b for b in bairros if b["nivel_risco"]=="ALTO"])
    moderado=len([b for b in bairros if b["nivel_risco"]=="MODERADO"])
    baixo=len(bairros)-alto-moderado
    
    # Determina alerta geral baseado nos dados reais
    dados_reais_disponiveis = any(b.get('dados_reais_tempo', {}).get('dados_reais', False) for b in bairros)
    
    if alto>8: 
        alerta_geral="ALERTA VERMELHO - RISCO MUITO ALTO"; cor_alerta="#FF0000"
    elif alto>3: 
        alerta_geral="ALERTA LARANJA - RISCO ALTO"; cor_alerta="#FF4444"
    elif alto>0 or moderado>5: 
        alerta_geral="ALERTA AMARELO - RISCO MODERADO"; cor_alerta="#FFA500"
    else: 
        alerta_geral="SITUAÇÃO NORMAL - BAIXO RISCO"; cor_alerta="#4CAF50"
    
    fontes=[b.get("dados_meteorologicos",{}).get("fonte","DESCONHECIDO") for b in bairros]
    fonte_principal="APAC/CEMADEN" if any("APAC" in f for f in fontes) else "SIMULAÇÃO"
    
    # Adiciona informações das APIs reais
    info_apis = {
        "apis_ativas": dados_reais_disponiveis,
        "hora_atualizacao_dados": _CACHE_DADOS_REAIS.get('hora_atualizacao') if _CACHE_DADOS_REAIS else datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "fontes_consultadas": ["CEMADEN Acumulados", "APAC CEMADEN", "APAC Meteorologia"]
    }
    
    return {
        "alerta_geral":alerta_geral,
        "cor_alerta":cor_alerta,
        "previsao_gerada_em":datetime.now().isoformat(),
        "bairros":bairros,
        "estatisticas":{
            "total_bairros":len(bairros),
            "alto_risco":alto,
            "moderado_risco":moderado,
            "baixo_risco":baixo,
            "area_total_km2":round(sum(b.get("area_km2",0) for b in bairros),2)
        },
        "dados_tempo_reais": info_apis,
        "metadados":{
            "fonte_dados":fonte_principal,
            "predictor_ativo":HAS_PREDICTOR,
            "shapefile_ativo":HAS_SHAPEFILE,
            "apis_reais_ativas": dados_reais_disponiveis,
            "ultima_atualizacao":datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
    }

def gerar_json_previsao():
    """Versão síncrona para API"""
    global _CACHE_DADOS,_CACHE_TIMESTAMP
    if _CACHE_DADOS and _CACHE_TIMESTAMP and (datetime.now()-_CACHE_TIMESTAMP).total_seconds()<300:
        return _CACHE_DADOS
    try:
        try:
            loop=asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future=executor.submit(lambda: asyncio.run(gerar_json_mapa_async()))
                resultado=future.result(timeout=60)
        except RuntimeError:
            loop=asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resultado=loop.run_until_complete(gerar_json_mapa_async())
            loop.close()
        _CACHE_DADOS=resultado
        _CACHE_TIMESTAMP=datetime.now()
        return resultado
    except Exception as e:
        print(f"❌ Erro síncrono: {e}")
        return {"alerta_geral":"SISTEMA EM INICIALIZAÇÃO","cor_alerta":"#FFA500","previsao_gerada_em":datetime.now().isoformat(),"bairros":[],"estatisticas":{"total_bairros":0,"alto_risco":0,"moderado_risco":0,"baixo_risco":0,"area_total_km2":0},"metadados":{"fonte_dados":"SISTEMA","predictor_ativo":False,"shapefile_ativo":False,"ultima_atualizacao":datetime.now().strftime("%d/%m/%Y %H:%M:%S")}}

# ============================================================================ 
# TESTE LOCAL
# ============================================================================

if __name__=="__main__":
    async def testar():
        print("🧪 Testando sistema...")
        print("📡 Conectando às APIs...")
        
        # Testa conexão com APIs
        dados_apis = await buscar_dados_reais_todas_fontes()
        print(f"✅ Dados das APIs coletados: {dados_apis.get('hora_atualizacao')}")
        
        dados=await gerar_json_mapa_async()
        print(f"📍 {len(dados['bairros'])} bairros analisados")
        print(f"🚨 Alerta: {dados['alerta_geral']}")
        print(f"📊 Estatísticas: {dados['estatisticas']}")
        print(f"🕒 Hora atualização: {dados['dados_tempo_reais']['hora_atualizacao_dados']}")
        print(f"🌡️ Dados reais disponíveis: {dados['metadados']['apis_reais_ativas']}")
        
        # Mostra exemplo de dados reais de um bairro
        if dados['bairros']:
            primeiro_bairro = dados['bairros'][0]
            dados_reais = primeiro_bairro.get('dados_reais_tempo', {})
            print(f"\n📋 Exemplo de dados para {primeiro_bairro['nome']}:")
            print(f"  🌧️ Acumulado 1h: {dados_reais.get('acumulado_chuva_1h')}mm")
            print(f"  🌡️ Temperatura: {dados_reais.get('temperatura_atual')}°C")
            print(f"  💧 Umidade: {dados_reais.get('umidade')}%")
            print(f"  🌊 Vazão: {dados_reais.get('vazao_rios')}m")
            print(f"  🕒 Atualizado: {dados_reais.get('hora_atualizacao')}")
    
    asyncio.run(testar())