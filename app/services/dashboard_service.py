# app/services/dashboard_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.case_model import TestCase
from app.models.result_model import TestResult
from app.models.prompt_model import Prompt
from datetime import datetime, timedelta
from typing import Dict, List, Any

class DashboardService:
    """
    Servicio para generar métricas y estadísticas del dashboard.
    """
    def __init__(self, db: Session):
        self.db = db
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas generales de ejecución.
        """
        # Total de casos de prueba
        total_cases = self.db.query(TestCase).count()
        
        # Total de ejecuciones
        total_executions = self.db.query(TestResult).count()
        
        # Ejecuciones por estado
        passed = self.db.query(TestResult).filter(TestResult.status == "passed").count()
        failed = self.db.query(TestResult).filter(TestResult.status == "failed").count()
        error = self.db.query(TestResult).filter(TestResult.status == "error").count()
        
        # Tasa de éxito
        success_rate = round((passed / total_executions * 100), 2) if total_executions > 0 else 0
        
        # Prompts generados
        total_prompts = self.db.query(Prompt).count()
        
        # Ejecuciones últimas 24 horas
        yesterday = datetime.now() - timedelta(days=1)
        executions_24h = self.db.query(TestResult).filter(
            TestResult.created_at >= yesterday
        ).count()
        
        # Test más ejecutado - ✅ CORREGIDO: usar 'name' en lugar de 'test_name'
        most_executed = self.db.query(
            TestCase.name,
            func.count(TestResult.id).label("count")
        ).join(TestResult, TestCase.id == TestResult.test_case_id)\
         .group_by(TestCase.id, TestCase.name)\
         .order_by(desc("count"))\
         .first()
        
        return {
            "summary": {
                "total_cases": total_cases,
                "total_executions": total_executions,
                "total_prompts": total_prompts,
                "executions_24h": executions_24h
            },
            "status_breakdown": {
                "passed": passed,
                "failed": failed,
                "error": error,
                "success_rate": success_rate
            },
            "most_executed_test": {
                "name": most_executed[0] if most_executed else "N/A",
                "count": most_executed[1] if most_executed else 0
            }
        }
    
    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lista las últimas ejecuciones con detalles completos.
        """
        executions = self.db.query(TestResult).join(
            TestCase, TestResult.test_case_id == TestCase.id
        ).order_by(desc(TestResult.created_at)).limit(limit).all()
        
        results = []
        for execution in executions:
            test_case = self.db.query(TestCase).filter(TestCase.id == execution.test_case_id).first()
            
            results.append({
                "id": execution.id,
                "test_name": test_case.name if test_case else "Unknown",  # ✅ CORREGIDO
                "status": execution.status,
                "execution_time": execution.execution_time,
                "created_at": execution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "screenshot": execution.screenshot_path,
                "logs_preview": execution.logs[:200] + "..." if execution.logs and len(execution.logs) > 200 else execution.logs
            })
        
        return results
    
    def get_execution_timeline(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Datos para gráfico de línea temporal (últimos N días).
        """
        start_date = datetime.now() - timedelta(days=days)
        
        timeline_data = self.db.query(
            func.date(TestResult.created_at).label("date"),
            TestResult.status,
            func.count(TestResult.id).label("count")
        ).filter(
            TestResult.created_at >= start_date
        ).group_by(
            func.date(TestResult.created_at),
            TestResult.status
        ).order_by("date").all()
        
        formatted_data = {}
        for record in timeline_data:
            date_str = record.date.strftime("%Y-%m-%d")
            if date_str not in formatted_data:
                formatted_data[date_str] = {"date": date_str, "passed": 0, "failed": 0, "error": 0}
            
            formatted_data[date_str][record.status] = record.count
        
        return list(formatted_data.values())
    
    def get_test_case_stats(self) -> List[Dict[str, Any]]:
        """
        Estadísticas por caso de prueba.
        """
        stats = self.db.query(
            TestCase.name,  # ✅ CORREGIDO
            func.count(TestResult.id).label("total_executions"),
            func.sum(func.case((TestResult.status == "passed", 1), else_=0)).label("passed"),
            func.sum(func.case((TestResult.status == "failed", 1), else_=0)).label("failed"),
            func.sum(func.case((TestResult.status == "error", 1), else_=0)).label("error")
        ).join(
            TestResult, TestCase.id == TestResult.test_case_id
        ).group_by(TestCase.id, TestCase.name).all()
        
        results = []
        for stat in stats:
            results.append({
                "test_name": stat.name,
                "total_executions": stat.total_executions,
                "passed": stat.passed,
                "failed": stat.failed,
                "error": stat.error,
                "success_rate": round((stat.passed / stat.total_executions * 100), 2) if stat.total_executions > 0 else 0
            })
        
        return results
    
    def get_execution_details(self, execution_id: int) -> Dict[str, Any]:
        """
        Detalles completos de una ejecución específica.
        """
        execution = self.db.query(TestResult).filter(TestResult.id == execution_id).first()
        
        if not execution:
            return {"error": "Ejecución no encontrada"}
        
        test_case = self.db.query(TestCase).filter(TestCase.id == execution.test_case_id).first()
        prompt = self.db.query(Prompt).filter(Prompt.test_case_id == execution.test_case_id).order_by(desc(Prompt.created_at)).first()
        
        return {
            "execution": {
                "id": execution.id,
                "status": execution.status,
                "execution_time": execution.execution_time,
                "created_at": execution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "executed_by_agent": execution.executed_by_agent,
                "logs": execution.logs,
                "screenshot_path": execution.screenshot_path
            },
            "test_case": {
                "id": test_case.id,
                "name": test_case.test_name,
                "url": test_case.url,
                "expected_result": test_case.expected_result,
                "test_type": test_case.test_type
            } if test_case else None,
            "prompt": {
                "id": prompt.id,
                "prompt_text": prompt.prompt_text[:500] + "...",
                "generated_code": prompt.generated_code[:500] + "..." if prompt.generated_code else None,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } if prompt else None
        }
    
    def get_prompts_history(self, test_case_id: int = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Historial de prompts generados.
        """
        query = self.db.query(Prompt)
        
        if test_case_id:
            query = query.filter(Prompt.test_case_id == test_case_id)
        
        prompts = query.order_by(desc(Prompt.created_at)).limit(limit).all()
        
        results = []
        for prompt in prompts:
            test_case = self.db.query(TestCase).filter(TestCase.id == prompt.test_case_id).first()
            
            results.append({
                "id": prompt.id,
                "test_case_name": test_case.test_name if test_case else "Unknown",
                "prompt_length": len(prompt.prompt_text),
                "has_code": bool(prompt.generated_code),
                "code_length": len(prompt.generated_code) if prompt.generated_code else 0,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return results
