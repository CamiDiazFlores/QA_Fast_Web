# app/routes/cases.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.config import get_db
from app.models.case_model import TestCase
from app.schemas.case_schema import TestCaseCreate, TestCaseResponse
from app.utils.file_loader import load_excel_cases


router = APIRouter()

@router.post("/upload", response_model=List[TestCaseResponse])
async def upload_cases(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Sube un archivo Excel con casos de prueba y los guarda en BD.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")
    
    try:
        cases_data = load_excel_cases(file.file)
        
        case_objects = []
        for case_dict in cases_data:
            test_case = TestCase(**case_dict)
            db.add(test_case)
            case_objects.append(test_case)
        
        db.commit()
        
        for case in case_objects:
            db.refresh(case)
        
        return case_objects
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.get("/", response_model=List[TestCaseResponse])
async def get_all_cases(db: Session = Depends(get_db)):
    """
    Obtiene todos los casos de prueba de la base de datos.
    """
    cases = db.query(TestCase).all()
    return cases

@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_case_by_id(case_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un caso de prueba específico por su ID.
    """
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso de prueba no encontrado")
    return case

@router.delete("/{case_id}")
async def delete_case(case_id: int, db: Session = Depends(get_db)):
    """
    Elimina un caso de prueba por su ID.
    """
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso de prueba no encontrado")
    
    db.delete(case)
    db.commit()
    return {"message": "Caso de prueba eliminado exitosamente"}
