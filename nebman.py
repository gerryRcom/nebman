#!/usr/bin/python3
## 
## required imports
import os.path
import sqlite3
import sys
print("hey")


def initDB():
# initialise a new DB for nebman or print contents if it exists.
    nebmanDB='nebmanDB.db'

# check if database file exists, if it does print all content (for troubleshooting)
    if os.path.exists(nebmanDB):
        dbConnect = sqlite3.connect(nebmanDB)
        dbCurser = dbConnect.cursor()
        dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
        print(dbContent.fetchall())
        #dbContent = dbCurser.execute("SELECT * FROM projectZeroTickers")
        #print(dbContent.fetchall())
        dbConnect.close()
        sys.exit()
    # if the database file doesn't exist create required table
    else:
        dbConnect = sqlite3.connect(nebmanDB)
        dbCurser = dbConnect.cursor()
        dbCurser.execute("CREATE TABLE nebmanClients(UNIQUE(hostname), id, network, lighthouse, os, services, version)")
        dbConnect.commit()
        #dbCurser.execute("CREATE TABLE projectZeroTickers(date, ticker, status)")
        #dbConnect.commit()
        dbConnect.close()
        # confirm DB exists (in case create above failed/ did not complete)
        if os.path.exists(nebmanDB):
            sys.exit()
        else:
            sys.exit("Database does not exist, exiting")