class FloodPredictor:
    def calcular_risco_area(self, area: dict, dados_apac: dict) -> dict:
        from services.data_processor import DataProcessor
        
        processor = DataProcessor()
        estacoes = dados_apac.get('estacoes', []) if dados_apac else []
        
        print(f"📊 Analisando área: {area['nome']}")
        
        estacao_proxima = processor.encontrar_estacao_proxima(area, estacoes)
        
        if estacao_proxima:
            dados_chuva = processor.extract_rain_data(estacao_proxima)
            print(f"🌧️ Dados ATUAIS: {dados_chuva['chuva_mm']}mm de chuva")
            
            risco_atual = self._calcular_risco_dinamico(dados_chuva)
            risco_final = (risco_atual * 0.8) + (area['risco_base'] * 0.2)
            
            print(f"⚠️  Risco calculado com dados ATUAIS: {risco_final:.3f}")
        else:
            print(f"❌ Sem dados atuais, usando histórico")
            risco_final = area['risco_base'] * 0.7
        
        return self._classificar_risco(risco_final)
    
    def _calcular_risco_dinamico(self, dados_chuva: dict) -> float:
        chuva = dados_chuva['chuva_mm']
        prob_chuva = dados_chuva['prob_chuva'] / 100.0
        acumulado = dados_chuva['acumulado_24h']
        
        fator_chuva = self._normalizar_chuva(chuva)
        fator_acumulado = self._normalizar_acumulado(acumulado)
        fator_probabilidade = prob_chuva
        
        risco = (fator_chuva * 0.5) + (fator_acumulado * 0.3) + (fator_probabilidade * 0.2)
        
        return min(risco, 1.0)
    
    def _normalizar_chuva(self, chuva_mm: float) -> float:
        if chuva_mm <= 5: return 0.1
        elif chuva_mm <= 15: return 0.3
        elif chuva_mm <= 30: return 0.6
        elif chuva_mm <= 50: return 0.8
        else: return 1.0
    
    def _normalizar_acumulado(self, acumulado_mm: float) -> float:
        if acumulado_mm <= 20: return 0.2
        elif acumulado_mm <= 40: return 0.4
        elif acumulado_mm <= 60: return 0.6
        elif acumulado_mm <= 80: return 0.8
        else: return 1.0
    
    def _classificar_risco(self, risco: float) -> dict:
        if risco >= 0.7:
            return {"score": round(risco, 3), "nivel": "ALTO", "cor": "#ff4444", "probabilidade": "Alta probabilidade de alagamento"}
        elif risco >= 0.4:
            return {"score": round(risco, 3), "nivel": "MODERADO", "cor": "#ffaa00", "probabilidade": "Risco moderado de alagamento"}
        else:
            return {"score": round(risco, 3), "nivel": "BAIXO", "cor": "#44ff44", "probabilidade": "Baixo risco de alagamento"}
    
    def determinar_alerta_geral(self, areas: list) -> str:
        riscos = [area['risco_atual'] for area in areas]
        risco_medio = sum(riscos) / len(riscos)
        
        if risco_medio >= 0.6:
            return "ALERTA LARANJA - Múltiplas áreas em risco"
        elif risco_medio >= 0.3:
            return "ATENÇÃO AMARELA - Algumas áreas em alerta"
        else:
            return "SITUAÇÃO NORMAL - Risco baixo na maioria das áreas"