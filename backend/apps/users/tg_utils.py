import hashlib, hmac, json
from urllib.parse import parse_qsl

def verify_init_data(init_data: str, bot_token: str) -> dict:
    """
    Проверка по документации Telegram WebApp:
    - data_check_string = join(sorted("{k}={v}")) без 'hash', через '\n'
    - secret_key = SHA256(bot_token)
    - hmac_sha256(data_check_string, secret_key) == provided hash (hex)
    """
    if not init_data or not bot_token:
        raise ValueError("init_data or token missing")

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise ValueError("hash missing")

    data_check = "\n".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calc_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    if calc_hash != received_hash:
        raise ValueError("hash mismatch")

    # user/json поля
    parsed = {}
    for k, v in params.items():
        if k in ("user","receiver","chat"):
          try: parsed[k] = json.loads(v)
          except Exception: parsed[k] = v
        else:
          parsed[k] = v
    return parsed
