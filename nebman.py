#!/usr/bin/python3
## 
## required imports
import os.path
import subprocess
import sqlite3
import sys
import requests
import shutil
import tarfile

# Set Constants
NEBMANDB='nebmanDB.db'
CURRENTVERSION='1.9.5'

# Set global variables
existingLighthouseID = 10
existingEndpointID = 50
existingNetwork = "notset"

# terminal colour text codes (found via a so page)
class bcolors:
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    vmTag = ''

# Report on the current state of key elements of the app.
def checkState():
    # Does the DB exist
    if os.path.exists(NEBMANDB):
        print("- Database is found: " + bcolors.GREEN + "Yes" + bcolors.END)
    else:
        print("- Database is found: " + bcolors.RED + "No" + bcolors.END)
    # Does the Certs folder exist   
    if os.path.exists('./certs/'):
        print("- Certs folder is found: " + bcolors.GREEN + "Yes" + bcolors.END)
    else:
        print("- Certs folder is found: " + bcolors.RED + "No" + bcolors.END)
    # Does the CA exist   
    if os.path.exists('./certs/ca.crt') and os.path.exists('./certs/ca.key'):
        print("- CA cert and key are found: " + bcolors.GREEN + "Yes" + bcolors.END)
    else:
        print("- CA cert and key are found: " + bcolors.RED + "No" + bcolors.END)



# initialise a new DB for nebman or load settings if existing DB and contents are located.
def initDB():
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
    # if database does exist set required values
    else:
        # Reference the global variables 
        global existingLighthouseID
        global existingEndpointID
        global existingNetwork

        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()
        dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
        for row in dbContent:
            existingNetwork = row[2]
            if row[3] == 'y':
                if row[0] > existingLighthouseID:
                    existingLighthouseID = row[0]
            else:
                if row[0] > existingEndpointID:
                    existingEndpointID = row[0]

# Add a function to create ansible directory for inventory file
def ansibleInit():
    if not os.path.exists('ansible'):
        os.makedirs('ansible')

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
            #shutil.copyfile('./nebula', './ansible/playbooks/files/nebula')


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
        newID = existingLighthouseID + 1
    else:
        newID = existingEndpointID + 1

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

def endpointCertGen(certType):
    # make certs dir if it doesn't already exist
    if not os.path.exists('certs'):
        os.makedirs('certs')

    # new endpoint cert generation
    if certType == '1':
        if existingNetwork == "notset":
            print("No endpoints exist in the DB, please add at least one")
        #  check if ca eists and if it doesn't request that it be generated
        elif not os.path.exists('certs/ca.crt') or not os.path.exists('certs/ca.key'):
            print ("CA cert does not exist, please generate one first.")
        else:
            x = 0
            y = 0
            dbConnect = sqlite3.connect(NEBMANDB)
            dbCurser = dbConnect.cursor()
            dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
            print("Generating cert for endpoint")
            print("----------------------------------")
            for row in dbContent:
                print(str(x) +" - "+row[1])
                x+=1
            # Close DB connection
            dbConnect.close()
            endpointSelection = input("Select an endpoint from list above (0, 1 ..): ")

            dbConnect = sqlite3.connect(NEBMANDB)
            dbCurser = dbConnect.cursor()
            dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
            for row in dbContent:
                if endpointSelection == str(y):
                    newEndpointCertCmd="./nebula-cert sign -ca-crt ./certs/ca.crt -ca-key ./certs/ca.key -out-crt ./certs/" +row[1]+ ".crt -out-key ./certs/" +row[1]+ ".key -name " +row[1]+ " -ip " + existingNetwork + "." + str(row[0]) + "/24"
                    subprocess.call(newEndpointCertCmd, shell=True)
                    break
                else:
                    y+=1
            # Close DB connection
            dbConnect.close()

    # new ca cert generation, this should only be done once in most cases
    elif certType == '99':
        #  check if ca eists and if it does request that it be deleted
        if os.path.exists('certs/ca.crt') or os.path.exists('certs/ca.key'):
            print ("CA cert alrady exists, you need to manually delete CA cert and key first.")
        else:
            print("Generating initial CA cert for org")
            print("----------------------------------")
            orgName = input("Please enter org name: ")
            newOrgCertCmd = "./nebula-cert ca -out-crt ./certs/ca.crt -out-key ./certs/ca.key -name \""+orgName+"\""
            subprocess.call(newOrgCertCmd, shell=True)
    else:
        print("invalid choice")

## Cert purge, should only be used in event an entire new set of certs is going to be generated.
def purgeCerts():
    if not os.path.exists('certs'):
        print("No certs found, nothing to do here")
    else:
        print("## Warning, this is destructive, ALL CERTS WILL BE DELETED, inc CA ##")
        confirmChoice = input("Please type yes to confirm you wish to proceed: ")
        if confirmChoice == "yes":
            certsDir = "certs/"
            certFiles = os.listdir(certsDir)
            # iterate through files and only delete .crt and .key files.
            for certFile in certFiles:
                if certFile.endswith(".crt") or certFile.endswith(".key"):
                    os.remove(os.path.join(certsDir, certFile))
        else:
            print("Not confirmed, exiting.")


if __name__ == "__main__":
    initDB()
    ansibleInit()
    pullNebula()
    print("---------------------")
    print("Current status of app")
    print("---------------------")
    checkState()
    print("---------------------------------")
    print("1 - View current clients in the DB")
    print("2 - Add new client in the DB")
    print("3 - Generate new CA cert for organisation")
    print("4 - Generate certs for an endpoint in the DB")
    print("99 - Purge all certs")
    print("---------------------------------")
    menuChoice = input("Please select from the menu above: ")

    if menuChoice == '1':
        listClients()
    elif menuChoice == '2':
        addClient()
    elif menuChoice == '3':
        endpointCertGen("99")
    elif menuChoice == '4':
        endpointCertGen("1")
    elif menuChoice == '99':
        purgeCerts()

    

