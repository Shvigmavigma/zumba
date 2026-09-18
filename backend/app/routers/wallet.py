from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin, require_pilot_plus
from app.models import CoinTransaction, User
from app.rate_limit import limiter
from app.schemas import CoinAdjustment, CoinTransactionRead, WalletBalanceRead
from app.wallet import InsufficientCoinsError, apply_coin_change


router = APIRouter()


@router.get("/me", response_model=WalletBalanceRead)
async def my_wallet(user: User = Depends(require_pilot_plus)):
    return WalletBalanceRead(coins=user.coins)


@router.get("/me/transactions", response_model=list[CoinTransactionRead])
async def my_wallet_transactions(
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    transactions = await session.scalars(
        select(CoinTransaction)
        .where(CoinTransaction.user_id == user.id)
        .order_by(CoinTransaction.created_at.desc(), CoinTransaction.id.desc())
        .limit(100)
    )
    return list(transactions)


async def change_user_coins(
    user_id: int,
    payload: CoinAdjustment,
    admin: User,
    session: AsyncSession,
    *,
    amount: int,
    source: str,
) -> CoinTransaction:
    try:
        _, transaction = await apply_coin_change(
            session,
            user_id=user_id,
            amount=amount,
            source=source,
            reason=payload.reason,
            actor_id=admin.id,
        )
    except InsufficientCoinsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient coins") from exc
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await session.commit()
    await session.refresh(transaction)
    return transaction


@router.post("/admin/users/{user_id}/credit", response_model=CoinTransactionRead)
@limiter.limit("10/minute")
async def credit_user_coins(
    user_id: int,
    request: Request,
    payload: CoinAdjustment,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await change_user_coins(user_id, payload, admin, session, amount=payload.coins, source="admin_credit")


@router.post("/admin/users/{user_id}/debit", response_model=CoinTransactionRead)
@limiter.limit("10/minute")
async def debit_user_coins(
    user_id: int,
    request: Request,
    payload: CoinAdjustment,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await change_user_coins(user_id, payload, admin, session, amount=-payload.coins, source="admin_debit")
