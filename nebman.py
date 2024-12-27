#!/usr/bin/python3
## 
## required imports
import os.path
import sqlite3
import sys
import requests
import shutil
import tarfile

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
        ##sys.exit()
    # if the database file doesn't exist create required table
    else:
        dbConnect = sqlite3.connect(nebmanDB)
        dbCurser = dbConnect.cursor()
        dbCurser.execute("CREATE TABLE nebmanClients(id, hostname, network, lighthouse, os, services, version, UNIQUE(hostname))")
        dbConnect.commit()
        #dbCurser.execute("CREATE TABLE projectZeroTickers(date, ticker, status)")
        #dbConnect.commit()
        dbConnect.close()
        # confirm DB exists (in case create above failed/ did not complete)
        if not os.path.exists(nebmanDB):
            sys.exit("Database does not exist, exiting")

def pullNebula():
    nebulaLinuxURL="https://github.com/slackhq/nebula/releases/download/v1.9.5/nebula-linux-amd64.tar.gz"
    nebulaLinuxDL="nebula-linux-amd64.tar.gz"
    nebulaLinuxCurrent="nebula-linux.tar.gz"
    nebulaFile="nebula"
    nebulaCertFile="nebula-cert"
    # If Nebula download doesn't exist, download it.
    if not os.path.exists(nebulaLinuxDL):
        response = requests.get(nebulaLinuxURL)
        response.raw.decode_content = True
        with open(nebulaLinuxDL, 'wb') as fileDL:
            for block in response.iter_content(chunk_size=1024):
                fileDL.write(block)
            fileDL.close()
        # If Nebula binary doesn't exist, extract the tar.
        if not os.path.exists(nebulaFile):
            nebulaTar = tarfile.open(nebulaLinuxDL)
            nebulaTar.extractall(filter='data')
            nebulaTar.close()

        



initDB()
pullNebula()

