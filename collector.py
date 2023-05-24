"""
Check release version of Ubuntu.
Run apt list and parse the output to get a list of installed packages including the version number.
Create a list of the packages including the version number and the hostname of the machine and save it to a file.
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
#now = now.strftime("%Y-%m-%d %H:%M:%S")

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

# Save the list of packages to a file named after the hostname
with open('/var/UpdTrack/' + hostname, 'w') as f:
    for package in installed_packages:
        f.write(package + '\n')

# Wrtie the hostname, release version and date to the file mentioned above as the first three lines
with open('/var/UpdTrack/' + hostname, 'r+') as f:
    content = f.read()
    f.seek(0, 0)
    f.write(hostname + '\n' + release + '\n' + now.strftime("%Y-%m-%d %H:%M:%S") + '\n' + content)