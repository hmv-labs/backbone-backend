import hashlib
import re
import time

# these should match with what frontend is having
HONEYPOT_ALPHABET = "abdefhikmnqrstuvwxyz234789"
HONEYPOT_REGEX = re.compile(rf"^hp_[{re.escape(HONEYPOT_ALPHABET)}]+$")
MIN_HONEYPOTS = 2
MIN_SUBMIT_MS = 1000 * 3  # 3 seconds
MAX_SUBMIT_MS = 1000 * 60 * 10  # 10 minutes


def is_honeypot_valid(data: dict[str, str], min_submit_ms=None) -> bool:
    data = data.copy()

    min_submit_ms = min_submit_ms or MIN_SUBMIT_MS

    # expects unix ts as string
    ts = data.pop("hp_ts", None)
    if not ts:
        return False

    # expects sha256 of "field1:field2:ts"
    sha = data.pop("hp_sha", None)
    if not sha:
        return False

    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False

    now_ms = int(time.time() * 1000)

    elapsed_ms = now_ms - ts_int

    # too fast or too old
    if elapsed_ms < min_submit_ms or elapsed_ms > MAX_SUBMIT_MS:
        return False

    honeypot_keys: list[str] = []

    # validate honeypot fields
    for k, v in data.items():
        if not k.startswith("hp_"):
            continue

        honeypot_keys.append(k)

        # ensure key charset is valid
        if not HONEYPOT_REGEX.match(k):
            return False

        # honeypot fields must stay empty
        if v != "":
            return False

    # require minimum honeypot count
    if len(honeypot_keys) < MIN_HONEYPOTS:
        return False

    # recreate frontend hash
    hash_input = ":".join(
        [
            *sorted(honeypot_keys),
            str(ts_int),
        ]
    )

    expected_sha = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    if sha != expected_sha:
        return False

    return True
