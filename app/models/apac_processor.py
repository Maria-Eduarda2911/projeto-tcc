# apac_processor.py
import csv
import os
from typing import List, Dict

class APACDataProcessor:
    """
    Processa os dados da APAC/CEMADEN e fornece informações
    de risco por bairro para o predictor.
    """
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.bairros_data: List[Dict] = []

    def carregar_csv(self) -> None:
        """Carrega dados de CSV com probabilidades simuladas"""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV não encontrado: {self.csv_path}")

        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.bairros_data = []
            for row in reader:
                # Assumindo que o CSV tem colunas: bairro, rpa, risco
                self.bairros_data.append({
                    "bairro": row.get("bairro_nom", row.get("bairro", "Desconhecido")),
                    "rpa": row.get("rpa", "0"),
                    "risco": row.get("risco", "MODERADO")  # default
                })

    def get_bairros(self) -> List[Dict]:
        """Retorna lista de bairros com risco"""
        return self.bairros_data
