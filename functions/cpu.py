def handler(event):
    n = int(event.get("n", 5_000_000))
    total = 0
    for i in range(n):
        total += i
    return {"sum": total, "n": n}
