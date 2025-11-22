from sqlalchemy.orm import Session
from app.models.result_model import Result

def calculate_metrics(db: Session):
    """Calcula métricas globales de las ejecuciones."""
    total = db.query(Result).count()
    passed = db.query(Result).filter(Result.success == True).count()
    failed = total - passed

    success_rate = round((passed / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "success_rate": f"{success_rate}%"
    }

def get_recent_executions(db: Session, limit: int = 10):
    """Obtiene las últimas ejecuciones registradas."""
    return db.query(Result).order_by(Result.created_at.desc()).limit(limit).all()
