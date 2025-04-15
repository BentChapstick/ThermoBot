import requests
import random

XKCDCURRENT = "https://xkcd.com/info.0.json"
XKCDARCHIVE = "https://xkcd.com/{number}/info.0.json"

def latestxkcd() -> dict:
    r = requests.get(XKCDCURRENT)
    intake = r.json()
    return intake

def maxXKCD() -> int:
    return int(latestxkcd()["num"])

def randomXKCD() -> dict:
    r= requests.get(XKCDARCHIVE.format(number=random.randint(1, maxXKCD())))
    intake = r.json()
    return intake

if __name__ == "__main__":
    print(latestxkcd())