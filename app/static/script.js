// script.js - Sistema de Monitoramento de Alagamentos
var map = L.map('map').setView([-8.0631, -34.8713], 12);
var bairrosLayer = L.layerGroup().addTo(map);
var alertaGeral = '';
var ultimaAtualizacao = '';

// Variáveis globais para filtros
let rpaSelecionada = 'todas';
let riscoSelecionado = 'todos';
let todosBairros = []; // Para armazenar todos os bairros carregados

function inicializarMapa() {
    console.log('🗺️ Inicializando mapa...');
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
    
    L.control.scale({imperial: false}).addTo(map);
    console.log('✅ Mapa inicializado');
}

async function carregarDados() {
    try {
        console.log('🌊 Buscando dados da API...');
        mostrarLoading(true);
        
        const response = await fetch('/api/previsao');
        if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
        
        const data = await response.json();
        console.log('✅ Dados recebidos:', data);
        
        ultimaAtualizacao = new Date().toLocaleString('pt-BR');
        processarDados(data);
        mostrarLoading(false);
        
    } catch (err) {
        console.error('❌ Erro ao carregar dados:', err);
        mostrarErro('Erro ao carregar dados. Verifique a conexão.');
        mostrarLoading(false);
    }
}

function processarDados(data) {
    console.log('🔄 Processando dados...', data);
    
    if (!data || !data.bairros) {
        console.error('❌ Dados inválidos da API:', data);
        mostrarErro('Estrutura de dados inválida da API');
        return;
    }

    // Armazenar todos os bairros para filtragem
    todosBairros = data.bairros;

    atualizarAlertaGeral(data.alerta_geral || 'SITUAÇÃO NORMAL');
    atualizarEstatisticas(data.estatisticas);
    atualizarContextoAlerta(data);
    
    // Limpar layers anteriores
    bairrosLayer.clearLayers();
    
    // Limpar lista de áreas
    const areasList = document.getElementById('areas-list');
    if (areasList) areasList.innerHTML = '';
    
    console.log(`📍 Processando ${data.bairros.length} bairros...`);
    
    // Adicionar cada bairro ao mapa e à lista
    data.bairros.forEach((bairro, index) => {
        if (bairro && bairro.nome) {
            adicionarBairroNoMapa(bairro);
            adicionarBairroNaLista(bairro, index);
        }
    });
    
    console.log('✅ Processamento concluído!');
}

function adicionarBairroNoMapa(bairro) {
    // Verificar se tem polígonos
    let poligonos = [];
    
    if (bairro.poligono && Array.isArray(bairro.poligono)) {
        poligonos = [bairro.poligono];
    }
    
    if (poligonos.length === 0) {
        console.warn(`❌ Bairro sem polígonos: ${bairro.nome}`);
        criarMarcadorFallback(bairro);
        return;
    }
    
    console.log(`✅ Adicionando polígono para: ${bairro.nome}`);
    
    // Criar polígonos
    poligonos.forEach((poligono, index) => {
        const coordenadasValidas = validarCoordenadas(poligono);
        
        if (coordenadasValidas.length < 3) {
            console.warn(`⚠️ Polígono ${index} inválido para: ${bairro.nome}`);
            criarMarcadorFallback(bairro);
            return;
        }
        
        try {
            const polygon = L.polygon(coordenadasValidas, {
                color: bairro.cor_risco || '#FF4444',
                fillColor: bairro.cor_risco || '#FF4444',
                fillOpacity: 0.5,
                weight: 2,
                opacity: 0.8,
                className: 'area-polygon'
            }).addTo(bairrosLayer);
            
            const popupContent = criarPopupBairro(bairro);
            polygon.bindPopup(popupContent);
            
            // Evento de clique para centralizar
            polygon.on('click', function() {
                map.fitBounds(polygon.getBounds(), { padding: [20, 20] });
                this.openPopup();
            });
            
        } catch (error) {
            console.error(`💥 Erro ao criar polígono para ${bairro.nome}:`, error);
            criarMarcadorFallback(bairro);
        }
    });
}

