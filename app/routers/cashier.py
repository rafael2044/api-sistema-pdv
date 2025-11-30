from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app import models, schemas
from datetime import datetime, date
from typing import List
from app.dependencies import allow_manager, allow_admin_only, get_current_user

router = APIRouter(prefix="/cashier", tags=["Cashier"])

# Adicione isso dentro de backend/app/routers/cashier.py

@router.get("/status")
async def get_cashier_status(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    x_terminal_id: str = Header(..., alias="x-terminal-id") # Lê o Header obrigatório
):
    # Lógica Nova: Busca sessão aberta NESTE TERMINAL (independente de quem abriu)
    query = select(models.CashierSession).where(
        models.CashierSession.terminal_id == x_terminal_id,
        models.CashierSession.status == "open"
    )
    result = await db.execute(query)
    session = result.scalars().first()
    
    if not session:
        return {"status": "closed", "terminal_id": x_terminal_id}

    # Calcula totais (igual anterior)
    sales_query = select(func.sum(models.Sale.total_amount)).where(
        models.Sale.session_id == session.id,
        models.Sale.status == models.SaleStatus.COMPLETED
    )
    sales_result = await db.execute(sales_query)
    total_sold = sales_result.scalar() or 0.0

    return {
        "status": "open",
        "session_id": session.id,
        "terminal_id": session.terminal_id, # Retorna qual terminal é
        "opened_by_user_id": session.user_id, # Quem abriu
        "initial_balance": session.initial_balance,
        "total_sold": total_sold,
        "expected_balance": session.initial_balance + total_sold
    }

@router.get("/history", response_model=List[schemas.CashierSessionResponse],
    dependencies=[Depends(allow_manager), Depends(allow_admin_only)])
async def get_sessions_by_date(
    day: date,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    start_of_day = datetime.combine(day, datetime.min.time())
    end_of_day = datetime.combine(day, datetime.max.time())

    query = select(models.CashierSession).where(
        models.CashierSession.start_time >= start_of_day,
        models.CashierSession.start_time <= end_of_day
    ).order_by(models.CashierSession.start_time.desc())

    result = await db.execute(query)
    return result.scalars().all()

@router.post("/open")
async def open_cashier(
    session_in: schemas.CashierOpen,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    x_terminal_id: str = Header(..., alias="x-terminal-id")
):
    # Verifica se JÁ EXISTE caixa aberto neste terminal
    query = select(models.CashierSession).where(
        models.CashierSession.terminal_id == x_terminal_id,
        models.CashierSession.status == "open"
    )
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail=f"O terminal {x_terminal_id} já possui um caixa aberto.")

    new_session = models.CashierSession(
        user_id=current_user.id, # Quem abriu fisicamente
        terminal_id=x_terminal_id, # <--- Grava o ID da máquina
        initial_balance=session_in.initial_balance,
        status="open"
    )
    db.add(new_session)
    await db.commit()
    return {"message": "Caixa aberto com sucesso", "terminal": x_terminal_id}

@router.post("/close")
async def close_cashier(
    close_data: schemas.CashierClose,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    x_terminal_id: str = Header(..., alias="x-terminal-id")
):
    # Busca sessão aberta NESTE TERMINAL
    query = select(models.CashierSession).where(
        models.CashierSession.terminal_id == x_terminal_id,
        models.CashierSession.status == "open"
    )
    result = await db.execute(query)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=400, detail="Não há caixa aberto neste terminal para fechar.")

    session.final_balance = close_data.final_balance
    session.end_time = datetime.now()
    session.status = "closed"
    
    await db.commit()
    return {"message": "Caixa fechado com sucesso"}