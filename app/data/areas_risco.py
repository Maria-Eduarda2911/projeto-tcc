# areas_risco.py
# ============================================================================
# SISTEMA DE PREVISÃO USANDO PREDICTOR COM DADOS REAIS APAC/CEMADEN
# ============================================================================

import os
import csv
import random
import asyncio
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

# Importar o predictor real que consome APAC/CEMADEN
try:
    from models.predictor import flood_predictor, initialize_predictor
    HAS_PREDICTOR = True
    print("✅ Predictor carregado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao carregar predictor: {e}")
    HAS_PREDICTOR = False
    flood_predictor = None

# Variável global para cache
_CACHE_DADOS = None
_CACHE_TIMESTAMP = None

async def inicializar_sistema():
    """Inicializa o sistema de previsão"""
    if HAS_PREDICTOR and flood_predictor:
        await initialize_predictor()
        print("✅ Sistema de previsão inicializado")

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
    return [
        round(sum(lats) / len(lats), 6),
        round(sum(lngs) / len(lngs), 6)
    ]

def calcular_area(poligono):
    """Calcula área aproximada em km²"""
    if len(poligono) < 3:
        return round(random.uniform(1.0, 5.0), 2)  # Área padrão
    
    area = 0.0
    n = len(poligono)
    
    for i in range(n):
        j = (i + 1) % n
        area += poligono[i][1] * poligono[j][0]
        area -= poligono[i][0] * poligono[j][1]
    
    area_graus = abs(area) / 2.0
    area_km2 = area_graus * 111.32 * 111.32
    return round(max(0.5, area_km2), 2)  # Mínimo 0.5 km²

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
    
    # Adicionar recomendações específicas baseadas na intensidade
    intensidade = dados_meteorologicos.get('intensidade_chuva', 0)
    if intensidade > 30:
        recomendacoes.append("🌊 Chuva intensa prevista - risco elevado de alagamentos rápidos")
    
    precipitacao = dados_meteorologicos.get('probabilidade_chuva', 0)
    if precipitacao > 80:
        recomendacoes.append("💦 Alta precipitação esperada - monitorar níveis de água")
    
    return recomendacoes

def previsao_fallback(bairro_nome: str, rpa: str) -> Dict[str, Any]:
    """Previsão de fallback quando predictor não está disponível"""
    # Cálculo simplificado baseado na RPA
    fatores_risco = {
        "1": 0.75, "2": 0.65, "3": 0.70, 
        "4": 0.55, "5": 0.60, "6": 0.50
    }
    
    risco_base = fatores_risco.get(rpa, 0.5)
    
    # Bairros críticos conhecidos
    bairros_criticos = ["RECIFE ANTIGO", "SANTO AMARO", "BOA VISTA", "SÃO JOSÉ", "COELHOS", 
                        "ILHA DO LEITE", "ILHA DO RETIRO", "PAISSANDU", "DERBY", "SANTO ANTÔNIO"]
    if bairro_nome in bairros_criticos:
        risco_base += 0.15
    
    risco_final = min(0.9, max(0.3, risco_base + random.uniform(-0.05, 0.08)))
    
    if risco_final > 0.7:
        nivel = "ALTO"
        cor = "#FF4444"
    elif risco_final > 0.4:
        nivel = "MODERADO"
        cor = "#FFA500"
    else:
        nivel = "BAIXO" 
        cor = "#4CAF50"
    
    return {
        'probabilidade_chuva': random.randint(40, 80),
        'intensidade_chuva': random.randint(10, 35),
        'probabilidade_alagamento': int(risco_final * 100),
        'nivel_risco': nivel,
        'cor_risco': cor,
        'risco_atual': round(risco_final, 3),
        'fonte': 'SIMULAÇÃO',
        'dados_utilizados': {
            'risco_base': risco_base,
            'bairro_critico': bairro_nome in bairros_criticos,
            'timestamp': datetime.now().isoformat()
        }
    }