function validarCoordenadas(poligono) {
    const coordenadasValidas = [];
    
    for (let i = 0; i < poligono.length; i++) {
        const ponto = poligono[i];
        
        if (!ponto || !Array.isArray(ponto) || ponto.length !== 2) {
            console.warn(`⚠️ Ponto ${i} inválido:`, ponto);
            continue;
        }
        
        const [lat, lng] = ponto;
        if (typeof lat !== 'number' || typeof lng !== 'number' || isNaN(lat) || isNaN(lng)) {
            console.warn(`⚠️ Ponto ${i} inválido (coordenadas inválidas):`, ponto);
            continue;
        }
        
        coordenadasValidas.push([lat, lng]);
    }
    
    return coordenadasValidas;
}

function criarMarcadorFallback(bairro) {
    const icon = L.divIcon({
        html: `
            <div class="bairro-marker" style="background: ${bairro.cor_risco};">
                <div class="bairro-probabilidade">${bairro.probabilidade_alagamento}%</div>
                <div class="bairro-nome">${bairro.nome.split(' ')[0]}</div>
            </div>
        `,
        className: 'risk-marker',
        iconSize: [50, 50],
        iconAnchor: [25, 25]
    });

    const marker = L.marker(bairro.centro || [-8.0631, -34.8711], {icon: icon}).addTo(bairrosLayer);
    
    const popupContent = criarPopupBairro(bairro);
    marker.bindPopup(popupContent);
    
    marker.on('click', function() {
        this.openPopup();
    });
}

function criarPopupBairro(bairro) {
    return `
        <div class="popup-content">
            <div class="popup-header" style="border-left: 4px solid ${bairro.cor_risco}">
                <h3 style="margin: 0 0 5px 0; color: ${bairro.cor_risco}">${bairro.nome}</h3>
                <div style="font-size: 0.9em; color: #666">${bairro.regiao}</div>
            </div>
            
            <div class="popup-risk-info">
                <div class="risk-level">
                    <span>Nível de Risco:</span>
                    <strong style="color: ${bairro.cor_risco}">${bairro.nivel_risco}</strong>
                </div>
                <div class="risk-probability">
                    <span>Probabilidade:</span>
                    <strong>${bairro.probabilidade_alagamento}%</strong>
                </div>
                <div class="risk-score">
                    <span>Score:</span>
                    <strong>${bairro.risco_atual || 0}</strong>
                </div>
            </div>
            
            <div class="popup-details">
                <div><strong>Área:</strong> ${bairro.area_km2 || 'N/A'} km²</div>
            </div>
            
            <div class="popup-recomendacoes">
                <strong>📋 Recomendações:</strong>
                <ul style="margin: 5px 0; padding-left: 15px;">
                    ${bairro.recomendacoes ? bairro.recomendacoes.map(rec => `<li>${rec}</li>`).join('') : 
                    '<li>Monitorar condições locais</li><li>Verificar pontos de alagamento</li>'}
                </ul>
            </div>
        </div>
    `;
}

function adicionarBairroNaLista(bairro, index) {
    const areasList = document.getElementById('areas-list');
    if (!areasList) return;

    const card = document.createElement('div');
    
    card.className = `area-card ${(bairro.nivel_risco || 'baixo').toLowerCase()} fade-in`;
    card.onclick = () => centralizarBairro(bairro);
    
    card.innerHTML = `
        <div class="area-header">
            <div class="area-name">${bairro.nome || 'Bairro sem nome'}</div>
            <div class="area-risk risk-${(bairro.nivel_risco || 'baixo').toLowerCase()}">
                ${bairro.nivel_risco || 'NÃO INFORMADO'}
            </div>
        </div>
        
        <div class="area-score" style="color: ${bairro.cor_risco}; font-weight: bold; font-size: 1.2em; text-align: center; margin: 5px 0;">
            ${bairro.probabilidade_alagamento || 0}% risco
        </div>
        
        <div class="area-details">
            <div class="detail-item">
                <span class="detail-icon">📍</span>
                <span class="detail-text">${bairro.regiao || 'Região não informada'}</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">📊</span>
                <span class="detail-text">Score: ${(bairro.risco_atual || 0).toFixed(3)}</span>
            </div>
            
            <div class="detail-item">
                <span class="detail-icon">📏</span>
                <span class="detail-text">${bairro.area_km2 || 0} km²</span>
            </div>
        </div>
        
        <div class="area-contexto">
            Clique para ver no mapa
        </div>
    `;
    
    areasList.appendChild(card);
}

