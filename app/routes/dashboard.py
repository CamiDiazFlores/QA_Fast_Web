from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.services.dashboard_service import DashboardService
from app.config import get_db
from typing import Optional

# ✅ QUITAR el prefix aquí porque ya se agrega en main.py
router = APIRouter(tags=["Dashboard"])

@router.get("/", response_class=HTMLResponse)
async def dashboard_html(request: Request):
    """
    🖥️ Dashboard HTML interactivo con gráficos en tiempo real.
    """
    html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Fast Web - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        
        h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 1.1em;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .metric-value {
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .metric-label {
            color: #666;
            font-size: 1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-card.success .metric-value { color: #10b981; }
        .metric-card.warning .metric-value { color: #f59e0b; }
        .metric-card.danger .metric-value { color: #ef4444; }
        .metric-card.info .metric-value { color: #3b82f6; }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .chart-card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .executions-table {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        
        th {
            background: #f3f4f6;
            color: #667eea;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }
        
        tr:hover {
            background: #f9fafb;
        }
        
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            display: inline-block;
        }
        
        .status-passed { background: #d1fae5; color: #065f46; }
        .status-failed { background: #fee2e2; color: #991b1b; }
        .status-error { background: #fef3c7; color: #92400e; }
        
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            transition: all 0.3s;
        }
        
        .refresh-btn:hover {
            background: #764ba2;
            transform: scale(1.05);
        }
        
        .auto-refresh {
            color: white;
            text-align: center;
            margin-top: 20px;
            font-size: 0.9em;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1.5s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 QA Fast Web Dashboard</h1>
            <p class="subtitle">Sistema de Automatización con Manus IA + Selenium</p>
        </header>

        <!-- Métricas Principales -->
        <div class="metrics-grid" id="metrics"></div>

        <!-- Gráficos -->
        <div class="charts-grid">
            <div class="chart-card">
                <h2>📊 Distribución de Estados</h2>
                <canvas id="statusChart"></canvas>
            </div>
            <div class="chart-card">
                <h2>📈 Tendencia de Ejecuciones (7 días)</h2>
                <canvas id="timelineChart"></canvas>
            </div>
        </div>

        <!-- Tabla de Ejecuciones Recientes -->
        <div class="executions-table">
            <h2 style="color: #667eea; margin-bottom: 20px;">📋 Últimas Ejecuciones</h2>
            <table id="executionsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Test</th>
                        <th>Estado</th>
                        <th>Tiempo</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <button class="refresh-btn" onclick="loadDashboard()">🔄 Actualizar</button>
        <div class="auto-refresh">Actualización automática cada 30 segundos</div>
    </div>

    <script>
        let statusChart, timelineChart;
        
        async function loadDashboard() {
            try {
                // Cargar métricas
                const metricsRes = await fetch('/api/dashboard/metrics');
                const metrics = await metricsRes.json();
                renderMetrics(metrics);
                
                // Cargar gráfico de estados
                renderStatusChart(metrics.status_breakdown);
                
                // Cargar timeline
                const timelineRes = await fetch('/api/dashboard/timeline?days=7');
                const timeline = await timelineRes.json();
                renderTimelineChart(timeline);
                
                // Cargar tabla de ejecuciones
                const executionsRes = await fetch('/api/dashboard/recent?limit=10');
                const executions = await executionsRes.json();
                renderExecutionsTable(executions);
                
            } catch (error) {
                console.error('Error cargando dashboard:', error);
            }
        }
        
        function renderMetrics(metrics) {
            const metricsHtml = `
                <div class="metric-card info">
                    <div class="metric-label">Total Tests</div>
                    <div class="metric-value">${metrics.summary.total_cases}</div>
                </div>
                <div class="metric-card success">
                    <div class="metric-label">Ejecuciones</div>
                    <div class="metric-value">${metrics.summary.total_executions}</div>
                </div>
                <div class="metric-card warning">
                    <div class="metric-label">Tasa de Éxito</div>
                    <div class="metric-value">${metrics.status_breakdown.success_rate}%</div>
                </div>
                <div class="metric-card danger">
                    <div class="metric-label">Últimas 24h</div>
                    <div class="metric-value">${metrics.summary.executions_24h}</div>
                </div>
            `;
            document.getElementById('metrics').innerHTML = metricsHtml;
        }
        
        function renderStatusChart(breakdown) {
            const ctx = document.getElementById('statusChart').getContext('2d');
            
            if (statusChart) statusChart.destroy();
            
            statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Passed', 'Failed', 'Error'],
                    datasets: [{
                        data: [breakdown.passed, breakdown.failed, breakdown.error],
                        backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
        
        function renderTimelineChart(timeline) {
            const ctx = document.getElementById('timelineChart').getContext('2d');
            
            if (timelineChart) timelineChart.destroy();
            
            timelineChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: timeline.map(d => d.date),
                    datasets: [
                        {
                            label: 'Passed',
                            data: timeline.map(d => d.passed),
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Failed',
                            data: timeline.map(d => d.failed),
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
        
        function renderExecutionsTable(executions) {
            const tbody = document.querySelector('#executionsTable tbody');
            tbody.innerHTML = executions.map(ex => `
                <tr>
                    <td>#${ex.id}</td>
                    <td>${ex.test_name}</td>
                    <td><span class="status-badge status-${ex.status}">${ex.status.toUpperCase()}</span></td>
                    <td>${ex.execution_time}</td>
                    <td>${ex.created_at}</td>
                </tr>
            `).join('');
        }
        
        // Cargar al inicio
        loadDashboard();
        
        // Auto-refresh cada 30 segundos
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# Mantener los endpoints JSON para el dashboard HTML
@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    dashboard = DashboardService(db)
    return dashboard.get_metrics()

@router.get("/recent")
async def get_recent_executions(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    dashboard = DashboardService(db)
    return dashboard.get_recent_executions(limit=limit)

@router.get("/timeline")
async def get_execution_timeline(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    dashboard = DashboardService(db)
    return dashboard.get_execution_timeline(days=days)

@router.get("/test-stats")
async def get_test_case_stats(db: Session = Depends(get_db)):
    dashboard = DashboardService(db)
    return dashboard.get_test_case_stats()

@router.get("/execution/{execution_id}")
async def get_execution_details(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """
    🔍 Detalles completos de una ejecución específica.
    
    Incluye:
    - Datos de la ejecución
    - Caso de prueba asociado
    - Prompt y código generado
    - Logs completos
    """
    dashboard = DashboardService(db)
    return dashboard.get_execution_details(execution_id)

@router.get("/prompts")
async def get_prompts_history(
    test_case_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    📝 Historial de prompts generados.
    
    Opcionalmente filtrar por test_case_id.
    """
    dashboard = DashboardService(db)
    return dashboard.get_prompts_history(test_case_id=test_case_id, limit=limit)
