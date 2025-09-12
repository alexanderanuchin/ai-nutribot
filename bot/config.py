import os
from dataclasses import dataclass

@dataclass
class Config:
    token: str
    api_base: str
    backend_user: str | None
    backend_pass: str | None
    redis_url: str | None
    fallback_products_file: str

    @staticmethod
    def load():
        return Config(
            token=os.getenv("TELEGRAM_BOT_TOKEN",""),
            api_base=os.getenv("API_BASE","http://backend:8000/api"),
            backend_user=os.getenv("BOT_BACKEND_USERNAME"),
            backend_pass=os.getenv("BOT_BACKEND_PASSWORD"),
            redis_url=os.getenv("REDIS_URL"),
            fallback_products_file=os.getenv("FALLBACK_PRODUCTS_FILE","data/products.json"),
        )