function centralizarBairro(bairro) {
    if (bairro.centro) {
        map.setView(bairro.centro, 15);
        
        // Abrir popup se possível
        bairrosLayer.eachLayer(function(layer) {
            if (layer.getPopup && layer.getPopup()) {
                const popupContent = layer.getPopup().getContent();
                if (popupContent && popupContent.includes(bairro.nome)) {
                    layer.openPopup();
                }
            }
        });
    }
}

function atualizarAlertaGeral(alerta) {
    const alertaDiv = document.getElementById('alerta-geral');
    if (!alertaDiv) return;

    let classe = 'alert-banner ';
    let icone = '';
    let titulo = '';
    
    if (alerta.includes('ALTO') || alerta.includes('CRITICO') || alerta.includes('LARANJA') || alerta.includes('VERMELHO')) {
        classe += 'alert-alto';
        icone = '🚨 ';
        titulo = 'ALERTA GERAL - RISCO ALTO';
    } else if (alerta.includes('MODERADO') || alerta.includes('AMARELO')) {
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

function atualizarEstatisticas(estatisticas) {
    if (!estatisticas) return;
    
    // Atualizar elementos de estatística se existirem
    const elementos = {
        'total-bairros': estatisticas.total_bairros,
        'alto-risco': estatisticas.alto_risco,
        'moderado-risco': estatisticas.moderado_risco,
        'baixo-risco': estatisticas.baixo_risco
    };
    
    for (const [id, valor] of Object.entries(elementos)) {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = valor || 0;
        }
    }
}

function atualizarContextoAlerta(data) {
    let contextoDiv = document.getElementById('contexto-alerta');
    
    if (!contextoDiv) {
        // Criar div de contexto se não existir
        contextoDiv = document.createElement('div');
        contextoDiv.id = 'contexto-alerta';
        contextoDiv.className = 'contexto-info';
        
        const sidebar = document.getElementById('sidebar');
        const alertaGeral = document.getElementById('alerta-geral');
        if (sidebar && alertaGeral) {
            sidebar.insertBefore(contextoDiv, alertaGeral.nextSibling);
        }
    }
    
    contextoDiv.innerHTML = `
        <div class="contexto-content">
            <div class="fonte-info">
                <strong>📊 Fonte dos dados:</strong>
                <div>• Shapefile oficial do Recife</div>
                <div>• APAC - Dados em tempo real</div>
                <div>• Defesa Civil do Recife</div>
            </div>
            <div class="atualizacao-info">
                <strong>🕒 Última atualização:</strong>
                <div>${ultimaAtualizacao}</div>
            </div>
            ${data.estatisticas ? `
            <div class="stats-info">
                <strong>📈 Estatísticas:</strong>
                <div>• ${data.estatisticas.total_bairros} bairros monitorados</div>
                <div>• ${data.estatisticas.alto_risco} em alto risco</div>
                <div>• ${data.estatisticas.moderado_risco} em risco moderado</div>
            </div>
            ` : ''}
        </div>
    `;
}

function mostrarLoading(mostrar) {
    const loading = document.getElementById('loading');
    if (!loading) return;

    if (mostrar) {
        loading.style.display = 'block';
        loading.innerHTML = `
            <div class="loading-content">
                <div class="spinner"></div>
                <h3>Carregando dados de alagamento...</h3>
                <p>Analisando áreas de risco em Recife</p>
                <div class="loading-source">
                    Conectando com APAC e Defesa Civil...
                </div>
            </div>
        `;
    } else {
        loading.style.display = 'none';
    }
}

function mostrarErro(mensagem) {
    const loading = document.getElementById('loading');
    if (!loading) return;

    loading.style.display = 'block';
    loading.innerHTML = `
        <div class="error-content">
            <div class="error-icon">❌</div>
            <h3 style="color: #dc3545;">Erro de Conexão</h3>
            <p>${mensagem}</p>
            <div class="error-context">
                Verifique se o servidor está rodando em http://localhost:8000
            </div>
            <button onclick="carregarDados()" class="retry-btn">
                🔄 Tentar Novamente
            </button>
        </div>
    `;
}

// ============================================================================
// FUNÇÕES DO FILTRO
// ============================================================================

function abrirFiltros() {
    console.log('🔍 Abrindo modal de filtros...');
    document.getElementById('filterModal').style.display = 'flex';
}

function fecharFiltros() {
    console.log('❌ Fechando modal de filtros...');
    document.getElementById('filterModal').style.display = 'none';
}

function aplicarFiltros() {
    console.log('🔍 Aplicando filtros...', { rpaSelecionada, riscoSelecionado });
    
    // Limpar layers anteriores
    bairrosLayer.clearLayers();
    
    // Limpar lista de áreas
    const areasList = document.getElementById('areas-list');
    if (areasList) areasList.innerHTML = '';
    
    // Filtrar bairros baseado nas variáveis do Python
    const bairrosFiltrados = todosBairros.filter(bairro => {
        // Extrair número da RPA do campo "regiao" (formato: "RPA X")
        let rpaBairro = null;
        if (bairro.regiao && bairro.regiao.includes('RPA')) {
            const match = bairro.regiao.match(/RPA\s*(\d+)/);
            rpaBairro = match ? match[1] : null;
        }
        
        // Filtro por RPA
        const filtroRPA = rpaSelecionada === 'todas' || 
                         (rpaBairro && rpaBairro === rpaSelecionada);
        
        // Normalizar níveis de risco para compatibilidade
        const nivelRiscoBairro = bairro.nivel_risco ? bairro.nivel_risco.toLowerCase() : '';
        let riscoFiltroNormalizado = riscoSelecionado;
        
        // Converter "medio" do filtro para "moderado" do Python
        if (riscoSelecionado === 'medio') {
            riscoFiltroNormalizado = 'moderado';
        }
        
        // Filtro por nível de risco (usando campo "nivel_risco")
        const filtroRisco = riscoSelecionado === 'todos' || 
                           nivelRiscoBairro === riscoFiltroNormalizado;
        
        return filtroRPA && filtroRisco;
    });
    
    console.log(`📍 Mostrando ${bairrosFiltrados.length} bairros filtrados`);
    
    // Adicionar bairros filtrados ao mapa e à lista
    bairrosFiltrados.forEach((bairro, index) => {
        if (bairro && bairro.nome) {
            adicionarBairroNoMapa(bairro);
            adicionarBairroNaLista(bairro, index);
        }
    });
    
    fecharFiltros();
}

// Configurar eventos dos botões de filtro
function configurarEventosFiltro() {
    // Eventos para botões RPA
    document.querySelectorAll('.rpa-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.rpa-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            rpaSelecionada = this.getAttribute('data-rpa');
            console.log(`📍 RPA selecionada: ${rpaSelecionada}`);
        });
    });
    
    // Eventos para botões de risco
    document.querySelectorAll('.risk-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.risk-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            riscoSelecionado = this.getAttribute('data-risk');
            console.log(`⚠️ Risco selecionado: ${riscoSelecionado}`);
        });
    });
    
    // Fechar modal ao clicar fora
    document.getElementById('filterModal').addEventListener('click', function(e) {
        if (e.target === this) {
            fecharFiltros();
        }
    });
    
    // Fechar modal com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            fecharFiltros();
        }
    });
}

