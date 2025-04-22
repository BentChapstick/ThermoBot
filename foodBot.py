# Script that will get the dinner options for MTU Dinning

import os
from inspect import _empty
import sqlite3
from datetime import date
from enum import Enum

class Hall(Enum):
    DHH = ('DHH', ["Homestyle", "Flame", "Chef Francisco Soups"])
    Wads = ('Wadsworth', ["Homestyle", "Flame", "Delicious Without"])
    McNair = ('McNair', ["Flame", "The Kitchen", "Chef Francisco Soups"])


databasePath = os.path.join("Database", "dish.db")

# Run query to the database
def query(query):
    
    try:
        db = sqlite3.connect(databasePath)
        cursor = db.cursor()

        cursor.execute( query )

        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data    
    
    except:
        print("unable to open database")

        cursor.close()
        db.close()

        return None

def currentDate():
    currentDate = date.today()


    return currentDate

# Main

# Wadsworth

def hallMeal(time, hall: Hall):

    menu = {}

    locations = hall.value[1]
    name = hall.value[0]

    for loc in locations:
        
        data = query(f"SELECT name, description FROM menuItems WHERE location = '{name}' AND station = '{loc}' AND description is not NULL and date = '{currentDate()}' and time = '{time}'")
                      #SELECT name, description FROM menuItems WHERE location = 'Wadsworth' AND station = 'Homestyle' AND description is not NULL and date = '2025-03-28' and time = 'Lunch'
        try:
            dishes = []
            for item in data:
        
                dishes.append(f"{item[0]}")
            
        except:
            dishes.append(f"No dishes at {loc}")

        menu[loc] = dishes

            
    
    return menu

def getMeals(mealTime):
    menu = {}
    
    for location in Hall:
        menu[location.value[0]] = hallMeal(mealTime, location)

    return menu

def getDescription(item):
    data = query( f"SELECT description from menuItems where name = '{item}' LIMIT 1" )
    return data[0][0]

    

if __name__ == '__main__':
    meal = "Lunch"
    meals = getMeals(meal)
    print(meals)
