from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class DadosEstacao(Base):
    __tablename__ = "dados_estacao"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    chuva_mm = Column(Float)
    prob_chuva = Column(Float)
    acumulado_24h = Column(Float)
    saturacao = Column(Float)
    score_risco = Column(Float)
    nivel_risco = Column(String)
    inundacao_prevista_mm = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
    
    async def initialize(self):
        """Inicializar conexão com banco"""
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Criar tabelas
        Base.metadata.create_all(bind=self.engine)
    
    async def salvar_dados_estacao(self, dados: list):
        """Salvar dados da estação no banco"""
        session = self.SessionLocal()
        try:
            for ponto in dados:
                registro = DadosEstacao(
                    nome=ponto["nome"],
                    latitude=ponto["latitude"],
                    longitude=ponto["longitude"],
                    chuva_mm=ponto["chuva_mm"],
                    prob_chuva=ponto["prob_chuva"],
                    acumulado_24h=ponto["acumulado_24h"],
                    saturacao=ponto["saturacao"],
                    score_risco=ponto["score"],
                    nivel_risco=ponto["nivel"],
                    inundacao_prevista_mm=ponto["inundacao_mm"]
                )
                session.add(registro)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def obter_dados_treinamento(self, limite: int = 1000) -> list:
        """Obter dados históricos para treinamento"""
        session = self.SessionLocal()
        try:
            resultados = session.query(DadosEstacao).limit(limite).all()
            return [
                {
                    "chuva_mm": r.chuva_mm,
                    "acumulado_24h": r.acumulado_24h,
                    "prob_chuva": r.prob_chuva,
                    "saturacao": r.saturacao,
                    "score": r.score_risco,
                    "inundacao_real": r.inundacao_prevista_mm  # Nota: precisaria de dados reais
                }
                for r in resultados
            ]
        finally:
            session.close()
    
    async def obter_estatisticas(self) -> dict:
        """Obter estatísticas dos dados"""
        session = self.SessionLocal()
        try:
            total = session.query(DadosEstacao).count()
            return {
                "total_registros": total,
                "ultima_atualizacao": datetime.utcnow().isoformat()
            }
        finally:
            session.close()