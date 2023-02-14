"""
Run apt list and parse the output to get a list of installed packages.
Create a list of the packages and the hostname of the machine.
Connect to the MSSQL DB. Get the connection string from the a file called /etc/UpdTrack/db.pwd.
If the table hostnames doesn't exist, create it.
If the table packages doesn't exist, create it.
Insert the hostname into the hostnames table.
Insert the hostname, package name, and current date and time into the packages table.
If the hostname already exists in the hostnames table, don't insert it.
If the combination of hostname and package name already exist in the packages table, don't insert it.
If the hostname and package name don't exist in the list of packages, delete them from the packages table.
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

# Split the output into a list of lines
apt_list = apt_list.splitlines()

# Create a list to hold the package names
packages = []

# Loop through the lines of the output
for line in apt_list:
    # Split the line into a list of words
    line = line.split()
    # Get the package name
    package = line[0]
    # Add the package name to the packages list
    packages.append(package)

# Get the connection string from the file /etc/UpdTrack/db.pwd
with open('/etc/UpdTrack/db.pwd', 'r') as f:
    conn_str = f.read()

# Connect to the MSSQL DB
conn = pyodbc.connect(conn_str)

# Get a cursor
cursor = conn.cursor()

# Create the hostnames table if it doesn't exist
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='hostnames' AND xtype='U')
    CREATE TABLE hostnames (
        hostname VARCHAR(255) NOT NULL PRIMARY KEY
    )
''')

# Create the packages table if it doesn't exist
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packages' AND xtype='U')
    CREATE TABLE packages (
        hostname VARCHAR(255) NOT NULL,
        package VARCHAR(255) NOT NULL,
        date DATETIME NOT NULL,
        PRIMARY KEY (hostname, package),
        FOREIGN KEY (hostname) REFERENCES hostnames (hostname)
    )
''')

# Insert the hostname into the hostnames table
cursor.execute('''
    INSERT INTO hostnames (hostname)
    SELECT ? WHERE NOT EXISTS (SELECT * FROM hostnames WHERE hostname = ?)
''', hostname, hostname)

# Insert the hostname, package name, and current date and time into the packages table
for package in packages:
    cursor.execute('''
        INSERT INTO packages (hostname, package, date)
        SELECT ?, ?, ? WHERE NOT EXISTS (SELECT * FROM packages WHERE hostname = ? AND package = ?)
    ''', hostname, package, now, hostname, package)

# Delete the hostname and package name from the packages table if it doesn't exist in the list of packages
cursor.execute('''
    DELETE FROM packages WHERE hostname = ? AND package NOT IN (SELECT package FROM @packages)
''', hostname)

# Commit the changes
conn.commit()

# Close the connection
conn.close()

# Exit the script
sys.exit()

# Path: /etc/UpdTrack/db.pwd
# This file contains the connection string for the MSSQL DB
# The connection string is in the format:
# DRIVER={ODBC Driver 17 for SQL Server};SERVER=server;DATABASE=database;UID=username;PWD=password
# Replace the values in the curly braces with the appropriate values for your environment

# Path: /etc/UpdTrack/collector.service
# This file contains the service definition for the collector service
# The service is used to run the collector.py script every 24 hours

[Unit]
Description=UpdTrack collector service
After=network.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/python3 /usr/local/bin/collector.py
Restart=on-failure

[Install]
WantedBy=multi-user.target

# Path: /etc/UpdTrack/collector.timer
# This file contains the timer definition for the collector service
# The timer is used to run the collector service every 24 hours

[Unit]
Description=UpdTrack collector timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target

# Path: /etc/UpdTrack/collector.sh
# This file contains the shell script used to install the collector service and timer
# The script is run by the UpdTrack installer

# Create the UpdTrack directory
mkdir /etc/UpdTrack

# Copy the collector.py script to the UpdTrack directory
cp collector.py /etc/UpdTrack

# Copy the db.pwd file to the UpdTrack directory
cp db.pwd /etc/UpdTrack

# Copy the collector.service file to the systemd directory
cp collector.service /etc/systemd/system

# Copy the collector.timer file to the systemd directory
cp collector.timer /etc/systemd/system

# Enable the collector service
systemctl enable collector.service

# Enable the collector timer
systemctl enable collector.timer

# Start the collector service
systemctl start collector.service

# Start the collector timer
systemctl start collector.timer