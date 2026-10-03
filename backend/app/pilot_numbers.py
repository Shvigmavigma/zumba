from collections.abc import Iterable, Mapping


PILOT_NUMBER_MIN = 0
PILOT_NUMBER_MAX = 999


def allocate_profile_numbers(user_ids: Iterable[int], users_by_id: Mapping[int, object]) -> dict[int, int]:
    assignments: dict[int, int] = {}
    used: set[int] = set()
    for user_id in user_ids:
        if user_id in assignments:
            continue
        user = users_by_id[user_id]
        try:
            preferred = int(getattr(user, "pilot_number", PILOT_NUMBER_MIN) or PILOT_NUMBER_MIN)
        except (TypeError, ValueError):
            preferred = PILOT_NUMBER_MIN
        preferred = max(PILOT_NUMBER_MIN, min(PILOT_NUMBER_MAX, preferred))
        candidates = [preferred]
        for distance in range(1, PILOT_NUMBER_MAX):
            candidates.extend((preferred + distance, preferred - distance))
        number = next((candidate for candidate in candidates if PILOT_NUMBER_MIN <= candidate <= PILOT_NUMBER_MAX and candidate not in used), None)
        if number is None:
            raise ValueError("No pilot numbers are available")
        assignments[user_id] = number
        used.add(number)
    return assignments


async def apply_pilot_number_assignments(session, registrations: Iterable[object], assignments: Mapping[int, int]) -> int:
    registrations = list(registrations)
    changed = [registration for registration in registrations if registration.pilot_number != assignments[registration.user_id]]
    if not changed:
        return 0
    current_numbers = {registration.pilot_number for registration in registrations}
    temporary_numbers = [number for number in range(0, PILOT_NUMBER_MAX + 1) if number not in current_numbers]
    if len(temporary_numbers) < len(changed):
        raise ValueError("No temporary pilot numbers are available")
    for registration, number in zip(changed, temporary_numbers):
        registration.pilot_number = number
    await session.flush()
    for registration in changed:
        registration.pilot_number = assignments[registration.user_id]
    return len(changed)
