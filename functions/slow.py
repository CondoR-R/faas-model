import time


def handler(event):
    seconds = event.get("seconds", 10)
    time.sleep(seconds)
    return {"slept": seconds}
