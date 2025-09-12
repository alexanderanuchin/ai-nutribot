from nutribot.celery import app

@app.task
def dummy_task(x: int) -> int:
    return x * 2
