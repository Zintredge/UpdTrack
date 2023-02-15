"""
Run apt list and parse the output to get a list of installed packages including the version number.
Create a list of the packages including the version number and the hostname of the machine.
Connect to the MSSQL DB. Get the connection string from the a file called /etc/UpdTrack/db.pwd.
If the table hostnames doesn't exist, create it.
If the table packages doesn't exist, create it.
Insert the hostname into the hostnames table.
Insert the hostname, package name including version number and current date and time into the packages table.
If the hostname already exists in the hostnames table, don't insert it.
If the combination of hostname and package name already exist in the packages table, don't insert it.
If the hostname and package name including the package version don't exist in the list of packages, delete them from the packages table.
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
        hostname VARCHAR(255) NOT NULL PRIMARY KEY
    )
''')

# If the table packages doesn't exist, create it
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packages' AND xtype='U')
    CREATE TABLE packages (
        hostname VARCHAR(255) NOT NULL,
        package VARCHAR(255) NOT NULL,
        date DATETIME NOT NULL,
        PRIMARY KEY (hostname, package)
    )
''')

# Insert the hostname into the hostnames table
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM hostnames WHERE hostname = ?)
    INSERT INTO hostnames (hostname) VALUES (?)
''', hostname, hostname)

# Insert every package in the installed_packages list into the packages table linking it to the hostname
for package in installed_packages:
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM packages WHERE hostname = ? AND package = ?)
        INSERT INTO packages (hostname, package, date) VALUES (?, ?, ?)
    ''', hostname, package, hostname, package, now)

#For every package in the packages table delete the entry if the package doesn't exist in the installed_packages list for the current machine
for package in cursor.execute('SELECT package FROM packages WHERE hostname = ?', hostname):
    if package not in installed_packages:
        cursor.execute('DELETE FROM packages WHERE hostname = ? AND package = ?', hostname, package)

# Commit the changes
conn.commit()

# Close the connection
conn.close()