import requests
import cloudscraper
from fake_useragent import UserAgent


target = "https://api.dineoncampus.com/v1/location/64b9990ec625af0685fb939d/periods?platform=0&date=2025-04-07"
targetA = "https://api.dineoncampus.com/v1/location/64b9990ec625af0685fb939d/periods?platform=0&date=2025-04-07"


scraper = cloudscraper.create_scraper()
ua = UserAgent()

headers = {"User-Agent": ua.random}  # Randomized user agent
response = scraper.get(target, headers=headers, timeout=30)
response.raise_for_status()

for i in range(0,100):
    print(ua.random)