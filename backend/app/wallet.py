from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CoinTransaction, User


class InsufficientCoinsError(ValueError):
    pass


def next_coin_balance(current_coins: int, amount: int) -> int:
    """Return the new balance without ever allowing it to become negative."""
    balance = current_coins + amount
    if balance < 0:
        raise InsufficientCoinsError("Insufficient coins")
    return balance


async def apply_coin_change(
    session: AsyncSession,
    *,
    user_id: int,
    amount: int,
    source: str,
    reason: str,
    actor_id: int | None = None,
    external_reference: str | None = None,
) -> tuple[User | None, CoinTransaction | None]:
    """Apply one balance change under a user row lock.

    A future cashier must pass its stable payment/event id as
    ``external_reference`` so the database can reject a duplicate credit.
    """
    if amount == 0:
        raise ValueError("Coin change cannot be zero")

    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        return None, None

    if external_reference:
        existing = await session.scalar(
            select(CoinTransaction).where(
                CoinTransaction.source == source,
                CoinTransaction.external_reference == external_reference,
            )
        )
        if existing is not None:
            return user, existing

    balance_after = next_coin_balance(user.coins, amount)
    user.coins = balance_after
    transaction = CoinTransaction(
        user_id=user.id,
        actor_id=actor_id,
        amount=amount,
        balance_after=balance_after,
        source=source,
        reason=reason,
        external_reference=external_reference,
    )
    session.add(transaction)
    await session.flush()
    return user, transaction


async def record_paid_top_up(
    session: AsyncSession,
    *,
    user_id: int,
    coins: int,
    provider: str,
    payment_id: str,
) -> tuple[User | None, CoinTransaction | None]:
    """Cashier hook: call only after the provider's webhook is verified."""
    if coins <= 0:
        raise ValueError("Top-up coins must be positive")
    provider = provider.strip().lower()
    payment_id = payment_id.strip()
    if not provider or not payment_id:
        raise ValueError("Provider and payment id are required")
    if len(provider) > 30 or len(payment_id) > 255:
        raise ValueError("Provider or payment id is too long")
    return await apply_coin_change(
        session,
        user_id=user_id,
        amount=coins,
        source=f"cashier:{provider}",
        reason="Paid top-up",
        external_reference=payment_id,
    )
