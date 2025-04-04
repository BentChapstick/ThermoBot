import sqlite3
import cloudscraper
import json
import time
import os
from datetime import datetime, timezone, timedelta
from fake_useragent import UserAgent

# Initialize scraper to bypass Cloudflare
scraper = cloudscraper.create_scraper()
ua = UserAgent()

# Database path
if os.getenv("RUNNING_IN_DOCKER") == "true":
    database_path = "/app/Database/dish.db"
else:
    database_path = "Database/dish.db"

# Date setup
date_today = datetime.now(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')
date_tomorrow = (datetime.now(timezone(timedelta(hours=-4))) + timedelta(1)).strftime('%Y-%m-%d')
date_2days = (datetime.now(timezone(timedelta(hours=-4))) + timedelta(2)).strftime('%Y-%m-%d')
dates = {"today": date_today, "tomorrow": date_tomorrow, "2 days": date_2days}

# API URLs
period_request = "https://api.dineoncampus.com/v1/location/{location}/periods?platform=0&date={date}"
meal_data_request = "https://api.dineoncampus.com/v1/location/{location}/periods/{period}?platform=0&date={date}"

dining_locations = {}
request_spacing_seconds = 1

def main():
    db_connection = sqlite3.connect(database_path)
    db_cursor = db_connection.cursor()

    # Get locations from database
    db_cursor.execute("SELECT * FROM locations")
    rows = db_cursor.fetchall()
    for row in rows:
        dining_locations[row[0]] = row[1]

    for date in dates:
        for location in dining_locations:
            print(f"Grabbing periods for {dates[date]} {location}")
            periods = get_periods(date, location)
            period_data = [{"name": p["name"], "UUID": p["id"]} for p in periods]
            db_cursor.executemany("INSERT OR REPLACE INTO time VALUES (:name, :UUID)", period_data)
            
            for period in period_data:
                meal_json = get_meal_data(period["UUID"], date, location)
                if meal_json != -1:
                    process_meal_data(meal_json, period, date, location, db_cursor)
            
            db_connection.commit()

def get_periods(date, location):
    request_string = period_request.format(date=dates[date], location=dining_locations[location])
    try:
        headers = {"User-Agent": ua.random}  # Randomized user agent
        response = scraper.get(request_string, headers=headers, timeout=30)
        response.raise_for_status()
        time.sleep(request_spacing_seconds)
        
        if response.status_code == 200:
            response_json = response.json()
            return response_json.get("periods", [])
        
    except Exception as e:
        print(f"Error fetching periods: {e}")
    return []

def get_meal_data(period, date, location):
    request_string = meal_data_request.format(period=period, date=dates[date], location=dining_locations[location])
    try:
        headers = {"User-Agent": ua.random}  # Randomized user agent
        response = scraper.get(request_string, headers=headers, timeout=30)
        response.raise_for_status()
        time.sleep(request_spacing_seconds)
        
        if response.status_code == 200:
            return response.json()
        
    except Exception as e:
        print(f"Error fetching meal data: {e}")
    return -1

def process_meal_data(meal_json, period, date, location, db_cursor):
    categories = meal_json.get("menu", {}).get("periods", {}).get("categories", [])
    for category in categories:
        station_name = category["name"]
        for item in category["items"]:
            item.update({
                "time": period["name"],
                "date": dates[date],
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
                dates[date], period["name"], location, item["allergens_json"], item["labels_json"], item.get("sort_order", 0)))

def handle_nutrients(db_cursor, item):
    nutrients_list = [{"name": n["name"], "value": n["value"], "uom": n["uom"], "value_numeric": n.get("value_numeric", "")} for n in item.get("nutrients", [])]
    db_cursor.executemany("INSERT OR REPLACE INTO menuNutrients VALUES (?, ?, ?, ?)", 
        [(n["name"], n["value"], n["uom"], n["value_numeric"]) for n in item.get("nutrients", [])])
    return str(nutrients_list)

if __name__ == "__main__":
    main()
