import sqlite3
from datetime import datetime
import os.path

fetch_amount = 1000 #how many rows max per request
db_name = "receipt.db"

#adapt datetime.datetime to timezone-naive ISO 8601 date
#have to specify because the default adapter is deprecated in sqlite3
def adapt_datetime_iso(val):
    return val.isoformat()
#
#check if the .db file exists
def exists():
    return os.path.isfile(db_name)
#
#create the database if it doesn't exist
#doesn't modify the tables even if it does exist
def create_db():
    con = sqlite3.connect(db_name)
    sqlite3.register_adapter(datetime, adapt_datetime_iso)
    cur = con.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS receipt(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date_time TEXT NOT NULL,
    receipt_date_time TEXT,
    price REAL NOT NULL,
    vat REAL NOT NULL
    )''')
    
    con.commit()
    con.close()
#
#convert the data from text recognition to be suitable for inserting into databse
def convert_data(data):
    #incoming data = date_time, price, vat (only receipt date is allowed to be null)
    cd = []
    
    #add trailing ":00" if needed and convert to datetime format
    if data["date_time"]:
        if len(data["date_time"]) < 18:
            data["date_time"] += ":00"
        #
        receipt_date = datetime.strptime(data["date_time"], "%d.%m.%Y %H:%M:%S")
    else:
        receipt_date = None
    #
    #create data list
    data_item = (datetime.now(), receipt_date, float(data["price"]), float(data["vat"]))
    cd.append(data_item)
    
    return cd
#
#insert one row of data into database
def add_row(data):  
    if not exists():
        create_db()
    #try to convert data, if invalid, return false
    try:
        c_data = convert_data(data)
    except Exception:
        return False
        pass
    #
    con = sqlite3.connect(db_name)
    sqlite3.register_adapter(datetime, adapt_datetime_iso)
    cur = con.cursor()

    #Data needs to be (datetime, datetime, float, int), can accept multiple rows
    cur.executemany("INSERT INTO receipt VALUES(null, ?, ?, ?, ?)", c_data)
    
    con.commit()   
    con.close()
    
    return True
#
#return next max {fetch_amount} of rows from the database
def get_rows(offset):
    rows = None
    con = sqlite3.connect(db_name)
    sqlite3.register_adapter(datetime, adapt_datetime_iso)
    cur = con.cursor()

    cur.execute('''
    SELECT id, STRFTIME('%d.%m.%Y %H:%M:%S', entry_date_time), STRFTIME('%d.%m.%Y %H:%M:%S', receipt_date_time), price, vat 
    FROM receipt 
    ORDER BY id LIMIT ? OFFSET ?
    ''', (fetch_amount, fetch_amount * offset))
    
    rows = cur.fetchall()
    con.close()

    return rows
#
#count how many entries total in database
def count():
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    
    cur.execute("SELECT COUNT(*) FROM receipt")
    amount = cur.fetchall() 
    
    con.close()
    #sqlite3 always returns an array of tuples, so [0][0] returns only the value
    return amount[0][0] 
#