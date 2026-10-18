def handler(event):
    return {"echo": event, "keys": sorted(event.keys())}
