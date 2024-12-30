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
import base64

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
    if not os.path.exists('ansible/inventory'):
        os.makedirs('ansible/inventory')
    if not os.path.exists('ansible/playbooks'):
        os.makedirs('ansible/playbooks')
    if not os.path.exists('ansible/playbooks/templates'):
        os.makedirs('ansible/playbooks/templates')
    if not os.path.exists('ansible/playbooks/files'):
        os.makedirs('ansible/playbooks/files')

def ansibleGen():
    # Generate ansile directory structure if it doesn't exist.
    ansibleInit()
    # Generate inventory file once database exists
    if not os.path.exists(NEBMANDB):
        sys.exit("Database does not exist, exiting")
    elif existingNetwork == "notset":
        sys.exit("Network not configured, please ensure hosts including a lighthouse are defined, exiting")       
    else:
        # open DB connection and iterate through to find Lighthouse details
        x = 0
        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()
        dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
        for row in dbContent:
            if row[3] == 'y' and x < 1:
                lighthouseHostname = row[1]
                lighthouseIP = existingNetwork + "." + str(row[0])
                x+=1
        dbConnect.close()

        # open DB connection and filestream for ansible inventory.ini file to find host details
        dbConnect = sqlite3.connect(NEBMANDB)
        dbCurser = dbConnect.cursor()
        dbContent = dbCurser.execute("SELECT * FROM nebmanClients")
        ansIventory = open("ansible/inventory/inventory.ini", "w")
        for row in dbContent:
            ansIventory.write(row[1]+" cert_name="+row[1]+" lighthouse_ip="+lighthouseIP+" lighthouse_hostname="+lighthouseHostname+"\n")
        # Write hostnames out to inventory file
        for row in dbContent:
            ansIventory.write(row[1]+" cert_name="+row[1]+"\n")
        # Close DB connection and file stream
        dbConnect.close()
        ansIventory.close()
    # Copy nebula binary to Ansible files folder.
    if os.path.exists("nebula"):
        shutil.copyfile('./nebula', './ansible/playbooks/files/nebula')

    # Write ansible playbook out to file from base64 version
    # base64 of playbook to simplify storage
    ansPlaybook="IyEvdXNyL2Jpbi9lbnYgYW5zaWJsZS1wbGF5Ym9vawotLS0KLSBuYW1lOiBDb25maWd1cmUgYW5kIHN0YXJ0IE5lYnVsYQogIGhvc3RzOiBuZWJ1bGEKICBiZWNvbWU6IHRydWUKICBnYXRoZXJfZmFjdHM6IGZhbHNlCgogIHRhc2tzOgogIC0gbmFtZTogQ3JlYXRlIGRpciBmb3IgTmVidWxhIGZpbGVzCiAgICBmaWxlOgogICAgICBwYXRoOiAiL3Vzci9sb2NhbC9iaW4vbmVidWxhIgogICAgICBzdGF0ZTogZGlyZWN0b3J5CiAgICAgIG1vZGU6ICcwNzAwJwoKICAtIG5hbWU6IENvcHkgY2VydCBmaWxlcwogICAgY29weToKICAgICAgc3JjOiAie3sgaXRlbSB9fSIKICAgICAgZGVzdDogIi91c3IvbG9jYWwvYmluL25lYnVsYSIKICAgICAgbW9kZTogJzA2MDAnCiAgICBsb29wOgogICAgICAtIC4vY2VydHMve3sgY2VydF9uYW1lIH19LmtleQogICAgICAtIC4vY2VydHMve3sgY2VydF9uYW1lIH19LmNydAogICAgICAtIC4vY2VydHMvY2EuY3J0CgogIC0gbmFtZTogQ29weSBuZWJ1bGEgYmluYXJ5CiAgICBjb3B5OgogICAgICBzcmM6ICJ7eyBpdGVtIH19IgogICAgICBkZXN0OiAiL3Vzci9sb2NhbC9iaW4vbmVidWxhLyIKICAgICAgbW9kZTogJzA3MDAnCiAgICBsb29wOgogICAgICAtIC4vYW5zaWJsZS9wbGF5Ym9va3MvZmlsZXMvbmVidWxhCiAgCiAgLSBuYW1lOiBDb3B5IE5lYnVsYSBjb25maWcKICAgIHRlbXBsYXRlOgogICAgICBzcmM6IG5lYnVsYS55bWwuajIKICAgICAgZGVzdDogL3Vzci9sb2NhbC9iaW4vbmVidWxhL3t7IGNlcnRfbmFtZSB9fS55bWwKICAgICAgbW9kZTogJzA2NDQnCgogIC0gbmFtZTogQ29weSBzZXJ2aWNlCiAgICB0ZW1wbGF0ZToKICAgICAgc3JjOiBuZWJ1bGEuc2VydmljZS5qMgogICAgICBkZXN0OiAvZXRjL3N5c3RlbWQvc3lzdGVtL25lYnVsYS5zZXJ2aWNlCiAgICAgIG1vZGU6ICcwNjQ0JwoKICAtIG5hbWU6IFN0YXJ0IE5lYnVsYSBzZXJ2aWNlCiAgICBhbnNpYmxlLmJ1aWx0aW4uc2VydmljZToKICAgICAgbmFtZTogbmVidWxhCiAgICAgIHN0YXRlOiBzdGFydGVkCiAgICAgIGVuYWJsZWQ6IHllcwoKICAtIG5hbWU6IENvbmZpZ3VyZSBVRlcgTmVidWxhCiAgICBjb21tdW5pdHkuZ2VuZXJhbC51Znc6CiAgICAgIHJ1bGU6IGFsbG93CiAgICAgIHBvcnQ6ICc0MjQyJwogICAgICBwcm90bzogdWRwCgogIC0gbmFtZTogUmVsb2FkIFVGVyAodG8gYXBwbHkgbmV3IHJ1bGUpCiAgICBjb21tdW5pdHkuZ2VuZXJhbC51Znc6CiAgICAgIHN0YXRlOiByZWxvYWRlZAouLi4="
    ansPlaybookDecode = base64.b64decode(ansPlaybook)
    ansPlaybookDecode = ansPlaybookDecode.decode("utf-8")
    ansPlaybook = open("ansible/playbooks/nebula.yml", "w")
    ansPlaybook.write(ansPlaybookDecode)
    ansPlaybook.close()
    
    # Write Linux service config template out to file from base64 version
    # base64 of template to simplify storage
    ansLinuxService="W1VuaXRdCkRlc2NyaXB0aW9uPU5lYnVsYSBNZXNoIFNlcnZpY2UKQWZ0ZXI9bmV0d29yay50YXJnZXQKCltTZXJ2aWNlXQpFeGVjU3RhcnQ9L3Vzci9sb2NhbC9iaW4vbmVidWxhL25lYnVsYSAtY29uZmlnIC91c3IvbG9jYWwvYmluL25lYnVsYS97eyBjZXJ0X25hbWUgfX0ueW1sClJlc3RhcnQ9YWx3YXlzCgpbSW5zdGFsbF0KV2FudGVkQnk9bXVsdGktdXNlci50YXJnZXQ="
    ansLinuxServiceDecode = base64.b64decode(ansLinuxService)
    ansLinuxServiceDecode = ansLinuxServiceDecode.decode("utf-8")
    ansLinuxService = open("ansible/playbooks/templates/nebula.service.j2", "w")
    ansLinuxService.write(ansLinuxServiceDecode)
    ansLinuxService.close()

    # Write Nebula config template out to file from base64 version
    # base64 of template to simplify storage
    ansNebulaConfig="IyBUaGlzIGlzIHRoZSBuZWJ1bGEgZXhhbXBsZSBjb25maWd1cmF0aW9uIGZpbGUuIFlvdSBtdXN0IGVkaXQsIGF0IGEgbWluaW11bSwgdGhlIHN0YXRpY19ob3N0X21hcCwgbGlnaHRob3VzZSwgYW5kIGZpcmV3YWxsIHNlY3Rpb25zCiMgU29tZSBvcHRpb25zIGluIHRoaXMgZmlsZSBhcmUgSFVQYWJsZSwgaW5jbHVkaW5nIHRoZSBwa2kgc2VjdGlvbi4gKEEgSFVQIHdpbGwgcmVsb2FkIGNyZWRlbnRpYWxzIGZyb20gZGlzayB3aXRob3V0IGFmZmVjdGluZyBleGlzdGluZyB0dW5uZWxzKQoKIyBQS0kgZGVmaW5lcyB0aGUgbG9jYXRpb24gb2YgY3JlZGVudGlhbHMgZm9yIHRoaXMgbm9kZS4gRWFjaCBvZiB0aGVzZSBjYW4gYWxzbyBiZSBpbmxpbmVkIGJ5IHVzaW5nIHRoZSB5YW1sICI6IHwiIHN5bnRheC4KcGtpOgogICMgVGhlIENBcyB0aGF0IGFyZSBhY2NlcHRlZCBieSB0aGlzIG5vZGUuIE11c3QgY29udGFpbiBvbmUgb3IgbW9yZSBjZXJ0aWZpY2F0ZXMgY3JlYXRlZCBieSAnbmVidWxhLWNlcnQgY2EnCiAgY2E6IC91c3IvbG9jYWwvYmluL25lYnVsYS9jYS5jcnQKICBjZXJ0OiAvdXNyL2xvY2FsL2Jpbi9uZWJ1bGEve3sgY2VydF9uYW1lIH19LmNydAogIGtleTogL3Vzci9sb2NhbC9iaW4vbmVidWxhL3t7IGNlcnRfbmFtZSB9fS5rZXkKICAjIGJsb2NrbGlzdCBpcyBhIGxpc3Qgb2YgY2VydGlmaWNhdGUgZmluZ2VycHJpbnRzIHRoYXQgd2Ugd2lsbCByZWZ1c2UgdG8gdGFsayB0bwogICNibG9ja2xpc3Q6CiAgIyAgLSBjOTlkNGU2NTA1MzNiOTIwNjFiMDk5MThlODM4YTVhMGE2YWFlZTIxZWVkMWQxMmZkOTM3NjgyODY1OTM2YzcyCiAgIyBkaXNjb25uZWN0X2ludmFsaWQgaXMgYSB0b2dnbGUgdG8gZm9yY2UgYSBjbGllbnQgdG8gYmUgZGlzY29ubmVjdGVkIGlmIHRoZSBjZXJ0aWZpY2F0ZSBpcyBleHBpcmVkIG9yIGludmFsaWQuCiAgI2Rpc2Nvbm5lY3RfaW52YWxpZDogZmFsc2UKCiMgVGhlIHN0YXRpYyBob3N0IG1hcCBkZWZpbmVzIGEgc2V0IG9mIGhvc3RzIHdpdGggZml4ZWQgSVAgYWRkcmVzc2VzIG9uIHRoZSBpbnRlcm5ldCAob3IgYW55IG5ldHdvcmspLgojIEEgaG9zdCBjYW4gaGF2ZSBtdWx0aXBsZSBmaXhlZCBJUCBhZGRyZXNzZXMgZGVmaW5lZCBoZXJlLCBhbmQgbmVidWxhIHdpbGwgdHJ5IGVhY2ggd2hlbiBlc3RhYmxpc2hpbmcgYSB0dW5uZWwuCiMgVGhlIHN5bnRheCBpczoKIyAgICJ7bmVidWxhIGlwfSI6IFsie3JvdXRhYmxlIGlwL2RucyBuYW1lfTp7cm91dGFibGUgcG9ydH0iXQojIEV4YW1wbGUsIGlmIHlvdXIgbGlnaHRob3VzZSBoYXMgdGhlIG5lYnVsYSBJUCBvZiAxOTIuMTY4LjEwMC4xIGFuZCBoYXMgdGhlIHJlYWwgaXAgYWRkcmVzcyBvZiAxMDAuNjQuMjIuMTEgYW5kIHJ1bnMgb24gcG9ydCA0MjQyOgpzdGF0aWNfaG9zdF9tYXA6CiAgInt7IGxpZ2h0aG91c2VfaXAgfX0iOiBbInt7IGxpZ2h0aG91c2VfaG9zdG5hbWUgfX06NDI0MiJdCgojIFRoZSBzdGF0aWNfbWFwIGNvbmZpZyBzdGFuemEgY2FuIGJlIHVzZWQgdG8gY29uZmlndXJlIGhvdyB0aGUgc3RhdGljX2hvc3RfbWFwIGJlaGF2ZXMuCiNzdGF0aWNfbWFwOgogICMgY2FkZW5jZSBkZXRlcm1pbmVzIGhvdyBmcmVxdWVudGx5IEROUyBpcyByZS1xdWVyaWVkIGZvciB1cGRhdGVkIElQIGFkZHJlc3NlcyB3aGVuIGEgc3RhdGljX2hvc3RfbWFwIGVudHJ5IGNvbnRhaW5zCiAgIyBhIEROUyBuYW1lLgogICNjYWRlbmNlOiAzMHMKCiAgIyBuZXR3b3JrIGRldGVybWluZXMgdGhlIHR5cGUgb2YgSVAgYWRkcmVzc2VzIHRvIGFzayB0aGUgRE5TIHNlcnZlciBmb3IuIFRoZSBkZWZhdWx0IGlzICJpcDQiIGJlY2F1c2Ugbm9kZXMgdHlwaWNhbGx5CiAgIyBkbyBub3Qga25vdyB0aGVpciBwdWJsaWMgSVB2NCBhZGRyZXNzLiBDb25uZWN0aW5nIHRvIHRoZSBMaWdodGhvdXNlIHZpYSBJUHY0IGFsbG93cyB0aGUgTGlnaHRob3VzZSB0byBkZXRlY3QgdGhlCiAgIyBwdWJsaWMgYWRkcmVzcy4gT3RoZXIgdmFsaWQgb3B0aW9ucyBhcmUgImlwNiIgYW5kICJpcCIgKHJldHVybnMgYm90aC4pCiAgI25ldHdvcms6IGlwNAoKICAjIGxvb2t1cF90aW1lb3V0IGlzIHRoZSBETlMgcXVlcnkgdGltZW91dC4KICAjbG9va3VwX3RpbWVvdXQ6IDI1MG1zCgpsaWdodGhvdXNlOgogICMgYW1fbGlnaHRob3VzZSBpcyB1c2VkIHRvIGVuYWJsZSBsaWdodGhvdXNlIGZ1bmN0aW9uYWxpdHkgZm9yIGEgbm9kZS4gVGhpcyBzaG91bGQgT05MWSBiZSB0cnVlIG9uIG5vZGVzCiAgIyB5b3UgaGF2ZSBjb25maWd1cmVkIHRvIGJlIGxpZ2h0aG91c2VzIGluIHlvdXIgbmV0d29yawogIGFtX2xpZ2h0aG91c2U6IGZhbHNlCiAgIyBzZXJ2ZV9kbnMgb3B0aW9uYWxseSBzdGFydHMgYSBkbnMgbGlzdGVuZXIgdGhhdCByZXNwb25kcyB0byB2YXJpb3VzIHF1ZXJpZXMgYW5kIGNhbiBldmVuIGJlCiAgIyBkZWxlZ2F0ZWQgdG8gZm9yIHJlc29sdXRpb24KICAjc2VydmVfZG5zOiBmYWxzZQogICNkbnM6CiAgICAjIFRoZSBETlMgaG9zdCBkZWZpbmVzIHRoZSBJUCB0byBiaW5kIHRoZSBkbnMgbGlzdGVuZXIgdG8uIFRoaXMgYWxzbyBhbGxvd3MgYmluZGluZyB0byB0aGUgbmVidWxhIG5vZGUgSVAuCiAgICAjaG9zdDogMC4wLjAuMAogICAgI3BvcnQ6IDUzCiAgIyBpbnRlcnZhbCBpcyB0aGUgbnVtYmVyIG9mIHNlY29uZHMgYmV0d2VlbiB1cGRhdGVzIGZyb20gdGhpcyBub2RlIHRvIGEgbGlnaHRob3VzZS4KICAjIGR1cmluZyB1cGRhdGVzLCBhIG5vZGUgc2VuZHMgaW5mb3JtYXRpb24gYWJvdXQgaXRzIGN1cnJlbnQgSVAgYWRkcmVzc2VzIHRvIGVhY2ggbm9kZS4KICBpbnRlcnZhbDogNjAKICAjIGhvc3RzIGlzIGEgbGlzdCBvZiBsaWdodGhvdXNlIGhvc3RzIHRoaXMgbm9kZSBzaG91bGQgcmVwb3J0IHRvIGFuZCBxdWVyeSBmcm9tCiAgIyBJTVBPUlRBTlQ6IFRISVMgU0hPVUxEIEJFIEVNUFRZIE9OIExJR0hUSE9VU0UgTk9ERVMKICAjIElNUE9SVEFOVDI6IFRISVMgU0hPVUxEIEJFIExJR0hUSE9VU0VTJyBORUJVTEEgSVBzLCBOT1QgTElHSFRIT1VTRVMnIFJFQUwgUk9VVEFCTEUgSVBzCiAgaG9zdHM6CiAgICAtICJ7eyBsaWdodGhvdXNlX2lwIH19IgoKICAjIHJlbW90ZV9hbGxvd19saXN0IGFsbG93cyB5b3UgdG8gY29udHJvbCBpcCByYW5nZXMgdGhhdCB0aGlzIG5vZGUgd2lsbAogICMgY29uc2lkZXIgd2hlbiBoYW5kc2hha2luZyB0byBhbm90aGVyIG5vZGUuIEJ5IGRlZmF1bHQsIGFueSByZW1vdGUgSVBzIGFyZQogICMgYWxsb3dlZC4gWW91IGNhbiBwcm92aWRlIENJRFJzIGhlcmUgd2l0aCBgdHJ1ZWAgdG8gYWxsb3cgYW5kIGBmYWxzZWAgdG8KICAjIGRlbnkuIFRoZSBtb3N0IHNwZWNpZmljIENJRFIgcnVsZSBhcHBsaWVzIHRvIGVhY2ggcmVtb3RlLiBJZiBhbGwgcnVsZXMgYXJlCiAgIyAiYWxsb3ciLCB0aGUgZGVmYXVsdCB3aWxsIGJlICJkZW55IiwgYW5kIHZpY2UtdmVyc2EuIElmIGJvdGggImFsbG93IiBhbmQKICAjICJkZW55IiBJUHY0IHJ1bGVzIGFyZSBwcmVzZW50LCB0aGVuIHlvdSBNVVNUIHNldCBhIHJ1bGUgZm9yICIwLjAuMC4wLzAiIGFzCiAgIyB0aGUgZGVmYXVsdC4gU2ltaWxhcmx5IGlmIGJvdGggImFsbG93IiBhbmQgImRlbnkiIElQdjYgcnVsZXMgYXJlIHByZXNlbnQsCiAgIyB0aGVuIHlvdSBNVVNUIHNldCBhIHJ1bGUgZm9yICI6Oi8wIiBhcyB0aGUgZGVmYXVsdC4KICAjcmVtb3RlX2FsbG93X2xpc3Q6CiAgICAjIEV4YW1wbGUgdG8gYmxvY2sgSVBzIGZyb20gdGhpcyBzdWJuZXQgZnJvbSBiZWluZyB1c2VkIGZvciByZW1vdGUgSVBzLgogICAgIyIxNzIuMTYuMC4wLzEyIjogZmFsc2UKCiAgICAjIEEgbW9yZSBjb21wbGljYXRlZCBleGFtcGxlLCBhbGxvdyBwdWJsaWMgSVBzIGJ1dCBvbmx5IHByaXZhdGUgSVBzIGZyb20gYSBzcGVjaWZpYyBzdWJuZXQKICAgICMiMC4wLjAuMC8wIjogdHJ1ZQogICAgIyIxMC4wLjAuMC84IjogZmFsc2UKICAgICMiMTAuNDIuNDIuMC8yNCI6IHRydWUKCiAgIyBFWFBFUklNRU5UQUw6IFRoaXMgb3B0aW9uIG1heSBjaGFuZ2Ugb3IgZGlzYXBwZWFyIGluIHRoZSBmdXR1cmUuCiAgIyBPcHRpb25hbGx5IGFsbG93cyB0aGUgZGVmaW5pdGlvbiBvZiByZW1vdGVfYWxsb3dfbGlzdCBibG9ja3MKICAjIHNwZWNpZmljIHRvIGFuIGluc2lkZSBWUE4gSVAgQ0lEUi4KICAjcmVtb3RlX2FsbG93X3JhbmdlczoKICAgICMgVGhpcyBydWxlIHdvdWxkIG9ubHkgYWxsb3cgb25seSBwcml2YXRlIElQcyBmb3IgdGhpcyBWUE4gcmFuZ2UKICAgICMiMTAuNDIuNDIuMC8yNCI6CiAgICAgICMiMTkyLjE2OC4wLjAvMTYiOiB0cnVlCgogICMgbG9jYWxfYWxsb3dfbGlzdCBhbGxvd3MgeW91IHRvIGZpbHRlciB3aGljaCBsb2NhbCBJUCBhZGRyZXNzZXMgd2UgYWR2ZXJ0aXNlCiAgIyB0byB0aGUgbGlnaHRob3VzZXMuIFRoaXMgdXNlcyB0aGUgc2FtZSBsb2dpYyBhcyBgcmVtb3RlX2FsbG93X2xpc3RgLCBidXQKICAjIGFkZGl0aW9uYWxseSwgeW91IGNhbiBzcGVjaWZ5IGFuIGBpbnRlcmZhY2VzYCBtYXAgb2YgcmVndWxhciBleHByZXNzaW9ucwogICMgdG8gbWF0Y2ggYWdhaW5zdCBpbnRlcmZhY2UgbmFtZXMuIFRoZSByZWdleHAgbXVzdCBtYXRjaCB0aGUgZW50aXJlIG5hbWUuCiAgIyBBbGwgaW50ZXJmYWNlIHJ1bGVzIG11c3QgYmUgZWl0aGVyIHRydWUgb3IgZmFsc2UgKGFuZCB0aGUgZGVmYXVsdCB3aWxsIGJlCiAgIyB0aGUgaW52ZXJzZSkuIENJRFIgcnVsZXMgYXJlIG1hdGNoZWQgYWZ0ZXIgaW50ZXJmYWNlIG5hbWUgcnVsZXMuCiAgIyBEZWZhdWx0IGlzIGFsbCBsb2NhbCBJUCBhZGRyZXNzZXMuCiAgI2xvY2FsX2FsbG93X2xpc3Q6CiAgICAjIEV4YW1wbGUgdG8gYmxvY2sgdHVuMCBhbmQgYWxsIGRvY2tlciBpbnRlcmZhY2VzLgogICAgI2ludGVyZmFjZXM6CiAgICAgICN0dW4wOiBmYWxzZQogICAgICAjJ2RvY2tlci4qJzogZmFsc2UKICAgICMgRXhhbXBsZSB0byBvbmx5IGFkdmVydGlzZSB0aGlzIHN1Ym5ldCB0byB0aGUgbGlnaHRob3VzZS4KICAgICMiMTAuMC4wLjAvOCI6IHRydWUKCiAgIyBhZHZlcnRpc2VfYWRkcnMgYXJlIHJvdXRhYmxlIGFkZHJlc3NlcyB0aGF0IHdpbGwgYmUgaW5jbHVkZWQgYWxvbmcgd2l0aCBkaXNjb3ZlcmVkIGFkZHJlc3NlcyB0byByZXBvcnQgdG8gdGhlCiAgIyBsaWdodGhvdXNlLCB0aGUgZm9ybWF0IGlzICJpcDpwb3J0Ii4gYHBvcnRgIGNhbiBiZSBgMGAsIGluIHdoaWNoIGNhc2UgdGhlIGFjdHVhbCBsaXN0ZW5pbmcgcG9ydCB3aWxsIGJlIHVzZWQgaW4gaXRzCiAgIyBwbGFjZSwgdXNlZnVsIGlmIGBsaXN0ZW4ucG9ydGAgaXMgc2V0IHRvIDAuCiAgIyBUaGlzIG9wdGlvbiBpcyBtYWlubHkgdXNlZnVsIHdoZW4gdGhlcmUgYXJlIHN0YXRpYyBpcCBhZGRyZXNzZXMgdGhlIGhvc3QgY2FuIGJlIHJlYWNoZWQgYXQgdGhhdCBuZWJ1bGEgY2FuIG5vdAogICMgdHlwaWNhbGx5IGRpc2NvdmVyIG9uIGl0cyBvd24uIEV4YW1wbGVzIGJlaW5nIHBvcnQgZm9yd2FyZGluZyBvciBtdWx0aXBsZSBwYXRocyB0byB0aGUgaW50ZXJuZXQuCiAgI2FkdmVydGlzZV9hZGRyczoKICAgICMtICIxLjEuMS4xOjQyNDIiCiAgICAjLSAiMS4yLjMuNDowIiAjIHBvcnQgd2lsbCBiZSByZXBsYWNlZCB3aXRoIHRoZSByZWFsIGxpc3RlbmluZyBwb3J0CgogICMgRVhQRVJJTUVOVEFMOiBUaGlzIG9wdGlvbiBtYXkgY2hhbmdlIG9yIGRpc2FwcGVhciBpbiB0aGUgZnV0dXJlLgogICMgVGhpcyBzZXR0aW5nIGFsbG93cyB1cyB0byAiZ3Vlc3MiIHdoYXQgdGhlIHJlbW90ZSBtaWdodCBiZSBmb3IgYSBob3N0CiAgIyB3aGlsZSB3ZSB3YWl0IGZvciB0aGUgbGlnaHRob3VzZSByZXNwb25zZS4KICAjY2FsY3VsYXRlZF9yZW1vdGVzOgogICAgIyBGb3IgYW55IE5lYnVsYSBJUHMgaW4gMTAuMC4xMC4wLzI0LCB0aGlzIHdpbGwgYXBwbHkgdGhlIG1hc2sgYW5kIGFkZAogICAgIyB0aGUgY2FsY3VsYXRlZCBJUCBhcyBhbiBpbml0aWFsIHJlbW90ZSAod2hpbGUgd2Ugd2FpdCBmb3IgdGhlIHJlc3BvbnNlCiAgICAjIGZyb20gdGhlIGxpZ2h0aG91c2UpLiBCb3RoIENJRFJzIG11c3QgaGF2ZSB0aGUgc2FtZSBtYXNrIHNpemUuCiAgICAjIEZvciBleGFtcGxlLCBOZWJ1bGEgSVAgMTAuMC4xMC4xMjMgd2lsbCBoYXZlIGEgY2FsY3VsYXRlZCByZW1vdGUgb2YKICAgICMgMTkyLjE2OC4xLjEyMwogICAgIzEwLjAuMTAuMC8yNDoKICAgICAgIy0gbWFzazogMTkyLjE2OC4xLjAvMjQKICAgICAgIyAgcG9ydDogNDI0MgoKIyBQb3J0IE5lYnVsYSB3aWxsIGJlIGxpc3RlbmluZyBvbi4gVGhlIGRlZmF1bHQgaGVyZSBpcyA0MjQyLiBGb3IgYSBsaWdodGhvdXNlIG5vZGUsIHRoZSBwb3J0IHNob3VsZCBiZSBkZWZpbmVkLAojIGhvd2V2ZXIgdXNpbmcgcG9ydCAwIHdpbGwgZHluYW1pY2FsbHkgYXNzaWduIGEgcG9ydCBhbmQgaXMgcmVjb21tZW5kZWQgZm9yIHJvYW1pbmcgbm9kZXMuCmxpc3RlbjoKICAjIFRvIGxpc3RlbiBvbiBib3RoIGFueSBpcHY0IGFuZCBpcHY2IHVzZSAiOjoiCiAgaG9zdDogMC4wLjAuMAogIHBvcnQ6IDAKICAjIFNldHMgdGhlIG1heCBudW1iZXIgb2YgcGFja2V0cyB0byBwdWxsIGZyb20gdGhlIGtlcm5lbCBmb3IgZWFjaCBzeXNjYWxsICh1bmRlciBzeXN0ZW1zIHRoYXQgc3VwcG9ydCByZWN2bW1zZykKICAjIGRlZmF1bHQgaXMgNjQsIGRvZXMgbm90IHN1cHBvcnQgcmVsb2FkCiAgI2JhdGNoOiA2NAogICMgQ29uZmlndXJlIHNvY2tldCBidWZmZXJzIGZvciB0aGUgdWRwIHNpZGUgKG91dHNpZGUpLCBsZWF2ZSB1bnNldCB0byB1c2UgdGhlIHN5c3RlbSBkZWZhdWx0cy4gVmFsdWVzIHdpbGwgYmUgZG91YmxlZCBieSB0aGUga2VybmVsCiAgIyBEZWZhdWx0IGlzIG5ldC5jb3JlLnJtZW1fZGVmYXVsdCBhbmQgbmV0LmNvcmUud21lbV9kZWZhdWx0ICgvcHJvYy9zeXMvbmV0L2NvcmUvcm1lbV9kZWZhdWx0IGFuZCAvcHJvYy9zeXMvbmV0L2NvcmUvcm1lbV9kZWZhdWx0KQogICMgTWF4aW11bSBpcyBsaW1pdGVkIGJ5IG1lbW9yeSBpbiB0aGUgc3lzdGVtLCBTT19SQ1ZCVUZGT1JDRSBhbmQgU09fU05EQlVGRk9SQ0UgaXMgdXNlZCB0byBhdm9pZCBoYXZpbmcgdG8gcmFpc2UgdGhlIHN5c3RlbSB3aWRlCiAgIyBtYXgsIG5ldC5jb3JlLnJtZW1fbWF4IGFuZCBuZXQuY29yZS53bWVtX21heAogICNyZWFkX2J1ZmZlcjogMTA0ODU3NjAKICAjd3JpdGVfYnVmZmVyOiAxMDQ4NTc2MAogICMgQnkgZGVmYXVsdCwgTmVidWxhIHJlcGxpZXMgdG8gcGFja2V0cyBpdCBoYXMgbm8gdHVubmVsIGZvciB3aXRoIGEgInJlY3ZfZXJyb3IiIHBhY2tldC4gVGhpcyBwYWNrZXQgaGVscHMgc3BlZWQgdXAgcmVjb25uZWN0aW9uCiAgIyBpbiB0aGUgY2FzZSB0aGF0IE5lYnVsYSBvbiBlaXRoZXIgc2lkZSBkaWQgbm90IHNodXQgZG93biBjbGVhbmx5LiBUaGlzIHJlc3BvbnNlIGNhbiBiZSBhYnVzZWQgYXMgYSB3YXkgdG8gZGlzY292ZXIgaWYgTmVidWxhIGlzIHJ1bm5pbmcKICAjIG9uIGEgaG9zdCB0aG91Z2guIFRoaXMgb3B0aW9uIGxldHMgeW91IGNvbmZpZ3VyZSBpZiB5b3Ugd2FudCB0byBzZW5kICJyZWN2X2Vycm9yIiBwYWNrZXRzIGFsd2F5cywgbmV2ZXIsIG9yIG9ubHkgdG8gcHJpdmF0ZSBuZXR3b3JrIHJlbW90ZXMuCiAgIyB2YWxpZCB2YWx1ZXM6IGFsd2F5cywgbmV2ZXIsIHByaXZhdGUKICAjIFRoaXMgc2V0dGluZyBpcyByZWxvYWRhYmxlLgogICNzZW5kX3JlY3ZfZXJyb3I6IGFsd2F5cwoKIyBSb3V0aW5lcyBpcyB0aGUgbnVtYmVyIG9mIHRocmVhZCBwYWlycyB0byBydW4gdGhhdCBjb25zdW1lIGZyb20gdGhlIHR1biBhbmQgVURQIHF1ZXVlcy4KIyBDdXJyZW50bHksIHRoaXMgZGVmYXVsdHMgdG8gMSB3aGljaCBtZWFucyB3ZSBoYXZlIDEgdHVuIHF1ZXVlIHJlYWRlciBhbmQgMQojIFVEUCBxdWV1ZSByZWFkZXIuIFNldHRpbmcgdGhpcyBhYm92ZSBvbmUgd2lsbCBzZXQgSUZGX01VTFRJX1FVRVVFIG9uIHRoZSB0dW4KIyBkZXZpY2UgYW5kIFNPX1JFVVNFUE9SVCBvbiB0aGUgVURQIHNvY2tldCB0byBhbGxvdyBtdWx0aXBsZSBxdWV1ZXMuCiMgVGhpcyBvcHRpb24gaXMgb25seSBzdXBwb3J0ZWQgb24gTGludXguCiNyb3V0aW5lczogMQoKcHVuY2h5OgogICMgQ29udGludWVzIHRvIHB1bmNoIGluYm91bmQvb3V0Ym91bmQgYXQgYSByZWd1bGFyIGludGVydmFsIHRvIGF2b2lkIGV4cGlyYXRpb24gb2YgZmlyZXdhbGwgbmF0IG1hcHBpbmdzCiAgcHVuY2g6IHRydWUKCiAgIyByZXNwb25kIG1lYW5zIHRoYXQgYSBub2RlIHlvdSBhcmUgdHJ5aW5nIHRvIHJlYWNoIHdpbGwgY29ubmVjdCBiYWNrIG91dCB0byB5b3UgaWYgeW91ciBob2xlIHB1bmNoaW5nIGZhaWxzCiAgIyB0aGlzIGlzIGV4dHJlbWVseSB1c2VmdWwgaWYgb25lIG5vZGUgaXMgYmVoaW5kIGEgZGlmZmljdWx0IG5hdCwgc3VjaCBhcyBhIHN5bW1ldHJpYyBOQVQKICAjIERlZmF1bHQgaXMgZmFsc2UKICAjcmVzcG9uZDogdHJ1ZQoKICAjIGRlbGF5cyBhIHB1bmNoIHJlc3BvbnNlIGZvciBtaXNiZWhhdmluZyBOQVRzLCBkZWZhdWx0IGlzIDEgc2Vjb25kLgogICNkZWxheTogMXMKCiAgIyBzZXQgdGhlIGRlbGF5IGJlZm9yZSBhdHRlbXB0aW5nIHB1bmNoeS5yZXNwb25kLiBEZWZhdWx0IGlzIDUgc2Vjb25kcy4gcmVzcG9uZCBtdXN0IGJlIHRydWUgdG8gdGFrZSBlZmZlY3QuCiAgI3Jlc3BvbmRfZGVsYXk6IDVzCgojIENpcGhlciBhbGxvd3MgeW91IHRvIGNob29zZSBiZXR3ZWVuIHRoZSBhdmFpbGFibGUgY2lwaGVycyBmb3IgeW91ciBuZXR3b3JrLiBPcHRpb25zIGFyZSBjaGFjaGFwb2x5IG9yIGFlcwojIElNUE9SVEFOVDogdGhpcyB2YWx1ZSBtdXN0IGJlIGlkZW50aWNhbCBvbiBBTEwgTk9ERVMvTElHSFRIT1VTRVMuIFdlIGRvIG5vdC93aWxsIG5vdCBzdXBwb3J0IHVzZSBvZiBkaWZmZXJlbnQgY2lwaGVycyBzaW11bHRhbmVvdXNseSEKI2NpcGhlcjogYWVzCgojIFByZWZlcnJlZCByYW5nZXMgaXMgdXNlZCB0byBkZWZpbmUgYSBoaW50IGFib3V0IHRoZSBsb2NhbCBuZXR3b3JrIHJhbmdlcywgd2hpY2ggc3BlZWRzIHVwIGRpc2NvdmVyaW5nIHRoZSBmYXN0ZXN0CiMgcGF0aCB0byBhIG5ldHdvcmsgYWRqYWNlbnQgbmVidWxhIG5vZGUuCiMgTk9URTogdGhlIHByZXZpb3VzIG9wdGlvbiAibG9jYWxfcmFuZ2UiIG9ubHkgYWxsb3dlZCBkZWZpbml0aW9uIG9mIGEgc2luZ2xlIHJhbmdlCiMgYW5kIGhhcyBiZWVuIGRlcHJlY2F0ZWQgZm9yICJwcmVmZXJyZWRfcmFuZ2VzIgojcHJlZmVycmVkX3JhbmdlczogWyIxNzIuMTYuMC4wLzI0Il0KCiMgc3NoZCBjYW4gZXhwb3NlIGluZm9ybWF0aW9uYWwgYW5kIGFkbWluaXN0cmF0aXZlIGZ1bmN0aW9ucyB2aWEgc3NoIHRoaXMgaXMgYQojc3NoZDoKICAjIFRvZ2dsZXMgdGhlIGZlYXR1cmUKICAjZW5hYmxlZDogdHJ1ZQogICMgSG9zdCBhbmQgcG9ydCB0byBsaXN0ZW4gb24sIHBvcnQgMjIgaXMgbm90IGFsbG93ZWQgZm9yIHlvdXIgc2FmZXR5CiAgI2xpc3RlbjogMTI3LjAuMC4xOjIyMjIKICAjIEEgZmlsZSBjb250YWluaW5nIHRoZSBzc2ggaG9zdCBwcml2YXRlIGtleSB0byB1c2UKICAjIEEgZGVjZW50IHdheSB0byBnZW5lcmF0ZSBvbmU6IHNzaC1rZXlnZW4gLXQgZWQyNTUxOSAtZiBzc2hfaG9zdF9lZDI1NTE5X2tleSAtTiAiIiA8IC9kZXYvbnVsbAogICNob3N0X2tleTogLi9zc2hfaG9zdF9lZDI1NTE5X2tleQogICMgQSBmaWxlIGNvbnRhaW5pbmcgYSBsaXN0IG9mIGF1dGhvcml6ZWQgcHVibGljIGtleXMKICAjYXV0aG9yaXplZF91c2VyczoKICAgICMtIHVzZXI6IHN0ZWVlZXZlCiAgICAgICMga2V5cyBjYW4gYmUgYW4gYXJyYXkgb2Ygc3RyaW5ncyBvciBzaW5nbGUgc3RyaW5nCiAgICAgICNrZXlzOgogICAgICAgICMtICJzc2ggcHVibGljIGtleSBzdHJpbmciCgojIEVYUEVSSU1FTlRBTDogcmVsYXkgc3VwcG9ydCBmb3IgbmV0d29ya3MgdGhhdCBjYW4ndCBlc3RhYmxpc2ggZGlyZWN0IGNvbm5lY3Rpb25zLgpyZWxheToKICAjIFJlbGF5cyBhcmUgYSBsaXN0IG9mIE5lYnVsYSBJUCdzIHRoYXQgcGVlcnMgY2FuIHVzZSB0byByZWxheSBwYWNrZXRzIHRvIG1lLgogICMgSVBzIGluIHRoaXMgbGlzdCBtdXN0IGhhdmUgYW1fcmVsYXkgc2V0IHRvIHRydWUgaW4gdGhlaXIgY29uZmlncywgb3RoZXJ3aXNlCiAgIyB0aGV5IHdpbGwgcmVqZWN0IHJlbGF5IHJlcXVlc3RzLgogICNyZWxheXM6CiAgICAjLSAxOTIuMTY4LjEwMC4xCiAgICAjLSA8b3RoZXIgTmVidWxhIFZQTiBJUHMgb2YgaG9zdHMgdXNlZCBhcyByZWxheXMgdG8gYWNjZXNzIG1lPgogICMgU2V0IGFtX3JlbGF5IHRvIHRydWUgdG8gcGVybWl0IG90aGVyIGhvc3RzIHRvIGxpc3QgbXkgSVAgaW4gdGhlaXIgcmVsYXlzIGNvbmZpZy4gRGVmYXVsdCBmYWxzZS4KICBhbV9yZWxheTogZmFsc2UKICAjIFNldCB1c2VfcmVsYXlzIHRvIGZhbHNlIHRvIHByZXZlbnQgdGhpcyBpbnN0YW5jZSBmcm9tIGF0dGVtcHRpbmcgdG8gZXN0YWJsaXNoIGNvbm5lY3Rpb25zIHRocm91Z2ggcmVsYXlzLgogICMgZGVmYXVsdCB0cnVlCiAgdXNlX3JlbGF5czogdHJ1ZQoKIyBDb25maWd1cmUgdGhlIHByaXZhdGUgaW50ZXJmYWNlLiBOb3RlOiBhZGRyIGlzIGJha2VkIGludG8gdGhlIG5lYnVsYSBjZXJ0aWZpY2F0ZQp0dW46CiAgIyBXaGVuIHR1biBpcyBkaXNhYmxlZCwgYSBsaWdodGhvdXNlIGNhbiBiZSBzdGFydGVkIHdpdGhvdXQgYSBsb2NhbCB0dW4gaW50ZXJmYWNlIChhbmQgdGhlcmVmb3JlIHdpdGhvdXQgcm9vdCkKICBkaXNhYmxlZDogZmFsc2UKICAjIE5hbWUgb2YgdGhlIGRldmljZS4gSWYgbm90IHNldCwgYSBkZWZhdWx0IHdpbGwgYmUgY2hvc2VuIGJ5IHRoZSBPUy4KICAjIEZvciBtYWNPUzogaWYgc2V0LCBtdXN0IGJlIGluIHRoZSBmb3JtIGB1dHVuWzAtOV0rYC4KICBkZXY6IG5lYnVsYTEKICAjIFRvZ2dsZXMgZm9yd2FyZGluZyBvZiBsb2NhbCBicm9hZGNhc3QgcGFja2V0cywgdGhlIGFkZHJlc3Mgb2Ygd2hpY2ggZGVwZW5kcyBvbiB0aGUgaXAvbWFzayBlbmNvZGVkIGluIHBraS5jZXJ0CiAgZHJvcF9sb2NhbF9icm9hZGNhc3Q6IGZhbHNlCiAgIyBUb2dnbGVzIGZvcndhcmRpbmcgb2YgbXVsdGljYXN0IHBhY2tldHMKICBkcm9wX211bHRpY2FzdDogZmFsc2UKICAjIFNldHMgdGhlIHRyYW5zbWl0IHF1ZXVlIGxlbmd0aCwgaWYgeW91IG5vdGljZSBsb3RzIG9mIHRyYW5zbWl0IGRyb3BzIG9uIHRoZSB0dW4gaXQgbWF5IGhlbHAgdG8gcmFpc2UgdGhpcyBudW1iZXIuIERlZmF1bHQgaXMgNTAwCiAgdHhfcXVldWU6IDUwMAogICMgRGVmYXVsdCBNVFUgZm9yIGV2ZXJ5IHBhY2tldCwgc2FmZSBzZXR0aW5nIGlzIChhbmQgdGhlIGRlZmF1bHQpIDEzMDAgZm9yIGludGVybmV0IGJhc2VkIHRyYWZmaWMKICBtdHU6IDEzMDAKCiAgIyBSb3V0ZSBiYXNlZCBNVFUgb3ZlcnJpZGVzLCB5b3UgaGF2ZSBrbm93biB2cG4gaXAgcGF0aHMgdGhhdCBjYW4gc3VwcG9ydCBsYXJnZXIgTVRVcyB5b3UgY2FuIGluY3JlYXNlL2RlY3JlYXNlIHRoZW0gaGVyZQogIHJvdXRlczoKICAgICMtIG10dTogODgwMAogICAgIyAgcm91dGU6IDEwLjAuMC4wLzE2CgogICMgVW5zYWZlIHJvdXRlcyBhbGxvd3MgeW91IHRvIHJvdXRlIHRyYWZmaWMgb3ZlciBuZWJ1bGEgdG8gbm9uLW5lYnVsYSBub2RlcwogICMgVW5zYWZlIHJvdXRlcyBzaG91bGQgYmUgYXZvaWRlZCB1bmxlc3MgeW91IGhhdmUgaG9zdHMvc2VydmljZXMgdGhhdCBjYW5ub3QgcnVuIG5lYnVsYQogICMgTk9URTogVGhlIG5lYnVsYSBjZXJ0aWZpY2F0ZSBvZiB0aGUgInZpYSIgbm9kZSAqTVVTVCogaGF2ZSB0aGUgInJvdXRlIiBkZWZpbmVkIGFzIGEgc3VibmV0IGluIGl0cyBjZXJ0aWZpY2F0ZQogICMgYG10dWA6IHdpbGwgZGVmYXVsdCB0byB0dW4gbXR1IGlmIHRoaXMgb3B0aW9uIGlzIG5vdCBzcGVjaWZpZWQKICAjIGBtZXRyaWNgOiB3aWxsIGRlZmF1bHQgdG8gMCBpZiB0aGlzIG9wdGlvbiBpcyBub3Qgc3BlY2lmaWVkCiAgIyBgaW5zdGFsbGA6IHdpbGwgZGVmYXVsdCB0byB0cnVlLCBjb250cm9scyB3aGV0aGVyIHRoaXMgcm91dGUgaXMgaW5zdGFsbGVkIGluIHRoZSBzeXN0ZW1zIHJvdXRpbmcgdGFibGUuCiAgdW5zYWZlX3JvdXRlczoKICAgICMtIHJvdXRlOiAxNzIuMTYuMS4wLzI0CiAgICAjICB2aWE6IDE5Mi4xNjguMTAwLjk5CiAgICAjICBtdHU6IDEzMDAKICAgICMgIG1ldHJpYzogMTAwCiAgICAjICBpbnN0YWxsOiB0cnVlCgogICMgT24gbGludXggb25seSwgc2V0IHRvIHRydWUgdG8gbWFuYWdlIHVuc2FmZSByb3V0ZXMgZGlyZWN0bHkgb24gdGhlIHN5c3RlbSByb3V0ZSB0YWJsZSB3aXRoIGdhdGV3YXkgcm91dGVzIGluc3RlYWQgb2YKICAjIGluIG5lYnVsYSBjb25maWd1cmF0aW9uIGZpbGVzLiBEZWZhdWx0IGZhbHNlLCBub3QgcmVsb2FkYWJsZS4KICAjdXNlX3N5c3RlbV9yb3V0ZV90YWJsZTogZmFsc2UKCiMgVE9ETwojIENvbmZpZ3VyZSBsb2dnaW5nIGxldmVsCmxvZ2dpbmc6CiAgIyBwYW5pYywgZmF0YWwsIGVycm9yLCB3YXJuaW5nLCBpbmZvLCBvciBkZWJ1Zy4gRGVmYXVsdCBpcyBpbmZvCiAgbGV2ZWw6IGluZm8KICAjIGpzb24gb3IgdGV4dCBmb3JtYXRzIGN1cnJlbnRseSBhdmFpbGFibGUuIERlZmF1bHQgaXMgdGV4dAogIGZvcm1hdDogdGV4dAogICMgRGlzYWJsZSB0aW1lc3RhbXAgbG9nZ2luZy4gdXNlZnVsIHdoZW4gb3V0cHV0IGlzIHJlZGlyZWN0ZWQgdG8gbG9nZ2luZyBzeXN0ZW0gdGhhdCBhbHJlYWR5IGFkZHMgdGltZXN0YW1wcy4gRGVmYXVsdCBpcyBmYWxzZQogICNkaXNhYmxlX3RpbWVzdGFtcDogdHJ1ZQogICMgdGltZXN0YW1wIGZvcm1hdCBpcyBzcGVjaWZpZWQgaW4gR28gdGltZSBmb3JtYXQsIHNlZToKICAjICAgICBodHRwczovL2dvbGFuZy5vcmcvcGtnL3RpbWUvI3BrZy1jb25zdGFudHMKICAjIGRlZmF1bHQgd2hlbiBgZm9ybWF0OiBqc29uYDogIjIwMDYtMDEtMDJUMTU6MDQ6MDVaMDc6MDAiIChSRkMzMzM5KQogICMgZGVmYXVsdCB3aGVuIGBmb3JtYXQ6IHRleHRgOgogICMgICAgIHdoZW4gVFRZIGF0dGFjaGVkOiBzZWNvbmRzIHNpbmNlIGJlZ2lubmluZyBvZiBleGVjdXRpb24KICAjICAgICBvdGhlcndpc2U6ICIyMDA2LTAxLTAyVDE1OjA0OjA1WjA3OjAwIiAoUkZDMzMzOSkKICAjIEFzIGFuIGV4YW1wbGUsIHRvIGxvZyBhcyBSRkMzMzM5IHdpdGggbWlsbGlzZWNvbmQgcHJlY2lzaW9uLCBzZXQgdG86CiAgI3RpbWVzdGFtcF9mb3JtYXQ6ICIyMDA2LTAxLTAyVDE1OjA0OjA1LjAwMFowNzowMCIKCiNzdGF0czoKICAjdHlwZTogZ3JhcGhpdGUKICAjcHJlZml4OiBuZWJ1bGEKICAjcHJvdG9jb2w6IHRjcAogICNob3N0OiAxMjcuMC4wLjE6OTk5OQogICNpbnRlcnZhbDogMTBzCgogICN0eXBlOiBwcm9tZXRoZXVzCiAgI2xpc3RlbjogMTI3LjAuMC4xOjgwODAKICAjcGF0aDogL21ldHJpY3MKICAjbmFtZXNwYWNlOiBwcm9tZXRoZXVzbnMKICAjc3Vic3lzdGVtOiBuZWJ1bGEKICAjaW50ZXJ2YWw6IDEwcwoKICAjIGVuYWJsZXMgY291bnRlciBtZXRyaWNzIGZvciBtZXRhIHBhY2tldHMKICAjICAgZS5nLjogYG1lc3NhZ2VzLnR4LmhhbmRzaGFrZWAKICAjIE5PVEU6IGBtZXNzYWdlLnt0eCxyeH0ucmVjdl9lcnJvcmAgaXMgYWx3YXlzIGVtaXR0ZWQKICAjbWVzc2FnZV9tZXRyaWNzOiBmYWxzZQoKICAjIGVuYWJsZXMgZGV0YWlsZWQgY291bnRlciBtZXRyaWNzIGZvciBsaWdodGhvdXNlIHBhY2tldHMKICAjICAgZS5nLjogYGxpZ2h0aG91c2UucnguSG9zdFF1ZXJ5YAogICNsaWdodGhvdXNlX21ldHJpY3M6IGZhbHNlCgojIEhhbmRzaGFrZSBNYW5hZ2VyIFNldHRpbmdzCiNoYW5kc2hha2VzOgogICMgSGFuZHNoYWtlcyBhcmUgc2VudCB0byBhbGwga25vd24gYWRkcmVzc2VzIGF0IGVhY2ggaW50ZXJ2YWwgd2l0aCBhIGxpbmVhciBiYWNrb2ZmLAogICMgV2FpdCB0cnlfaW50ZXJ2YWwgYWZ0ZXIgdGhlIDFzdCBhdHRlbXB0LCAyICogdHJ5X2ludGVydmFsIGFmdGVyIHRoZSAybmQsIGV0YywgdW50aWwgdGhlIGhhbmRzaGFrZSBpcyBvbGRlciB0aGFuIHRpbWVvdXQKICAjIEEgMTAwbXMgaW50ZXJ2YWwgd2l0aCB0aGUgZGVmYXVsdCAxMCByZXRyaWVzIHdpbGwgZ2l2ZSBhIGhhbmRzaGFrZSA1LjUgc2Vjb25kcyB0byByZXNvbHZlIGJlZm9yZSB0aW1pbmcgb3V0CiAgI3RyeV9pbnRlcnZhbDogMTAwbXMKICAjcmV0cmllczogMjAKICAjIHRyaWdnZXJfYnVmZmVyIGlzIHRoZSBzaXplIG9mIHRoZSBidWZmZXIgY2hhbm5lbCBmb3IgcXVpY2tseSBzZW5kaW5nIGhhbmRzaGFrZXMKICAjIGFmdGVyIHJlY2VpdmluZyB0aGUgcmVzcG9uc2UgZm9yIGxpZ2h0aG91c2UgcXVlcmllcwogICN0cmlnZ2VyX2J1ZmZlcjogNjQKCgojIE5lYnVsYSBzZWN1cml0eSBncm91cCBjb25maWd1cmF0aW9uCmZpcmV3YWxsOgogICMgQWN0aW9uIHRvIHRha2Ugd2hlbiBhIHBhY2tldCBpcyBub3QgYWxsb3dlZCBieSB0aGUgZmlyZXdhbGwgcnVsZXMuCiAgIyBDYW4gYmUgb25lIG9mOgogICMgICBgZHJvcGAgKGRlZmF1bHQpOiBzaWxlbnRseSBkcm9wIHRoZSBwYWNrZXQuCiAgIyAgIGByZWplY3RgOiBzZW5kIGEgcmVqZWN0IHJlcGx5LgogICMgICAgIC0gRm9yIFRDUCwgdGhpcyB3aWxsIGJlIGEgUlNUICJDb25uZWN0aW9uIFJlc2V0IiBwYWNrZXQuCiAgIyAgICAgLSBGb3Igb3RoZXIgcHJvdG9jb2xzLCB0aGlzIHdpbGwgYmUgYW4gSUNNUCBwb3J0IHVucmVhY2hhYmxlIHBhY2tldC4KICBvdXRib3VuZF9hY3Rpb246IGRyb3AKICBpbmJvdW5kX2FjdGlvbjogZHJvcAoKICBjb25udHJhY2s6CiAgICB0Y3BfdGltZW91dDogMTJtCiAgICB1ZHBfdGltZW91dDogM20KICAgIGRlZmF1bHRfdGltZW91dDogMTBtCgogICMgVGhlIGZpcmV3YWxsIGlzIGRlZmF1bHQgZGVueS4gVGhlcmUgaXMgbm8gd2F5IHRvIHdyaXRlIGEgZGVueSBydWxlLgogICMgUnVsZXMgYXJlIGNvbXByaXNlZCBvZiBhIHByb3RvY29sLCBwb3J0LCBhbmQgb25lIG9yIG1vcmUgb2YgaG9zdCwgZ3JvdXAsIG9yIENJRFIKICAjIExvZ2ljYWwgZXZhbHVhdGlvbiBpcyByb3VnaGx5OiBwb3J0IEFORCBwcm90byBBTkQgKGNhX3NoYSBPUiBjYV9uYW1lKSBBTkQgKGhvc3QgT1IgZ3JvdXAgT1IgZ3JvdXBzIE9SIGNpZHIpCiAgIyAtIHBvcnQ6IFRha2VzIGAwYCBvciBgYW55YCBhcyBhbnksIGEgc2luZ2xlIG51bWJlciBgODBgLCBhIHJhbmdlIGAyMDAtOTAxYCwgb3IgYGZyYWdtZW50YCB0byBtYXRjaCBzZWNvbmQgYW5kIGZ1cnRoZXIgZnJhZ21lbnRzIG9mIGZyYWdtZW50ZWQgcGFja2V0cyAoc2luY2UgdGhlcmUgaXMgbm8gcG9ydCBhdmFpbGFibGUpLgogICMgICBjb2RlOiBzYW1lIGFzIHBvcnQgYnV0IG1ha2VzIG1vcmUgc2Vuc2Ugd2hlbiB0YWxraW5nIGFib3V0IElDTVAsIFRPRE86IHRoaXMgaXMgbm90IGN1cnJlbnRseSBpbXBsZW1lbnRlZCBpbiBhIHdheSB0aGF0IHdvcmtzLCB1c2UgYGFueWAKICAjICAgcHJvdG86IGBhbnlgLCBgdGNwYCwgYHVkcGAsIG9yIGBpY21wYAogICMgICBob3N0OiBgYW55YCBvciBhIGxpdGVyYWwgaG9zdG5hbWUsIGllIGB0ZXN0LWhvc3RgCiAgIyAgIGdyb3VwOiBgYW55YCBvciBhIGxpdGVyYWwgZ3JvdXAgbmFtZSwgaWUgYGRlZmF1bHQtZ3JvdXBgCiAgIyAgIGdyb3VwczogU2FtZSBhcyBncm91cCBidXQgYWNjZXB0cyBhIGxpc3Qgb2YgdmFsdWVzLiBNdWx0aXBsZSB2YWx1ZXMgYXJlIEFORCdkIHRvZ2V0aGVyIGFuZCBhIGNlcnRpZmljYXRlIHdvdWxkIGhhdmUgdG8gY29udGFpbiBhbGwgZ3JvdXBzIHRvIHBhc3MKICAjICAgY2lkcjogYSByZW1vdGUgQ0lEUiwgYDAuMC4wLjAvMGAgaXMgYW55LgogICMgICBsb2NhbF9jaWRyOiBhIGxvY2FsIENJRFIsIGAwLjAuMC4wLzBgIGlzIGFueS4gVGhpcyBjb3VsZCBiZSB1c2VkIHRvIGZpbHRlciBkZXN0aW5hdGlvbnMgd2hlbiB1c2luZyB1bnNhZmVfcm91dGVzLgogICMgICBjYV9uYW1lOiBBbiBpc3N1aW5nIENBIG5hbWUKICAjICAgY2Ffc2hhOiBBbiBpc3N1aW5nIENBIHNoYXN1bQoKICBvdXRib3VuZDoKICAgICMgQWxsb3cgYWxsIG91dGJvdW5kIHRyYWZmaWMgZnJvbSB0aGlzIG5vZGUKICAgIC0gcG9ydDogYW55CiAgICAgIHByb3RvOiBhbnkKICAgICAgaG9zdDogYW55CgogIGluYm91bmQ6CiAgICAjIEFsbG93IGljbXAgYmV0d2VlbiBhbnkgbmVidWxhIGhvc3RzCiAgICAtIHBvcnQ6IGFueQogICAgICBwcm90bzogaWNtcAogICAgICBob3N0OiBhbnkKCiAgICAjIEFsbG93IHNzaAogICAgLSBwb3J0OiAyMgogICAgICBwcm90bzogdGNwCiAgICAgIGhvc3Q6IGFueQoKICAgICMgQWxsb3cgdGNwLzQ0MyBmcm9tIGFueSBob3N0IHdpdGggQk9USCBsYXB0b3AgYW5kIGhvbWUgZ3JvdXAKICAgIC0gcG9ydDogNDQzCiAgICAgIHByb3RvOiB0Y3AKICAgICAgZ3JvdXBzOgogICAgICAgIC0gbGFwdG9wCiAgICAgICAgLSBob21l"
    ansNebulaConfigDecode = base64.b64decode(ansNebulaConfig)
    ansNebulaConfigDecode = ansNebulaConfigDecode.decode("utf-8")
    ansNebulaConfig = open("ansible/playbooks/templates/nebula.yml.j2", "w")
    ansNebulaConfig.write(ansNebulaConfigDecode)
    ansNebulaConfig.close()


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
            shutil.copyfile('./nebula', './ansible/playbooks/files/nebula')


# Display all clients in the DB
def listClients():
    if not os.path.exists(NEBMANDB):
        sys.exit("Database does not exist, exiting")
    else:
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
    print("5 - Generate Ansible inventory")
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
    elif menuChoice == '5':
        ansibleGen()
    elif menuChoice == '99':
        purgeCerts()
