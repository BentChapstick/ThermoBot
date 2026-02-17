import sqlite3
import cloudscraper
import json
import time
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fake_useragent import UserAgent
from time import mktime, localtime, strftime
import termcolor as tc

# Initialize scraper to bypass Cloudflare
scraper = cloudscraper.create_scraper()
ua = UserAgent()

# Database path
if os.getenv("RUNNING_IN_DOCKER") == "true":
    database_path = "/app/Database/dish.db"
else:
    database_path = "Database/dish.db"

# Date setup
campus_tz = ZoneInfo("America/New_York")
date_today = datetime.now(campus_tz).strftime('%Y-%m-%d')
date_tomorrow = (datetime.now(campus_tz) + timedelta(1)).strftime('%Y-%m-%d')
date_2days = (datetime.now(campus_tz) + timedelta(2)).strftime('%Y-%m-%d')
dates = {"today": date_today} # , "tomorrow": date_tomorrow, "2 days": date_2days}

# API URLs
# https://apiv4.dineoncampus.com/locations/64b9990ec625af0685fb939d/periods/?date=2026-02-16
period_request = "https://apiv4.dineoncampus.com/locations/{location}/periods/?date={date}"
# https://apiv4.dineoncampus.com/locations/64b9990ec625af0685fb939d/menu?date=2026-02-16&period=6992dab154c66406ba4d0091
meal_data_request = "https://apiv4.dineoncampus.com/locations/{location}/menu?date={date}&period={period}"

dining_locations = {}
request_spacing_seconds = .5

def main():
    db_connection = sqlite3.connect(database_path)
    db_cursor = db_connection.cursor()

    # Delete the future meals to ensure they are up to date. 
    # for date in dates:
    #     print(f"DELETE FROM menuItems WHERE date = '{dates[date]}'")
    #     db_cursor.execute(f"DELETE FROM menuItems WHERE date = '{dates[date]}'")

    # Get locations from database
    db_cursor.execute("SELECT * FROM locations")
    rows = db_cursor.fetchall()
    for row in rows:
        dining_locations[row[0]] = row[1]

    for date in dates:
        date_time = dates[date]
        for location in dining_locations:
            print(f"Grabbing periods for {date_time} {location}")
            periods = get_periods(date_time, location)
            period_data = [{"name": p["name"], "UUID": p["id"]} for p in periods]
            db_cursor.executemany("INSERT OR REPLACE INTO time VALUES (:name, :UUID)", period_data)
            
            for period in period_data:
                meal_json = get_meal_data(period["UUID"], date_time, location)
                if meal_json != -1:
                    print("Meal_json: " + str(type(meal_json)) + " | " + str(meal_json)[0:100])
                    print("Period: " + str(type(period)) + " | " + str(period))
                    print("Location: " + str(type(location)) + " | " + str(location))

                    process_meal_data(meal_json, period, date_time, location, db_cursor)
            
            db_connection.commit()

def get_periods(date_time: str, location: str) -> list:
    request_string = period_request.format(date=date_time, location=dining_locations[location])
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

def get_meal_data(period, date_time, location):
    request_string = meal_data_request.format(period=period, date=date_time, location=dining_locations[location])
    print(request_string)
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

def process_meal_data(meal_json, period_info, date_time, location, db_cursor):
    categories = meal_json.get("period", {}).get("categories", [])

    for category in categories:
        station_name = category.get("name")
        
        for item in category.get("items"):
            # Nutrient Handling TODO Not yet updated for new JSON
            nutrients_json = None #handle_nutrients(db_cursor, item)
            
            # 3. Allergens/Labels)
            # In your snippet, there is no 'type' key. We have to guess by name or save all.
            # Here we just grab all filter names as labels/allergens.
            all_filters = [f["name"] for f in item.get("filters", [])]
            
            # 4. Prepare data for SQL
            # Make sure this matches your 13-column table structure exactly
            vals = (
                item.get("name"),
                station_name,
                item.get("ingredients", ""),
                item.get("portion", ""),
                item.get("desc", ""),
                nutrients_json,
                item.get("calories", ""),
                date_time,
                period_info["name"],
                location,
                str(all_filters), # allergens_json
                str(all_filters), # labels_json
                item.get("sortOrder", 0) 
            )
            
            try:
                db_cursor.execute("INSERT OR REPLACE INTO menuItems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals)
            except Exception as e:
                print(f"SQL Error inserting {item.get('name')}: {e}")

def handle_nutrients(db_cursor, item):
    nutrients_list = [{"name": n["name"], "value": n["value"], "uom": n["uom"], "value_numeric": n.get("value_numeric", "")} for n in item.get("nutrients", [])]
    db_cursor.executemany("INSERT OR REPLACE INTO menuNutrients VALUES (?, ?, ?, ?)", 
        [(n["name"], n["value"], n["uom"], n["value_numeric"]) for n in item.get("nutrients", [])])
    return str(nutrients_list)

if __name__ == "__main__":
    startTime = localtime()
    main()
    endTime =  localtime()
    print(tc.colored("Took: " + strftime("%M:%S", (localtime(mktime(endTime) - mktime(startTime)))), color="yellow", on_color="on_light_grey"))
