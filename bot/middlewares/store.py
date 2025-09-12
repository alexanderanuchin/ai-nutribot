from aiogram.dispatcher.middlewares.base import BaseMiddleware

class StoreMiddleware(BaseMiddleware):
    def __init__(self, store, webapp_url: str):
        super().__init__()
        self.store = store
        self.webapp_url = webapp_url

    async def __call__(self, handler, event, data):
        # кладём зависимости в data — aiogram передаст их по именам параметров хендлеров
        data["store"] = self.store
        data["webapp_url"] = self.webapp_url
        return await handler(event, data)
