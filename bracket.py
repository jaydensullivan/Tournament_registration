import random
import database as db


async def generate_bracket(teams: list[dict]):
    """Creates a single-elimination bracket from a list of team dicts ({id, name}).
    Handles non-power-of-two team counts with byes (auto-advance in round 1).
    Returns the list of round-1 match ids that are ready to be posted (both slots filled,
    i.e. not an auto-resolved bye)."""
    await db.clear_bracket()

    teams = teams[:]
    random.shuffle(teams)

    size = 1
    while size < len(teams):
        size *= 2

    # Distribute byes one-per-match instead of piling them at the end of the
    # slot list. If byes were simply appended after the shuffled teams, any
    # time 2+ byes were needed, two of them could land in the same round-1
    # match, producing a match with BOTH slots empty. That match can never
    # produce a winner, so the bracket slot depending on it would stay
    # unfilled forever and the tournament would stall. Since `size` is the
    # smallest power of two >= len(teams), the number of byes is always
    # strictly less than the number of round-1 matches (size // 2), so a
    # one-bye-per-match distribution is always possible.
    num_matches = size // 2
    byes = size - len(teams)
    slots = [None] * size
    team_iter = iter(teams)
    for i in range(num_matches):
        slots[2 * i] = next(team_iter)
        if i >= byes:
            slots[2 * i + 1] = next(team_iter)

    total_rounds = size.bit_length() - 1  # size=1 -> 0 rounds (only 1 team, edge case)
    if total_rounds == 0:
        return []

    # Build round matches bottom-up so we can link next_match_id
    # First create placeholder rows for all rounds, then fill round 1 teams, then wire links.
    rows_by_round = {r: [] for r in range(1, total_rounds + 1)}
    for r in range(1, total_rounds + 1):
        count = size // (2 ** r)
        for pos in range(count):
            rows_by_round[r].append({
                "round": r, "position": pos,
                "team1_id": None, "team2_id": None,
                "winner_id": None, "next_match_id": None, "next_slot": None
            })

    # Fill round 1 team slots
    for i, row in enumerate(rows_by_round[1]):
        t1 = slots[2 * i]
        t2 = slots[2 * i + 1]
        row["team1_id"] = t1["id"] if t1 else None
        row["team2_id"] = t2["id"] if t2 else None

    # Insert rows round by round, keeping track of DB ids so we can wire next_match_id
    ids_by_round = {}
    for r in range(1, total_rounds + 1):
        ids_by_round[r] = await db.insert_matches(rows_by_round[r])

    # Wire next_match_id / next_slot (round r position p -> round r+1 position p//2, slot p%2)
    for r in range(1, total_rounds):
        for pos, match_id in enumerate(ids_by_round[r]):
            next_id = ids_by_round[r + 1][pos // 2]
            await db.update_match(match_id, next_match_id=next_id, next_slot=pos % 2)

    # Resolve byes in round 1 (team present but opponent missing -> auto win).
    # NOTE: when 2+ byes are adjacent (positions 2k and 2k+1), both of their
    # winners feed into the SAME round-2 match. advance_winner() tells us when
    # that match becomes fully populated (both slots filled) via its return
    # value - we must capture and surface that, otherwise that match would
    # silently sit fully-populated-but-never-announced, since it isn't itself
    # a round-1 match and the loop below only inspects round 1.
    ready_matches = []
    for match_id in ids_by_round[1]:
        m = await db.get_match(match_id)
        if m["team1_id"] and not m["team2_id"]:
            propagated = await advance_winner(match_id, m["team1_id"])
            if propagated:
                ready_matches.append(propagated)
        elif m["team2_id"] and not m["team1_id"]:
            propagated = await advance_winner(match_id, m["team2_id"])
            if propagated:
                ready_matches.append(propagated)
        elif m["team1_id"] and m["team2_id"]:
            ready_matches.append(match_id)
        # if both empty, nothing to do (shouldn't normally happen)

    return ready_matches


async def advance_winner(match_id: int, winner_team_id: int):
    """Marks a match's winner and pushes it into the next match's slot.
    Returns the next_match_id if that match became fully ready (both slots filled), else None."""
    await db.update_match(match_id, winner_id=winner_team_id)
    m = await db.get_match(match_id)
    if not m["next_match_id"]:
        return None  # this was the final

    field = "team1_id" if m["next_slot"] == 0 else "team2_id"
    await db.update_match(m["next_match_id"], **{field: winner_team_id})

    next_m = await db.get_match(m["next_match_id"])
    if next_m["team1_id"] and next_m["team2_id"]:
        return m["next_match_id"]
    return None


async def render_bracket_text(team_names_by_id: dict) -> str:
    matches = await db.all_matches()
    if not matches:
        return "Ð¡ÐµÑÐºÐ° ÐµÑÑ Ð½Ðµ ÑÐ³ÐµÐ½ÐµÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð°. ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ÑÐµ /generate_bracket"

    rounds = {}
    for m in matches:
        rounds.setdefault(m["round"], []).append(m)

    lines = []
    round_names = {}
    max_round = max(rounds.keys())
    for r in rounds:
        remaining = max_round - r
        if remaining == 0:
            round_names[r] = "Ð¤Ð¸Ð½Ð°Ð»"
        elif remaining == 1:
            round_names[r] = "ÐÐ¾Ð»ÑÑÐ¸Ð½Ð°Ð»"
        elif remaining == 2:
            round_names[r] = "Ð§ÐµÑÐ²ÐµÑÑÑÑÐ¸Ð½Ð°Ð»"
        else:
            round_names[r] = f"Ð Ð°ÑÐ½Ð´ {r}"

    for r in sorted(rounds.keys()):
        lines.append(f"\n<b>{round_names[r]}</b>")
        for m in rounds[r]:
            t1 = team_names_by_id.get(m["team1_id"], "TBD") if m["team1_id"] else "TBD"
            t2 = team_names_by_id.get(m["team2_id"], "TBD") if m["team2_id"] else "TBD"
            if m["winner_id"]:
                winner_name = team_names_by_id.get(m["winner_id"], "?")
                lines.append(f"  {t1} vs {t2} â ð {winner_name}")
            else:
                lines.append(f"  {t1} vs {t2}")
    return "\n".join(lines)