async def carregar_shapefile_com_previsor():
    """Carrega shapefile usando predictor com dados APAC/CEMADEN em tempo real"""
    bairros_data = []
    shapefile_path = os.path.join(os.path.dirname(__file__), 'bairros-polygon.shp')
    
    print(f"📁 Verificando shapefile: {shapefile_path}")
    print(f"📁 Existe: {os.path.exists(shapefile_path)}")
    print(f"📁 HAS_SHAPEFILE: {HAS_SHAPEFILE}")
    
    if not os.path.exists(shapefile_path):
        print("❌ Shapefile não encontrado!")
        # Listar arquivos na pasta data para debug
        data_dir = os.path.dirname(__file__)
        print(f"📁 Arquivos em {data_dir}:")
        for file in os.listdir(data_dir):
            print(f"   - {file}")
        return await carregar_fallback()
    
    if not HAS_SHAPEFILE:
        print("❌ PyShp não disponível!")
        return await carregar_fallback()
    
    try:
        print("📁 Carregando shapefile com predictor APAC/CEMADEN...")
        sf = shapefile.Reader(shapefile_path)
        rpa_por_bairro = carregar_rpas_csv()
        
        # Inicializar predictor se disponível
        if HAS_PREDICTOR:
            await inicializar_sistema()
        
        total_features = len(sf)
        print(f"📁 Total de features no shapefile: {total_features}")
        
        # Verificar campos disponíveis
        fields = sf.fields
        print(f"📁 Campos disponíveis: {[field[0] for field in fields]}")
        
        bairros_processados = 0
        bairros_ignorados = 0
        
        for i, shape_record in enumerate(sf.shapeRecords()):
            properties = shape_record.record
            
            # Debug: ver todos os campos para os primeiros registros
            if i < 3:  # Apenas para os primeiros 3 registros
                print(f"🔍 Registro {i} - propriedades: {properties}")
            
            # Tentar diferentes campos para nome do bairro
            bairro_nome = None
            for idx, field in enumerate(properties):
                field_str = str(field).strip().upper()
                if (field_str and 
                    field_str != "NONE" and 
                    field_str != "NULL" and
                    len(field_str) > 2 and
                    not field_str.isdigit()):
                    bairro_nome = field_str
                    break
            
            # Se não encontrou, usar índice 1 como fallback
            if not bairro_nome and len(properties) > 1:
                bairro_nome = str(properties[1]).strip().upper()
            
            # Tentar diferentes campos para RPA
            rpa_shapefile = None
            for idx, field in enumerate(properties):
                field_str = str(field).strip()
                if field_str in ["1", "2", "3", "4", "5", "6"]:
                    rpa_shapefile = field_str
                    break
            
            # Se não encontrou, tentar campos específicos
            if not rpa_shapefile and len(properties) > 2:
                rpa_shapefile = str(properties[2]).strip()
            if not rpa_shapefile and len(properties) > 3:
                rpa_shapefile = str(properties[3]).strip()
            
            print(f"🔍 Bairro {i}: '{bairro_nome}' | RPA: '{rpa_shapefile}'")
            
            # Usar RPA do CSV se disponível, senão do shapefile
            rpa = rpa_por_bairro.get(bairro_nome, rpa_shapefile)
            if not rpa or rpa == "0":
                rpa = "1"  # RPA padrão
            
            # Obter polígono
            geometria = shape_record.shape
            coordenadas = []
            
            for ponto in geometria.points:
                if len(ponto) >= 2:
                    lat, lng = ponto[1], ponto[0]  # Converter para [lat, lng]
                    coordenadas.append([round(lat, 6), round(lng, 6)])
            
            # Critérios mais flexíveis para incluir bairro
            if (bairro_nome and 
                bairro_nome != "DESCONHECIDO" and 
                bairro_nome != "NONE" and
                len(bairro_nome) > 1 and
                coordenadas):
                
                # 1. OBTER PREVISÃO EM TEMPO REAL
                if HAS_PREDICTOR and flood_predictor:
                    try:
                        previsao = await flood_predictor.predict_for_area(
                            bairro_nome=bairro_nome,
                            rpa=rpa,
                            coordenadas=coordenadas
                        )
                    except Exception as e:
                        print(f"❌ Erro no predictor para {bairro_nome}: {e}")
                        previsao = previsao_fallback(bairro_nome, rpa)
                else:
                    previsao = previsao_fallback(bairro_nome, rpa)
                
                # 2. PROCESSAR DADOS DA PREVISÃO
                bairro_data = {
                    "id": len(bairros_data) + 1,
                    "nome": bairro_nome,
                    "regiao": f"RPA {rpa}",
                    "nivel_risco": previsao['nivel_risco'],
                    "probabilidade_alagamento": previsao['probabilidade_alagamento'],
                    "cor_risco": previsao['cor_risco'],
                    "risco_atual": previsao['risco_atual'],
                    "centro": calcular_centro(coordenadas),
                    "poligono": coordenadas,
                    "area_km2": calcular_area(coordenadas),
                    "dados_meteorologicos": {
                        "probabilidade_chuva": previsao.get('probabilidade_chuva', 0),
                        "intensidade_chuva": previsao.get('intensidade_chuva', 0),
                        "fonte": previsao.get('fonte', 'APAC/CEMADEN'),
                        "timestamp": previsao.get('dados_utilizados', {}).get('timestamp', datetime.now().isoformat())
                    },
                    "detalhes_calculo": previsao.get('dados_utilizados', {}),
                    "recomendacoes": gerar_recomendacoes(previsao['nivel_risco'], previsao),
                    "timestamp_analise": datetime.now().isoformat()
                }
                
                print(f"✅ {bairro_nome} - {previsao['nivel_risco']} ({previsao['probabilidade_alagamento']}%) - Fonte: {previsao['fonte']}")
                bairros_data.append(bairro_data)
                bairros_processados += 1
            else:
                bairros_ignorados += 1
                print(f"❌ Ignorado: {bairro_nome} - RPA: {rpa} - Coordenadas: {len(coordenadas)}")
            
            # Log de progresso a cada 10 features
            if (i + 1) % 10 == 0:
                print(f"📊 Processados {i + 1}/{total_features} features...")
        
        print(f"🎯 Total processados: {bairros_processados} bairros")
        print(f"🚫 Total ignorados: {bairros_ignorados} bairros")
        
        if bairros_processados == 0:
            print("⚠️ Nenhum bairro processado do shapefile, usando fallback")
            return await carregar_fallback()
        
        return bairros_data
        
    except Exception as e:
        print(f"❌ Erro no processamento do shapefile: {e}")
        import traceback
        traceback.print_exc()
        return await carregar_fallback()

