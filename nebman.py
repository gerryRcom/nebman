#!/usr/bin/python3
## 
## required imports
import os.path
import sqlite3
import sys
import requests
import shutil
import tarfile

# Set Constants
NEBMANDB='nebmanDB.db'
CURRENTVERSION='1.9.5'

# Set global variables
lighthouseID = 10
endpointID = 50

def initDB():

# initialise a new DB for nebman or print contents if it exists.
    
    # check if database file exists, if not, create it.
    if not os.path.exists(NEBMANDB):
        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()
        dbCurser.execute("CREATE TABLE nebmanClients(id, hostname, network, lighthouse, os, services, version, UNIQUE(hostname))")
        dbConnect.commit()
        dbConnect.close()
        # confirm DB exists, in case create above failed/ did not complete.
        if not os.path.exists(NEBMANDB):
            sys.exit("Database does not exist, exiting")
    # if database does exist set ID values

def pullNebula():
    # Set file variables, concentrating on Linux for initial build
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

# Display all clients in the DB
def listClients():
        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()
        dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
        print(dbContent.fetchall())
        dbConnect.close()

def addClient():
    # add client to DB
    newHostname = input("Please enter new hostname (FQDN): ")
    newNetwork = input("Please enter network address (192.168.1.0): ")
    newLighthouse = input("Is this new a lighthouse (y/n): ")
    newOS = input("Please enter OS (Windows, Ubuntu, Fedora): ")
    newServices = input("Please enter comma seperated list of services (ssh,http): ")
    newVersion = CURRENTVERSION

    # Set new ID value based on endpoint type
    if newLighthouse == 'y':
        newID = lighthouseID
    else:
        newID = endpointID

    # If DB doesn't exist, exit the app, otherwise create new entry in the DB
    if not os.path.exists(NEBMANDB):
        sys.exit("Database does not exist, exiting")
    else:
        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()

        # pass inserted values into sqlite3 db
        dbCurser.execute("INSERT OR IGNORE INTO nebmanClients(id, hostname, network, lighthouse, os, services, version) VALUES(?, ?, ?, ?, ?, ?, ?)",(newID, newHostname, newNetwork, newLighthouse, newOS, newServices, newVersion))
        dbConnect.commit()
        # Close DB connection
        dbConnect.close()

if __name__ == "__main__":
    initDB()
    pullNebula()
    print("---------------------------------")
    print("1 - View current clients in the DB")
    print("2 - Add new client in the DB")
    print("---------------------------------")
    menuChoice = input("Please select from the menu above: ")

    if menuChoice == '1':
        listClients()
    elif menuChoice == '2':
        addClient()

    

