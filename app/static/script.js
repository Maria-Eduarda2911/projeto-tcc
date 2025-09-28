var map = L.map('map').setView([-8.0631, -34.8713], 12);
var areasLayer = L.layerGroup().addTo(map);
var alertaGeral = '';
var ultimaAtualizacao = '';

function inicializarMapa() {
    // Mapa mais limpo para melhor visualização dos polígonos
   L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);
    map.getPane('tilePane').style.filter = 'brightness(0.85) contrast(1.2)';

    // Adicionar controle de camadas
    L.control.scale({imperial: false}).addTo(map);
}

function mostrarContextoAlerta() {
    const contextoDiv = document.getElementById('contexto-alerta');
    if (!contextoDiv) {
        const novaDiv = document.createElement('div');
        novaDiv.id = 'contexto-alerta';
        novaDiv.className = 'contexto-info';
        document.getElementById('sidebar').insertBefore(novaDiv, document.getElementById('alerta-geral'));
    }
    
    document.getElementById('contexto-alerta').innerHTML = `
        <div class="contexto-content">
            <div class="fonte-info">
                <strong>📊 Fonte dos dados:</strong>
                <div>• APAC - Dados em tempo real</div>
                <div>• Defesa Civil do Recife</div>
                <div>• CPRM - Serviço Geológico</div>
            </div>
            <div class="atualizacao-info">
                <strong>🕒 Última atualização:</strong>
                <div id="hora-atualizacao">${ultimaAtualizacao}</div>
            </div>
        </div>
    `;
}

async function carregarDados() {
    try {
        mostrarLoading(true);
        
        const response = await fetch('/api/previsao');
        if (!response.ok) throw new Error('Erro na resposta da API');
        
        const data = await response.json();
        ultimaAtualizacao = new Date().toLocaleString('pt-BR');
        processarDados(data);
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        mostrarErro('Erro ao carregar dados da APAC. Verifique a conexão.');
    } finally {
        mostrarLoading(false);
    }
}

function processarDados(data) {
    atualizarAlertaGeral(data.alerta_geral);
    mostrarContextoAlerta();
    
    areasLayer.clearLayers();
    document.getElementById('areas-list').innerHTML = '';
    
    // Ordenar áreas por risco (maior primeiro)
    const areasOrdenadas = data.areas.sort((a, b) => b.risco_atual - a.risco_atual);
    
    areasOrdenadas.forEach((area, index) => {
        adicionarAreaNoMapa(area);
        adicionarAreaNaLista(area, index);
    });
    
    // Atualizar hora da última atualização
    document.getElementById('hora-atualizacao').textContent = ultimaAtualizacao;
}

function atualizarAlertaGeral(alerta) {
    const alertaDiv = document.getElementById('alerta-geral');
    
    let classe = 'alert-banner ';
    let icone = '';
    let titulo = '';
    
    if (alerta.includes('LARANJA')) {
        classe += 'alert-alto';
        icone = '🚨 ';
        titulo = 'ALERTA GERAL - RISCO ALTO';
    } else if (alerta.includes('AMARELA')) {
        classe += 'alert-moderado';
        icone = '⚠️ ';
        titulo = 'ATENÇÃO - RISCO MODERADO';
    } else {
        classe += 'alert-baixo';
        icone = '✅ ';
        titulo = 'SITUAÇÃO NORMAL';
    }
    
    alertaDiv.innerHTML = `
        <div class="${classe}">
            <div class="alert-title">${icone} ${titulo}</div>
            <div class="alert-subtitle">${alerta}</div>
        </div>
    `;
}

