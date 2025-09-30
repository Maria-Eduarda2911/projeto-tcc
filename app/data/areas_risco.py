# areas_risco.py
# ============================================================================
# SISTEMA DE MONITORAMENTO - MAPA COM SHAPEFILE REAL
# ============================================================================

import os
import csv
import random
from datetime import datetime
from typing import List, Dict, Any

try:
    import shapefile
    HAS_SHAPEFILE = True
except ImportError:
    print("❌ pip install pyshp")
    HAS_SHAPEFILE = False

def carregar_shapefile_completo():
    """Carrega TODOS os polígonos do shapefile e cruza com CSV"""
    bairros_data = []
    
    shapefile_path = os.path.join(os.path.dirname(__file__), 'bairros-polygon.shp')
    
    if not os.path.exists(shapefile_path) or not HAS_SHAPEFILE:
        print("❌ Shapefile não encontrado ou biblioteca indisponível")
        return carregar_fallback()
    
    try:
        print("📁 Carregando shapefile completo...")
        sf = shapefile.Reader(shapefile_path)
        
        # Carregar mapeamento do CSV
        rpa_por_bairro = carregar_rpas_csv()
        
        # Processar cada feature do shapefile
        for shape_record in sf.shapeRecords():
            properties = shape_record.record
            
            # Extrair dados do shapefile
            bairro_nome = properties[1] if len(properties) > 1 else "Desconhecido"
            rpa_shapefile = properties[2] if len(properties) > 2 else "0"
            
            # Obter RPA do CSV ou do shapefile
            rpa = rpa_por_bairro.get(bairro_nome, rpa_shapefile)
            
            # Obter polígono
            geometria = shape_record.shape
            coordenadas = []
            
            for ponto in geometria.points:
                if len(ponto) >= 2:
                    lat, lng = ponto[1], ponto[0]  # Converter para [lat, lng]
                    coordenadas.append([round(lat, 6), round(lng, 6)])
            
            if bairro_nome and bairro_nome != "Desconhecido" and coordenadas:
                # Calcular risco
                risco_calculado, nivel_risco, cor_risco = calcular_risco_realista(rpa, bairro_nome)
                probabilidade = int(risco_calculado * 100)
                
                bairro_data = {
                    "id": len(bairros_data) + 1,
                    "nome": bairro_nome.upper(),  # Padronizar para maiúsculas
                    "regiao": f"RPA {rpa}",
                    "nivel_risco": nivel_risco,
                    "probabilidade_alagamento": probabilidade,
                    "cor_risco": cor_risco,
                    "risco_atual": risco_calculado,
                    "centro": calcular_centro(coordenadas),
                    "poligono": coordenadas,
                    "area_km2": round(calcular_area(coordenadas), 2),
                    "recomendacoes": [
                        "Monitorar condições meteorológicas",
                        "Verificar alertas da Defesa Civil",
                        "Evitar áreas alagáveis em chuva forte"
                    ]
                }
                bairros_data.append(bairro_data)
                print(f"✅ {bairro_nome} - RPA {rpa}")
        
        print(f"🎯 Total: {len(bairros_data)} bairros carregados do shapefile")
        return bairros_data
        
    except Exception as e:
        print(f"❌ Erro crítico no shapefile: {e}")
        return carregar_fallback()

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
            print(f"📊 CSV: {len(rpa_por_bairro)} bairros mapeados")
        except Exception as e:
            print(f"⚠️ Erro no CSV: {e}")
    
    return rpa_por_bairro

def calcular_risco_realista(rpa, bairro_nome):
    """Calcula risco baseado na RPA e características do bairro"""
    # Fatores base por RPA
    fatores_base = {
        "1": 0.75,  # RPA 1 - Centro (alto risco histórico)
        "2": 0.65,  # RPA 2 - Zona Norte
        "3": 0.70,  # RPA 3 - Zona Sul (influência marítima)
        "4": 0.55,  # RPA 4 - Zona Oeste
        "5": 0.60,  # RPA 5 - Zona Oeste
        "6": 0.50   # RPA 6 - Zona Norte
    }
    
    # Bairros conhecidamente críticos
    bairros_criticos = [
        "RECIFE ANTIGO", "SANTO AMARO", "BOA VISTA", "SÃO JOSÉ", 
        "ARRUDA", "ÁGUA FRIA", "PEIXINHOS", "CAMPO GRANDE",
        "COELHOS", "ILHA DO LEITE", "SOLEDADE"
    ]
    
    risco_base = fatores_base.get(rpa, 0.5)
    
    # Ajustar para bairros críticos
    if bairro_nome in bairros_criticos:
        risco_base += 0.2
    
    # Variação aleatória realista
    risco_final = min(0.95, max(0.3, risco_base + random.uniform(-0.08, 0.12)))
    
    # Determinar nível de risco
    if risco_final > 0.7:
        nivel = "ALTO"
        cor = "#FF4444"
    elif risco_final > 0.5:
        nivel = "MODERADO"
        cor = "#FFA500"
    else:
        nivel = "BAIXO"
        cor = "#4CAF50"
    
    return round(risco_final, 3), nivel, cor

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
        return random.uniform(1.0, 5.0)  # Área padrão
    
    area = 0.0
    n = len(poligono)
    
    for i in range(n):
        j = (i + 1) % n
        area += poligono[i][1] * poligono[j][0]
        area -= poligono[i][0] * poligono[j][1]
    
    area_graus = abs(area) / 2.0
    area_km2 = area_graus * 111.32 * 111.32
    return max(0.5, area_km2)  # Mínimo 0.5 km²

def carregar_fallback():
    """Fallback com alguns bairros principais"""
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
            "recomendacoes": ["Área crítica - evitar deslocamentos"]
        }
    ]
    return bairros_fallback

def gerar_json_mapa():
    """Gera JSON para o frontend"""
    bairros = carregar_shapefile_completo()
    
    # Calcular estatísticas
    alto_risco = len([b for b in bairros if b['nivel_risco'] == 'ALTO'])
    moderado_risco = len([b for b in bairros if b['nivel_risco'] == 'MODERADO'])
    
    # Determinar alerta geral
    if alto_risco > 10:
        alerta_geral = "ALERTA VERMELHO - RISCO MUITO ALTO"
    elif alto_risco > 5:
        alerta_geral = "ALERTA LARANJA - RISCO ALTO"
    elif alto_risco > 0 or moderado_risco > 10:
        alerta_geral = "ALERTA AMARELO - RISCO MODERADO"
    else:
        alerta_geral = "SITUAÇÃO NORMAL - BAIXO RISCO"
    
    return {
        "alerta_geral": alerta_geral,
        "previsao_gerada_em": datetime.now().isoformat(),
        "bairros": bairros,
        "estatisticas": {
            "total_bairros": len(bairros),
            "alto_risco": alto_risco,
            "moderado_risco": moderado_risco,
            "baixo_risco": len(bairros) - alto_risco - moderado_risco
        },
        "fonte_dados": "Shapefile oficial + APAC simulada"
    }

if __name__ == "__main__":
    print("🌊 MAPA DE RISCO - RECIFE")
    data = gerar_json_mapa()
    print(f"📍 {len(data['bairros'])} bairros carregados")
    print(f"🚨 Alerta: {data['alerta_geral']}")