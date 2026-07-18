from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import MODER_PLUS, require_moder_plus
from app.models import Race, Setup, User
from app.rate_limit import limiter
from app.schemas import SetupCreate, SetupRead


router = APIRouter()


@router.get("", response_model=list[SetupRead])
@limiter.limit("3/minute")
async def list_setups(
    request: Request,
    race_id: int | None = None,
    car_model: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Setup).order_by(Setup.created_at.desc())
    if race_id is not None:
        stmt = stmt.where(Setup.race_id == race_id)
    if car_model is not None:
        stmt = stmt.where(Setup.car_model == car_model)
    return (await session.scalars(stmt.limit(100))).all()


@router.post("", response_model=SetupRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_setup(payload: SetupCreate, request: Request, user: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    if payload.race_id is not None and await session.get(Race, payload.race_id) is None:
        raise HTTPException(status_code=404, detail="Race not found")
    setup = Setup(**payload.model_dump(), user_id=user.id)
    session.add(setup)
    await session.commit()
    await session.refresh(setup)
    return setup


@router.delete("/{setup_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def delete_setup(setup_id: int, request: Request, user: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    setup = await session.get(Setup, setup_id)
    if setup is None:
        raise HTTPException(status_code=404, detail="Setup not found")
    if setup.user_id != user.id and user.role not in MODER_PLUS:
        raise HTTPException(status_code=403, detail="Only owner or moder+ can delete setup")
    await session.delete(setup)
    await session.commit()