function adicionarAreaNoMapa(area) {
    // Criar polígono com estilo melhorado
    var polygon = L.polygon(area.poligono, {
        color: area.cor_risco,
        fillColor: area.cor_risco,
        fillOpacity: 0.4,
        weight: 3,
        opacity: 0.8,
        className: 'area-polygon'
    }).addTo(areasLayer);
    
    // Calcular centro do polígono para o marcador
    var center = calcularCentroPoligono(area.poligono);
    
    // Adicionar marcador no centro com ícone de risco
    var icon = L.divIcon({
        html: `<div style="background: ${area.cor_risco}; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">${area.risco_atual.toFixed(1)}</div>`,
        className: 'risk-marker',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    var marker = L.marker(center, {icon: icon}).addTo(areasLayer);
    
    // Popup com informações completas
    var popupContent = criarPopupContent(area);
    polygon.bindPopup(popupContent);
    marker.bindPopup(popupContent);
    
    // Eventos de interação
    polygon.on('click', function() {
        map.fitBounds(polygon.getBounds(), { padding: [20, 20] });
        this.openPopup();
    });
    
    marker.on('click', function() {
        map.fitBounds(polygon.getBounds(), { padding: [20, 20] });
        this.openPopup();
    });
}

function criarPopupContent(area) {
    const pontosCriticos = area.pontos_criticos.slice(0, 3).join(', ') + 
                          (area.pontos_criticos.length > 3 ? '...' : '');
    
    return `
        <div class="popup-content">
            <div class="popup-header" style="border-left: 4px solid ${area.cor_risco};">
                <h3 style="margin: 0 0 5px 0; color: ${area.cor_risco};">${area.nome}</h3>
                <div style="font-size: 0.9em; color: #666;">${area.regiao}</div>
            </div>
            
            <div class="popup-risk-info">
                <div class="risk-level">
                    <span>Nível de Risco:</span>
                    <strong style="color: ${area.cor_risco}">${area.nivel_risco}</strong>
                </div>
                <div class="risk-score">
                    <span>Score:</span>
                    <strong>${area.risco_atual.toFixed(3)}</strong>
                </div>
                <div class="risk-probability">
                    <span>Probabilidade:</span>
                    <strong>${area.probabilidade_alagamento}</strong>
                </div>
            </div>
            
            <div class="popup-details">
                <div class="bairros-section">
                    <strong>📍 Bairros:</strong>
                    <div>${area.bairros.join(', ')}</div>
                </div>
                
                <div class="pontos-criticos-section">
                    <strong>⚠️ Pontos Críticos:</strong>
                    <div>${pontosCriticos}</div>
                </div>
                
                <div class="contexto-section">
                    <strong>📋 Contexto:</strong>
                    <div>Baseado em dados oficiais da Defesa Civil</div>
                </div>
                
                <div class="fonte-section">
                    <strong>🌧️ Fonte:</strong>
                    <div>Dados em tempo real da APAC</div>
                </div>
            </div>
        </div>
    `;
}

function adicionarAreaNaLista(area, index) {
    const areasList = document.getElementById('areas-list');
    const card = document.createElement('div');
    
    card.className = `area-card ${area.nivel_risco.toLowerCase()} fade-in`;
    card.onclick = () => centralizarArea(area);
    
    const pontosCriticos = area.pontos_criticos.slice(0, 2).join(', ') + 
                          (area.pontos_criticos.length > 2 ? '...' : '');
    
    card.innerHTML = `
        <div class="area-header">
            <div class="area-name">${area.nome}</div>
            <div class="area-risk risk-${area.nivel_risco.toLowerCase()}">
                ${area.nivel_risco}
            </div>
        </div>
        
        <div class="area-score" style="color: ${area.cor_risco}; font-weight: bold; font-size: 1.2em; text-align: center; margin: 5px 0;">
            Score: ${area.risco_atual.toFixed(3)}
        </div>
        
        <div class="area-details">
            <div class="detail-item">
                <span class="detail-icon">📍</span>
                <span class="detail-text">${area.regiao}</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">🏘️</span>
                <span class="detail-text">${area.bairros.slice(0, 2).join(', ')}${area.bairros.length > 2 ? '...' : ''}</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">⚠️</span>
                <span class="detail-text">${pontosCriticos}</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">🌧️</span>
                <span class="detail-text">Dados em tempo real</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">🕒</span>
                <span class="detail-text">Atualizado: Agora</span>
            </div>
        </div>
        
        <div class="area-contexto">
            <small>Fonte: Defesa Civil do Recife</small>
        </div>
    `;
    
    areasList.appendChild(card);
}

function calcularCentroPoligono(poligono) {
    const lats = poligono.map(p => p[0]);
    const lons = poligono.map(p => p[1]);
    return [
        lats.reduce((a, b) => a + b) / lats.length,
        lons.reduce((a, b) => a + b) / lons.length
    ];
}

function centralizarArea(area) {
    var bounds = L.latLngBounds(area.poligono);
    map.fitBounds(bounds, { padding: [30, 30] });
    
    // Abrir popup após centralizar
    setTimeout(() => {
        areasLayer.eachLayer(function(layer) {
            if (layer instanceof L.Polygon) {
                const layerBounds = layer.getBounds();
                if (layerBounds.toBBoxString() === bounds.toBBoxString()) {
                    layer.openPopup();
                }
            }
        });
    }, 500);
}

function mostrarLoading(mostrar) {
    const loading = document.getElementById('loading');
    if (mostrar) {
        loading.innerHTML = `
            <div class="loading-content">
                <div class="spinner"></div>
                <h3>Carregando dados de alagamento...</h3>
                <p>Conectando com APAC e analisando áreas de risco</p>
                <div class="loading-source">Fonte: Defesa Civil do Recife</div>
            </div>
        `;
        loading.style.display = 'block';
    } else {
        loading.style.display = 'none';
    }
}

function mostrarErro(mensagem) {
    const loading = document.getElementById('loading');
    loading.innerHTML = `
        <div class="error-content">
            <div class="error-icon">❌</div>
            <h3 style="color: #dc3545;">Erro de Conexão</h3>
            <p>${mensagem}</p>
            <div class="error-context">
                <strong>Contexto:</strong> Sistema usando dados históricos da Defesa Civil
            </div>
            <button onclick="carregarDados()" class="retry-btn">
                🔄 Tentar Novamente
            </button>
        </div>
    `;
    loading.style.display = 'block';
}

// Inicialização quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    inicializarMapa();
    carregarDados();
    
    // Atualizar a cada 5 minutos
    setInterval(carregarDados, 300000);
    
    // Tecla F5 para atualizar
    document.addEventListener('keydown', function(e) {
        if (e.key === 'F5') {
            e.preventDefault();
            carregarDados();
        }
    });
});

// Função para forçar atualização
function forcarAtualizacao() {
    carregarDados();
}