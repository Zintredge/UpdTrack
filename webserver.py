"""
Display contents of a MSSQL database in a web browser.
Make a connection to the database and display the contents of the hostnames and packages tables.
Make a separate page for each hostname.
"""

# Import the necessary modules
import pyodbc
from flask import Flask, render_template

# Create the Flask app
app = Flask(__name__)

# Get the connection string from the file /etc/UpdTrack/db.pwd
with open('/etc/UpdTrack/db.pwd', 'r') as f:
    conn_str = f.read()

# Connect to the MSSQL DB
conn = pyodbc.connect(conn_str)

# Get a cursor
cursor = conn.cursor()

# Get the hostnames from the hostnames table
cursor.execute('SELECT hostname FROM hostnames')
hostnames = [row[0] for row in cursor.fetchall()]

# Get the packages and the date and time they were last updated per hostname
cursor.execute('''
    SELECT hostname, package, date FROM packages
    WHERE date = (SELECT MAX(date) FROM packages WHERE hostname = packages.hostname AND package = packages.package)
''')
packages = {row[0]: [] for row in cursor.fetchall()}
for row in cursor.fetchall():
    packages[row[0]].append({'package': row[1], 'date': row[2]})

# Close the connection
conn.close()

# Create the index page
@app.route('/')
def index():
    return render_template('index.html', hostnames=hostnames)

# Create a page for each hostname
@app.route('/<hostname>')
def hostname(hostname):
    return render_template('hostname.html', hostname=hostname, packages=packages[hostname])

# Run the Flask app
if __name__ == '__main__':
    app.run(host='localhost', port=5000)

# Path: templates/index.html
# Display the hostnames in a table
<!DOCTYPE html>
<html>
    <head>
        <title>UpdTrack</title>
    </head>
    <body>
        <h1>UpdTrack</h1>
        <table>
            <tr>
                <th>Hostname</th>
            </tr>
            {% for hostname in hostnames %}
            <tr>
                <td><a href="{{ hostname }}">{{ hostname }}</a></td>
            </tr>
            {% endfor %}
        </table>
    </body>
</html>

# Path: templates/hostname.html
# Display the hostname and the packages in a table
# Display the date and time the package was last updated
# Format the table rows to be readable on 1920x1080 displays
# Divide the table rows and columns by lines
# Display the table rows and columns in a grid with a fixed width and a fixed height and a fixed font size

<!DOCTYPE html>
<html>
    <head>
        <title>{{ hostname }}</title>
        <style>
            table {
                border-collapse: collapse;
                border: 1px solid black;
                font-size: 16px;
                font-family: monospace;
                width: 100%;
                height: 100%;
            }
            th {
                border: 1px solid black;
                text-align: left;
                padding: 5px;
            }
            td {
                border: 1px solid black;
                text-align: left;
                padding: 5px;
            }
        </style>
    </head>
    <body>
        <h1>{{ hostname }}</h1>
        <table>
            <tr>
                <th>Package</th>
                <th>Date</th>
            </tr>
            {% for package in packages %}
            <tr>
                <td>{{ package.package }}</td>
                <td>{{ package.date }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
</html>

