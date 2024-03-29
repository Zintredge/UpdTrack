"""
This is a custom module for ansible
It will be used to collect the data from the remote host and update a MSSQL database from the local host
The module will be called from the ansible playbook
The module collects the following data:
    - hostname
    - release version of Ubuntu
    - list of installed packages
    - timestamp

The module will be called from the ansible playbook as follows:
    - name: Collect data from remote host
        ansible_module:
            hostname: "{{ inventory_hostname }}"
            release: "{{ ansible_distribution_release }}"
            installedpackages: "{{ ansible_facts.packages }}"
            now: "{{ ansible_date_time.iso8601 }}"

The following is the MSSQL database schema:
    - hostnames
        - hostname VARCHAR(255) NOT NULL
        - release VARCHAR(255) NOT NULL
        - PRIMARY KEY (hostname)
    - packages
        - hostname VARCHAR(255) NOT NULL
        - package VARCHAR(255) NOT NULL
        - date DATETIME NOT NULL
        - installed BIT NOT NULL
        - PRIMARY KEY (hostname, package)

The connection string for the MSSQL database is saved in the file /etc/UpdTrack/db.pwd
The connection string is read from the file and used to connect to the database
If the file doesn't exist, the module will fail

The module will check if the tables hostnames and packages exist in the database
If they don't exist, the module will create them

The module will check if the hostname exists in the hostnames table
If it doesn't exist, the module will insert the hostname and release version into the hostnames table
If it does exist, the module will update the release version of Ubuntu for the hostname if it is different

The module will insert every package in the installedpackages list into the packages table linking it to the hostname marking it as installed and updating the date
The module will check if there are any packages in the packages table that are not in the list installedpackages and mark them as uninstalled updating the date
"""

#Import the required modules
from ansible.module_utils.basic import AnsibleModule
import pyodbc

# Create the module
def run_module():
    # Define the parameters that the module will accept
    module_args = dict(
        hostname=dict(type='str', required=True),
        release=dict(type='str', required=True),
        installedpackages=dict(type='list', required=True),
        now=dict(type='str', required=True)
    )

    # Create the AnsibleModule object
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Get the parameters from the module
    hostname = module.params['hostname']
    release = module.params['release']
    installedpackages = module.params['installedpackages']
    now = module.params['now']

    # Get the connection string from the file /etc/UpdTrack/db.pwd
    # with open('/etc/UpdTrack/db.pwd', 'r') as f:
    # with open('/etc/UpdTrack/db.pwd', 'r') as f:
    conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=SERVERNAME;DATABASE=UpdTrack;UID=USERNAME;PWD=PASSWORD

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
            packageversion VARCHAR (255) NOT NULL,
            date DATETIME NOT NULL,
            present BIT,
            uninstalled BIT,
            PRIMARY KEY (hostname, package, packageversion),
            FOREIGN KEY (hostname) REFERENCES hostnames(hostname)
        )
    ''')

    # Check if the hostname exists in the hostnames table
    cursor.execute('SELECT * FROM hostnames WHERE hostname=?', hostname)
    row = cursor.fetchone()

    # If the hostname doesn't exist, insert it into the hostnames table
    if row is None:
        cursor.execute('INSERT INTO hostnames (hostname, release) VALUES (?, ?)', hostname, release)
        conn.commit()

    # If the hostname exists, check if the release version is different
    elif row[1] != release:
        cursor.execute('UPDATE hostnames SET release=? WHERE hostname=?', release, hostname)
        conn.commit()

    # Check if the package is in the dictionary
    # If it is, do nothing
    # If it isn't, insert it into the packages table or Update if the version is updated

    sql = 'IF NOT EXISTS (SELECT * FROM packages WHERE package=? AND packageversion=? AND hostname=?) INSERT INTO packages (hostname, package, packageversion, date, uninstalled) VALUES (?, ?, ?, ?, ?)'
    for package in installedpackages:
       cursor.execute(sql, (package['name'], package['version'], hostname, hostname, package['name'], package['version'], now, 0 ))
       conn.commit()

    sql = 'UPDATE packages set uninstalled=?, date=? WHERE package=? AND packageversion=? AND hostname=?'
    for package in installedpackages:
       cursor.execute(sql, (0, now, package['name'], package['version'], hostname))
       conn.commit()

    # Set all present to 0

    sql = 'UPDATE packages set present=0 WHERE hostname =?'
    cursor.execute(sql, hostname)

    # Set all present packages to present = 1

    sql = 'UPDATE packages set present=? WHERE package=? AND packageversion=? AND hostname=?'

    for package in installedpackages:
        cursor.execute(sql, (1, package['name'], package['version'], hostname))
        conn.commit()

    # Update Date and uninstalled if present is 0 and uninstalled not already 1
    sql = 'UPDATE packages set date=?, uninstalled=? WHERE present=0 AND uninstalled<>1 AND hostname=?'
    cursor.execute(sql, now, 1, hostname)
    conn.commit()

    # Close the connection
    conn.close()

    # Return the result
    result = dict(
        changed=True,
        hostname=hostname,
        release=release,
        installedpackages=installedpackages,
        now=now
    )

    # Exit the module
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
