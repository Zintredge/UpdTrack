"""
This file is an ansible module to collect the installed packages on a system and store the information in ansible facts.
The module is called by the ansible playbook and the output is stored in the ansible facts.
The ansible playbook is called by the ansible tower job template.
The required information is collected by the ansible module and stored in the ansible facts.
The package and version information is extracted from /var/lib/dpkg/status file.
"""

from ansible.module_utils.basic import AnsibleModule
import subprocess

def main():
    module = AnsibleModule(argument_spec={})
    module.exit_json(changed=False, ansible_facts={'packages': get_packages()})

# Function to extract the package and version information from /var/lib/dpkg/status file and store it in a list.
def get_packages():
    packages = []
    with open('/var/lib/dpkg/status') as f:
        package = {}
        for line in f:
            if line.startswith('Package: '):
                package['name'] = line.split('Package: ')[1].strip()
            elif line.startswith('Version: '):
                package['version'] = line.split('Version: ')[1].strip()
                packages.append(package)
                package = {}
    return packages

if __name__ == '__main__':
    main()
