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

# Get the release version of Ubuntu with the lsb_release -a command from the description field
release = subprocess.check_output(['lsb_release', '-a']).decode('utf-8').splitlines()[2].split(':')[1].strip()

# Get the output of the "dpkg --list" command
dpkg_list = subprocess.check_output(['dpkg', '--list'])

# Convert the output to a string
dpkg_list = dpkg_list.decode('utf-8')

# Split the output into a list of lines
dpkg_list = dpkg_list.splitlines()

# Create a list of packages
installed_packages = []

# Loop through the list of lines
for line in dpkg_list:
    # Split the line into a list of words
    line = line.split()

    # If the line is a package, add it to the list of packages
    if len(line) > 3 and line[0] == 'ii':
        installed_packages.append(line[1] + ' ' + line[2])

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

# Insert the hostname and release version into the hostnames table if it doesn't already exist
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM hostnames WHERE hostname = ?)
    INSERT INTO hostnames (hostname, release) VALUES (?, ?)
''', hostname, hostname, release)

#Update the release version of Ubuntu for the hostname if it is different
cursor.execute('''
    IF EXISTS (SELECT * FROM hostnames WHERE hostname = ? AND release <> ?)
    UPDATE hostnames SET release = ? WHERE hostname = ?
''', hostname, release, release, hostname)

# Insert every package in the installed_packages list into the packages table linking it to the hostname marking it as installed
for package in installed_packages:
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM packages WHERE hostname = ? AND package = ?)
        INSERT INTO packages (hostname, package, date, installed) VALUES (?, ?, ?, ?)
    ''', hostname, package, hostname, package, now, 1)

# Check if there are any packages in the packages table that are not in the list installed_packages and mark them as uninstalled updating the date
cursor.execute('''SELECT package FROM packages WHERE hostname = ?''', hostname)
packages = cursor.fetchall()
for package in packages:
    if package[0] not in installed_packages:
        cursor.execute('''
            UPDATE packages SET date = ?, installed = ? WHERE hostname = ? AND package = ?
        ''', now, 0, hostname, package[0])

# Commit the changes
conn.commit()

# Close the connection
conn.close()