async def carregar_fallback():
    """Carrega dados de fallback quando shapefile não está disponível"""
    print("🔄 Usando dados de fallback...")
    
    bairros_fallback = [
        {
            "id": 1,
            "nome": "RECIFE ANTIGO",
            "regiao": "RPA 1",
            "nivel_risco": "ALTO",
            "probabilidade_alagamento": 85,
            "cor_risco": "#FF4444",
            "risco_atual": 0.85,
            "centro": [-8.0631, -34.8711],
            "poligono": [
                [-8.0631, -34.8711], [-8.0580, -34.8800], [-8.0520, -34.8780],
                [-8.0480, -34.8750], [-8.0450, -34.8700], [-8.0480, -34.8650],
                [-8.0550, -34.8620], [-8.0631, -34.8711]
            ],
            "area_km2": 2.5,
            "dados_meteorologicos": {
                "probabilidade_chuva": 80,
                "intensidade_chuva": 35,
                "fonte": "SIMULAÇÃO"
            },
            "recomendacoes": [
                "🚨 Área crítica - evitar deslocamentos",
                "📞 Contatar Defesa Civil se necessário",
                "🏠 Permanecer em local elevado"
            ],
            "timestamp_analise": datetime.now().isoformat()
        },
        {
            "id": 2,
            "nome": "BOA VIAGEM", 
            "regiao": "RPA 3",
            "nivel_risco": "MODERADO",
            "probabilidade_alagamento": 60,
            "cor_risco": "#FFA500",
            "risco_atual": 0.60,
            "centro": [-8.1198, -34.9047],
            "poligono": [
                [-8.1198, -34.9047], [-8.1100, -34.8900], [-8.1000, -34.8800],
                [-8.0900, -34.8750], [-8.0850, -34.8850], [-8.0900, -34.8950],
                [-8.1000, -34.9000], [-8.1100, -34.9050], [-8.1198, -34.9047]
            ],
            "area_km2": 8.2,
            "dados_meteorologicos": {
                "probabilidade_chuva": 65,
                "intensidade_chuva": 25,
                "fonte": "SIMULAÇÃO"
            },
            "recomendacoes": [
                "⚠️ Monitorar condições da maré",
                "🚗 Evitar avenida Boa Viagem em caso de chuva",
                "🌊 Cuidado com ressaca do mar"
            ],
            "timestamp_analise": datetime.now().isoformat()
        },
        {
            "id": 3,
            "nome": "BOA VISTA",
            "regiao": "RPA 1",
            "nivel_risco": "ALTO",
            "probabilidade_alagamento": 78,
            "cor_risco": "#FF4444",
            "risco_atual": 0.78,
            "centro": [-8.0578, -34.8829],
            "poligono": [
                [-8.0578, -34.8829], [-8.0550, -34.8850], [-8.0520, -34.8870],
                [-8.0480, -34.8850], [-8.0450, -34.8820], [-8.0480, -34.8780],
                [-8.0520, -34.8750], [-8.0578, -34.8829]
            ],
            "area_km2": 1.8,
            "dados_meteorologicos": {
                "probabilidade_chuva": 75,
                "intensidade_chuva": 30,
                "fonte": "SIMULAÇÃO"
            },
            "recomendacoes": [
                "🚨 Área de risco histórico",
                "📞 Monitorar canais de drenagem",
                "🏠 Verificar pontos de alagamento"
            ],
            "timestamp_analise": datetime.now().isoformat()
        }
    ]
    return bairros_fallback

