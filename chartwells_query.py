import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from time import mktime, localtime, strftime
import termcolor as tc

import requests

# curl_cffi lets us present a real Chrome TLS/HTTP2 fingerprint. Cloudflare
# scores plain-python TLS handshakes as bot traffic, so use it when available
# and fall back to requests otherwise.
try:
    from curl_cffi import requests as curl_requests
    IMPERSONATE = "chrome"
except ImportError:
    curl_requests = None
    IMPERSONATE = None

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

# dineoncampus sits behind Cloudflare. It rejects requests that do not look
# like the browser XHR the real site makes, so send a *consistent* modern
# Chrome identity. Do not randomize the User-Agent: a UA that disagrees with
# the sec-ch-ua hints (or that names a browser version from years ago) is a
# stronger bot signal than a repeated one.
CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
BASE_HEADERS = {
    "User-Agent": CHROME_UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://dineoncampus.com",
    "Referer": "https://dineoncampus.com/",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# Cloudflare blocks datacenter/hosting IP ranges outright, so a server run can
# get a 403 no matter how the request is shaped. Set DINEONCAMPUS_PROXY to a
# residential/consumer egress to get around that.
proxy_url = os.getenv("DINEONCAMPUS_PROXY")
PROXIES = {"http": proxy_url, "https": proxy_url} if proxy_url else None

dining_locations = {}
request_spacing_seconds = .5
request_retries = 3

# Set when any request comes back 403 so we can explain it once at the end
# and exit non-zero instead of silently writing an empty menu.
forbidden_seen = False
request_failures = 0

def get_json(url: str):
    """GET a dineoncampus API URL and return parsed JSON, or None on failure.

    Retries transient errors with backoff. A 403 is not retried past the first
    attempt: it means Cloudflare rejected us, and hammering it makes that worse.
    """
    global forbidden_seen, request_failures

    for attempt in range(1, request_retries + 1):
        try:
            if curl_requests is not None:
                response = curl_requests.get(url, headers=BASE_HEADERS, timeout=30,
                                             impersonate=IMPERSONATE, proxies=PROXIES)
            else:
                response = requests.get(url, headers=BASE_HEADERS, timeout=30,
                                        proxies=PROXIES)

            if response.status_code == 403:
                forbidden_seen = True
                print(tc.colored(f"403 Forbidden from {url}", color="red"))
                break

            if response.status_code == 429 or response.status_code >= 500:
                print(tc.colored(f"HTTP {response.status_code} from {url} "
                                 f"(attempt {attempt}/{request_retries})", color="yellow"))
                time.sleep(request_spacing_seconds * (2 ** attempt))
                continue

            response.raise_for_status()
            time.sleep(request_spacing_seconds)
            return response.json()

        except json.JSONDecodeError:
            print(tc.colored(f"Non-JSON response from {url}", color="red"))
            break
        except Exception as e:
            print(tc.colored(f"Error fetching {url} (attempt {attempt}/{request_retries}): {e}",
                             color="yellow"))
            time.sleep(request_spacing_seconds * (2 ** attempt))

    request_failures += 1
    return None

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

    items_written = 0

    for date in dates:
        date_time = dates[date]
        for location in dining_locations:
            print(f"Grabbing periods for {date_time} {location}")
            periods = get_periods(date_time, location)
            period_data = [{"name": p["name"], "UUID": p["id"]} for p in periods]
            db_cursor.executemany("INSERT OR REPLACE INTO time VALUES (:name, :UUID)", period_data)

            for period in period_data:
                meal_json = get_meal_data(period["UUID"], date_time, location)
                if meal_json is not None:
                    items_written += process_meal_data(meal_json, period, date_time,
                                                       location, db_cursor)

            db_connection.commit()

    db_connection.close()

    print(f"Wrote {items_written} menu items; {request_failures} request(s) failed.")

    if forbidden_seen:
        print(tc.colored(
            "\nCloudflare returned 403 for dineoncampus.\n"
            "This is an IP/edge block, not a bad request: the whole domain "
            "(including https://dineoncampus.com/ in a browser) refuses this host.\n"
            "Run this from a residential connection, or set DINEONCAMPUS_PROXY to a "
            "residential/consumer egress and retry.",
            color="red"))
        return 1

    return 0 if items_written else 1

def get_periods(date_time: str, location: str) -> list:
    request_string = period_request.format(date=date_time, location=dining_locations[location])
    response_json = get_json(request_string)
    if response_json is None:
        return []
    return response_json.get("periods", [])

def get_meal_data(period, date_time, location):
    request_string = meal_data_request.format(period=period, date=date_time,
                                              location=dining_locations[location])
    return get_json(request_string)

def process_meal_data(meal_json, period_info, date_time, location, db_cursor):
    # apiv4 nests the categories under "period"; the older v1 shape nested them
    # under menu.periods. Accept either so a response-shape change is visible
    # as a warning rather than a silently empty menu.
    categories = meal_json.get("period", {}).get("categories")
    if categories is None:
        categories = meal_json.get("menu", {}).get("periods", {}).get("categories", [])

    if not categories:
        print(tc.colored(f"No categories in response for {location} "
                         f"{period_info['name']} {date_time}", color="yellow"))
        return 0

    written = 0

    for category in categories:
        station_name = category.get("name")

        for item in category.get("items", []):
            # Nutrient Handling TODO Not yet updated for new JSON
            nutrients_json = None #handle_nutrients(db_cursor, item)

            # Allergens/Labels. The apiv4 filters have no 'type' key to split
            # allergens from labels, so store the full filter list in both.
            all_filters = [f["name"] for f in item.get("filters", [])]

            # Must match the 13-column menuItems table exactly.
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
                written += 1
            except Exception as e:
                print(f"SQL Error inserting {item.get('name')}: {e}")

    return written

def handle_nutrients(db_cursor, item):
    nutrients_list = [{"name": n["name"], "value": n["value"], "uom": n["uom"], "value_numeric": n.get("value_numeric", "")} for n in item.get("nutrients", [])]
    db_cursor.executemany("INSERT OR REPLACE INTO menuNutrients VALUES (?, ?, ?, ?)", 
        [(n["name"], n["value"], n["uom"], n["value_numeric"]) for n in item.get("nutrients", [])])
    return str(nutrients_list)

if __name__ == "__main__":
    startTime = localtime()
    exit_code = main()
    endTime =  localtime()
    print(tc.colored("Took: " + strftime("%M:%S", (localtime(mktime(endTime) - mktime(startTime)))), color="yellow", on_color="on_light_grey"))
    sys.exit(exit_code)
