"""
Check release version of Ubuntu.
Run apt list and parse the output to get a list of installed packages including the version number.
Create a list of the packages including the version number and the hostname of the machine.
Connect to the MSSQL DB. Get the connection string from the a file called /etc/UpdTrack/db.pwd.
If the table hostnames doesn't exist, create it.
If the table packages doesn't exist, create it.
Insert the hostname into the hostnames table. Change the release version of Ubuntu for the hostname if it is different.
Insert the release version of Ubuntu into the hostnames table.
Insert the hostname, package name including version number and current date and time into the packages table. Mark the package as installed.
If the hostname already exists in the hostnames table, don't insert it.
If the combination of hostname and package name already exist in the packages table, don't insert it.
If the hostname and package name including the package version don't exist in the list of packages, mark the package as uninstalled.
Install this script as a service to run every 15 minutes.
Run the service as root.
"""

import os
import sys
import subprocess
import pyodbc
import socket
import datetime

# Get the hostname of the machine
hostname = socket.gethostname()

# Get the current date and time
now = datetime.datetime.now()

# Get the current date and time in a format that MSSQL can use
now = now.strftime("%Y-%m-%d %H:%M:%S")

# Get the release version of Ubuntu
release = subprocess.check_output(['lsb_release', '-r']).decode('utf-8').split()[1]

# Get the output of the apt list command
apt_list = subprocess.check_output(['apt', 'list', '--installed'])

# Convert the output to a string
apt_list = apt_list.decode('utf-8')

# Split the output into a list of lines
apt_list = apt_list.splitlines()

# Create a list of packages
installed_packages = []

# Loop through the lines of the output
for line in apt_list:
    # Split the line into a list of words
    words = line.split()

    # If the line contains a package name and a version number
    if len(words) == 2:
        # Add the package name and version number to the list of packages
        installed_packages.append(words[0] + ' ' + words[1])

# Get the connection string from the file /etc/UpdTrack/db.pwd
with open('/etc/UpdTrack/db.pwd', 'r') as f:
    conn_str = f.read()

# Connect to the MSSQL DB
conn = pyodbc.connect(conn_str)

# Get a cursor
cursor = conn.cursor()

# If the table hostnames doesn't exist, create it use ID as the primary key
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='hostnames' AND xtype='U')
    CREATE TABLE hostnames (
        hostname VARCHAR(255) NOT NULL,
        release VARCHAR(255) NOT NULL,
        PRIMARY KEY (hostname)
    )
''')

# If the table packages doesn't exist, create it
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packages' AND xtype='U')
    CREATE TABLE packages (
        hostname VARCHAR(255) NOT NULL,
        package VARCHAR(255) NOT NULL,
        date DATETIME NOT NULL,
        installed BIT NOT NULL,
        PRIMARY KEY (hostname, package)
    )
''')

# Insert the hostname into the hostnames table
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM hostnames WHERE hostname = ?)
    INSERT INTO hostnames (hostname) VALUES (?)
''', hostname, hostname)

# Insert the release version of Ubuntu into the hostnames table
cursor.execute('''
    UPDATE hostnames SET release = ? WHERE hostname = ?
''', release, hostname)


# Insert every package in the installed_packages list into the packages table linking it to the hostname marking it as installed
for package in installed_packages:
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM packages WHERE hostname = ? AND package = ?)
        INSERT INTO packages (hostname, package, date, installed) VALUES (?, ?, ?, ?)
    ''', hostname, package, hostname, package, now, 1)

# Check if there are any packages in the packages table that are not in the installed_packages list and mark them as uninstalled updating the date
cursor.execute('''
    UPDATE packages SET date = ?, installed = ? WHERE hostname = ? AND package NOT IN (SELECT * FROM ?)
''', now, 0, hostname, installed_packages)

# Commit the changes
conn.commit()

# Close the connection
conn.close()