// Adicionar CSS dinâmico para marcadores
const estiloMarcadores = `
<style>
.bairro-marker {
    background: #FF4444;
    border-radius: 50%;
    border: 3px solid white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    text-align: center;
    width: 50px;
    height: 50px;
    cursor: pointer;
}

.bairro-probabilidade {
    font-size: 12px;
    line-height: 1;
}

.bairro-nome {
    font-size: 8px;
    line-height: 1;
    margin-top: 2px;
}

.risk-marker {
    background: transparent !important;
    border: none !important;
}
</style>
`;

// Adicionar CSS ao documento
document.head.insertAdjacentHTML('beforeend', estiloMarcadores);

// Inicialização quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando sistema de monitoramento...');
    
    // Inicializar mapa
    inicializarMapa();
    
    // Configurar eventos do filtro
    configurarEventosFiltro();
    
    // Carregar dados após um pequeno delay para garantir que o mapa está pronto
    setTimeout(() => {
        carregarDados();
    }, 500);
    
    // Atualizar a cada 5 minutos (automático - removido botão)
    setInterval(carregarDados, 300000);
});

// Exportar funções para uso global
window.carregarDados = carregarDados;
window.centralizarBairro = centralizarBairro;
window.abrirFiltros = abrirFiltros;
window.fecharFiltros = fecharFiltros;
window.aplicarFiltros = aplicarFiltros;