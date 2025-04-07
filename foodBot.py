# Script that will get the dinner options for MTU Dinning

from asyncio.windows_events import NULL
from inspect import _empty
import sqlite3
from datetime import date


databasePath = "A:\\Website\\DISH-API\\Database\\dish.db"


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

def Wadsworth(time):

    locations = ["Homestyle", "Flame", "Delicious Without"]

    menu = []

    for loc in locations:
        
        data = query(f"SELECT name, description FROM menuItems WHERE location = 'Wadsworth' AND station = '{loc}' AND description is not NULL and date = '{currentDate()}' and time = '{time}'")
                      #SELECT name, description FROM menuItems WHERE location = 'Wadsworth' AND station = 'Homestyle' AND description is not NULL and date = '2025-03-28' and time = 'Lunch'
        try:
            dishes = []
            for item in data:
        
                dishes.append(f"{item[0]}")
            
        except:
            dishes.append(f"No dishes at {loc}")

        menu.append(dishes)

            
    
    return menu

def DHH(time):


    locations = ["Homestyle", "Flame", "Chef Francisco Soups"]

    menu = []

    for loc in locations:
        
        data = query(f"SELECT name, description FROM menuItems WHERE location = 'DHH' AND station = '{loc}' AND description is not NULL and date = '{currentDate()}' and time = '{time}'")

        # If DHH is not serving a meal
        if len(data) is 0:
            temp = [None]
            menu.append(temp)
        
        else:

            try:
                dishes = []
                for item in data:

                    dishes.append(f"{item[0]}")
                
            except:
                dishes.append(f"No dishes at {loc}")

            menu.append(dishes)

    return menu

def McNair(time):

    locations = [ "Flame", "The Kitchen", "Chef Francisco Soups"]

    menu = []

    for loc in locations:
        
        data = query(f"SELECT name, description FROM menuItems WHERE location = 'McNair' AND station = '{loc}' AND description is not NULL and date = '{currentDate()}' and time = '{time}'")

        try:
            dishes = []

            for item in data:

                if item is None:
                    dishes.append("None")
                    break

                dishes.append(f"{item[0]}")
            
        except:
            dishes.append(f"No dishes at {loc}")

        menu.append(dishes)

    return menu

def getMeals(meal):
    
    menu =  [ Wadsworth(meal) , DHH(meal) , McNair(meal) ]

    return menu

def getDescription(item):
    data = query( f"SELECT description from menuItems where name = '{item}' LIMIT 1" )
    return data[0][0]

    

if __name__ == '__main__':
    meal = "Lunch"
    #Wadsworth(meal)
    print(Wadsworth(meal))
    print(DHH(meal))
    print(McNair(meal))

