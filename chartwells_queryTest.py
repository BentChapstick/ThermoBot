import os
import sqlite3
import cloudscraper
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from fake_useragent import UserAgent
from time import mktime, localtime, strftime
import termcolor as tc

# Database path
if os.getenv("RUNNING_IN_DOCKER") == "true":
    DATABASE = "/app/Database/dish.db"
else:
    DATABASE = "Database/dish.db"

# API URLs
PERIOD_TARGET = "https://api.dineoncampus.com/v1/location/{location}/periods?platform=0&date={date}"
MEAL_TARGET = "https://api.dineoncampus.com/v1/location/{location}/periods/{period}?platform=0&date={date}"

SCRAPER = cloudscraper.create_scraper()
UA = UserAgent()

async def main() -> None:
    # Constant Def
    TODAY:str = datetime.now(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')

    # Variable Def
    locList: list = []
    scrape_targets: list = []
    meal_targets: list = []


    group = await asyncio.gather(*scrape_targets) # process coroutines

    loclist = get_locs(TODAY)
    update_period(TODAY, loclist, group)

    #group = await asyncio.gather(*meal_targets) # process coroutines

    

    print(group)
    return

async def get_locs(TODAY:str ) -> list:
    locList = []
    # Get locations from database
    try:
        with sqlite3.connect(DATABASE) as conn:
            print(tc.colored(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully." , color="green", on_color="on_light_grey"))
            cur = conn.cursor()
            cur.execute("SELECT * FROM locations")
            rows = cur.fetchall()
            for row in rows:
                locList.append(row[1])
                
            print(tc.colored("Access Done",color="green", on_color="on_light_grey"))
    except sqlite3.OperationalError as e:
        print("Failed to open Database: ", e)

    return locList


async def update_period(TODAY: str, locList: list, locGroup: asyncio.futures) -> asyncio.coroutines:
    scrape_targets: list = []
    meal_targets: list = []
    for i in locList:
        scrape_targets.append(scrape_period(TODAY, i)) # assemble list of coroutines

    try:
        with sqlite3.connect(DATABASE) as conn:
            print(tc.colored(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully." , color="green", on_color="on_light_grey"))
            cur = conn.cursor()
            for idx, loc in enumerate(locGroup):
                for per in loc:
                    cur.execute("REPLACE INTO time(mealTime, apiUUID) VALUES(?,?)", tuple((per["name"], per["id"])))
                    meal_targets.append(scrape_meals(per["id"], TODAY, locList[idx])) # assembly list of coroutines
            conn.commit()
            print(tc.colored("Access Done",color="green", on_color="on_light_grey"))
    except sqlite3.OperationalError as e:
        print("Failed to open Database: ", e)
    return meal_targets

async def scrape_period(date_time: str, uuid: str) -> dict:
    TARGET = PERIOD_TARGET.format(date=date_time, location=uuid)
    # MEAL = MEAL_TARGET.format(date=date_time, location=uuid)
    try:
        headers = {"User-Agent": UA.random}  # Randomized user agent
        response = SCRAPER.get(TARGET, headers=headers, timeout=30)
        response.raise_for_status()

        if response.status_code == 200:
            response_json = response.json()
            return response_json.get("periods", [])
        else:
            return []
        
    except Exception as e:
        print(f"Error fetching periods: {e}")
    print(TARGET)
    return []

async def scrape_meals(per: str, date_time: str , uuid: str) -> dict:
    TARGET = MEAL_TARGET.format(period=per, date=date_time, location=uuid)
    try:
            headers = {"User-Agent": UA.random}  # Randomized user agent
            response = SCRAPER.get(TARGET, headers=headers, timeout=30)
            response.raise_for_status()

            if response.status_code == 200:
                return response.json()
            else:
                return -1
    except Exception as e:
        print(f"Error fetching meal data: {e}")
    return -1

def process_meal_data(meal_json, period, date_time, location, db_cursor):
    categories = meal_json.get("menu", {}).get("periods", {}).get("categories", [])
    for category in categories:
        station_name = category["name"]
        for item in category["items"]:
            item.update({
                "time": period["name"],
                "date": date_time,
                "location": location,
                "station": station_name,
                "nutrients_json": handle_nutrients(db_cursor, item)
            })
            
            allergens_list = [f["name"] for f in item.get("filters", []) if f["type"] == "allergen"]
            labels_list = [f["name"] for f in item.get("filters", []) if f["type"] == "label"]
            item["allergens_json"] = str(allergens_list)
            item["labels_json"] = str(labels_list)
            
            db_cursor.execute("INSERT OR REPLACE INTO menuItems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item["name"], station_name, item.get("ingredients", ""), item.get("portion", ""),
                item.get("desc", ""), item["nutrients_json"], item.get("calories", ""),
                date_time, period["name"], location, item["allergens_json"], item["labels_json"], item.get("sort_order", 0)))

def handle_nutrients(db_cursor, item):
    nutrients_list = [{"name": n["name"], "value": n["value"], "uom": n["uom"], "value_numeric": n.get("value_numeric", "")} for n in item.get("nutrients", [])]
    db_cursor.executemany("INSERT OR REPLACE INTO menuNutrients VALUES (?, ?, ?, ?)", 
        [(n["name"], n["value"], n["uom"], n["value_numeric"]) for n in item.get("nutrients", [])])
    return str(nutrients_list)

if __name__ == "__main__":
    startTime = localtime()
    asyncio.run(main())
    endTime =  localtime()
    print(tc.colored("Took: " + strftime("%M:%S", (localtime(mktime(endTime) - mktime(startTime)))), color="yellow", on_color="on_light_grey"))