async def gerar_json_mapa_async():
    """Gera JSON completo para o frontend com dados em tempo real (assíncrono)"""
    
    print("🌊 Iniciando análise de risco...")
    
    # Carregar dados dos bairros
    bairros = await carregar_shapefile_com_previsor()
    
    # Calcular estatísticas
    alto_risco = len([b for b in bairros if b['nivel_risco'] == 'ALTO'])
    moderado_risco = len([b for b in bairros if b['nivel_risco'] == 'MODERADO'])
    baixo_risco = len(bairros) - alto_risco - moderado_risco
    
    # Determinar alerta geral
    if alto_risco > 8:
        alerta_geral = "ALERTA VERMELHO - RISCO MUITO ALTO"
        cor_alerta = "#FF0000"
    elif alto_risco > 3:
        alerta_geral = "ALERTA LARANJA - RISCO ALTO"
        cor_alerta = "#FF4444"
    elif alto_risco > 0 or moderado_risco > 5:
        alerta_geral = "ALERTA AMARELO - RISCO MODERADO"
        cor_alerta = "#FFA500"
    else:
        alerta_geral = "SITUAÇÃO NORMAL - BAIXO RISCO"
        cor_alerta = "#4CAF50"
    
    # Verificar fonte dos dados
    fontes = [b.get('dados_meteorologicos', {}).get('fonte', 'DESCONHECIDO') for b in bairros]
    fonte_principal = "APAC/CEMADEN" if "APAC" in str(fontes) else "SIMULAÇÃO"
    
    print(f"📊 Estatísticas finais: {len(bairros)} bairros, {alto_risco} alto risco")
    
    return {
        "alerta_geral": alerta_geral,
        "cor_alerta": cor_alerta,
        "previsao_gerada_em": datetime.now().isoformat(),
        "bairros": bairros,
        "estatisticas": {
            "total_bairros": len(bairros),
            "alto_risco": alto_risco,
            "moderado_risco": moderado_risco,
            "baixo_risco": baixo_risco,
            "area_total_km2": round(sum(b.get('area_km2', 0) for b in bairros), 2)
        },
        "metadados": {
            "fonte_dados": fonte_principal,
            "predictor_ativo": HAS_PREDICTOR,
            "shapefile_ativo": HAS_SHAPEFILE,
            "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
    }

# Função síncrona para compatibilidade com o main.py existente
def gerar_json_previsao():
    """Versão síncrona para compatibilidade com a API existente"""
    global _CACHE_DADOS, _CACHE_TIMESTAMP
    
    # Verificar cache (5 minutos)
    if (_CACHE_DADOS and _CACHE_TIMESTAMP and 
        (datetime.now() - _CACHE_TIMESTAMP).total_seconds() < 300):
        print("📦 Retornando dados do cache")
        return _CACHE_DADOS
    
    try:
        # Verificar se já existe um loop em execução
        try:
            loop = asyncio.get_running_loop()
            # Se já existe um loop, executar em thread separada
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(gerar_json_mapa_async()))
                resultado = future.result(timeout=60)  # Timeout de 60 segundos
        except RuntimeError:
            # Não há loop rodando, criar um novo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resultado = loop.run_until_complete(gerar_json_mapa_async())
            loop.close()
        
        # Atualizar cache
        _CACHE_DADOS = resultado
        _CACHE_TIMESTAMP = datetime.now()
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro na geração síncrona: {e}")
        import traceback
        traceback.print_exc()
        
        # Retornar dados de fallback em caso de erro
        return {
            "alerta_geral": "SISTEMA EM INICIALIZAÇÃO",
            "cor_alerta": "#FFA500",
            "previsao_gerada_em": datetime.now().isoformat(),
            "bairros": [
                {
                    "id": 1,
                    "nome": "RECIFE ANTIGO",
                    "regiao": "RPA 1",
                    "nivel_risco": "MODERADO",
                    "probabilidade_alagamento": 50,
                    "cor_risco": "#FFA500",
                    "risco_atual": 0.5,
                    "centro": [-8.0631, -34.8711],
                    "area_km2": 2.5,
                    "dados_meteorologicos": {
                        "probabilidade_chuva": 60,
                        "intensidade_chuva": 20,
                        "fonte": "SISTEMA"
                    },
                    "recomendacoes": ["Sistema em inicialização", "Aguardando dados..."],
                    "timestamp_analise": datetime.now().isoformat()
                }
            ],
            "estatisticas": {
                "total_bairros": 1,
                "alto_risco": 0,
                "moderado_risco": 1,
                "baixo_risco": 0,
                "area_total_km2": 2.5
            },
            "metadados": {
                "fonte_dados": "SISTEMA",
                "predictor_ativo": False,
                "shapefile_ativo": False,
                "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        }

if __name__ == "__main__":
    # Teste do sistema
    async def testar_sistema():
        print("🧪 Testando sistema de previsão...")
        dados = await gerar_json_mapa_async()
        print(f"📍 {len(dados['bairros'])} bairros analisados")
        print(f"🚨 Alerta: {dados['alerta_geral']}")
        print(f"📊 Estatísticas: {dados['estatisticas']}")
        print(f"🔧 Metadados: {dados['metadados']}")
        
        # Listar todos os bairros
        print("\n📋 Lista de bairros:")
        for bairro in dados['bairros']:
            print(f"  - {bairro['nome']}: {bairro['nivel_risco']} ({bairro['probabilidade_alagamento']}%)")
    
    asyncio.run(testar_sistema())