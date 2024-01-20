"""
Scan a zone looking for invalid DNS records
"""
from datetime import date
from ipaddress import ip_address, ip_network

import re
import socket
import sys
import time

import csv
import ns1

# Exclude domains that we expect and are not interesing
DOMAIN_EXCLUDE = re.compile(r'.*\._(exluded domains)\..*')

# Exclude CNAME targets that are not interesting
CNAME_EXCLUDE = re.compile(r'^.*(not interesting targets)\.?$')

# Expected CNAME targets
CNAME_APPROVED = re.compile(r'^.*\.(expected targets)\.?$')

# IP Ranges owned (or at least trusted) 
IP_OWNED = [ip_network('enter ip here'), 
            ]

# List of private IP address ranges
IP_PRIVATE = [ip_network('enter ip here'),        # 
              ]

# List of approved nameservers
NS_APPROVED = re.compile(r'.*\.(approved name servers)$')

TYPES_EXCLUDE = re.compile(r'DNSKEY|TXT|RRSIG|DS')

# opens a CSV for all domains in NS1
NS1Domains = f"{date.today()}_NS1Domains.csv"
with open(NS1Domains, "w", encoding="UTF8") as file:
    writer = csv.writer(file)
    header = ["zone", "domain", "record type", "answer", "message"]
    writer.writerow(header)

# opens a CSV for all domains in NS1 based on record type we need
FilteredDomains = f"{date.today()}_FilteredDomains.csv"
with open(FilteredDomains, "w", encoding="UTF8") as file:
    writer = csv.writer(file)
    header = ["domain", "record type", "message"]
    writer.writerow(header)

# opens a CSV for dangling domains in NS1
DanglingDomains = f"{date.today()}_DanglingDomains.csv"
with open(DanglingDomains, "w", encoding="UTF8") as file:
    writer = csv.writer(file)
    header = ["domain", "message"]
    writer.writerow(header)

# prints out to the terminal
def record_out(zone, record, record_type, answer, messages):
   print(f"{zone},{record},{record_type},{answer},{messages}")

# creates the messages based on fail test
def eval_answer(zone, record, record_type, answer):
    messages = []

    if (record_type == 'CNAME'):
        # Check exclusion list
        answer = re.sub(r'\.$', '', answer)
        if not re.match(CNAME_EXCLUDE, answer):
            # Test if the CNAME points to a resolvable address
            try:
                ai = socket.getaddrinfo(answer, 0)
            except socket.gaierror:
                messages.append("CNAME does not resolve")

            if not re.match(CNAME_APPROVED, answer):
                messages.append("CNAME outside approved domain list")

    elif record_type == 'A':
        # Checking against a list of IP ranges is pretty clunky, there's probably a better way...
        address = ip_address(answer)
        ip_owned = 0
        ip_private = 0

        for network in IP_OWNED:
            if address in network:
                ip_owned += 1
                break

        for network in IP_PRIVATE:
            if address in network:
                ip_private +=1
                break

        if not ip_owned and zone == record:
            messages.append("A record at zone apex not in managed subnets")
        elif not ip_owned and not ip_private:
            messages.append("A record not in managed subnets")
    elif record_type == 'NS':
        if not re.match(NS_APPROVED, answer):
            messages.append("NS delegation outside NS1")

    return messages


def main():
    config, zones = None, None

    # NS1 API Key
    api = ns1.NS1(apiKey=('PUT NS1 KEY HERE'))

    try:
        config = api.config
        zones = api.zones()

        if config:
            config["follow_pagination"] = True
    except Exception:
        exit()

    for zone in zones.list():
        
        zone_name = zone['zone']
        try:
            zone = zones.retrieve(zone_name)
        except Exception:
            print("Error from NS1 API, sleeping and will retry one more time", file=sys.stderr)
            time.sleep(5)
            zone = zones.retrieve(zone_name)

        for record in zone['records']:
            domain = record['domain']

            if (re.match(DOMAIN_EXCLUDE, domain) or
                    'short_answers' not in record):
                continue

            for answer in record['short_answers']:
                record_type = record['type']
                if re.match(TYPES_EXCLUDE, record_type):
                    # skip record types we don't care about
                    continue

                messages = eval_answer(zone_name, domain, record_type, answer)
                record_out(zone_name, domain, record_type, answer, messages)

                # writes all domains from NS1 to the CSV
                with open(NS1Domains, 'a+', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(zone_name.split() + domain.split() + record_type.split() + answer.split() + messages)

                # writes the domains to the CSV based on record type 
                with open(FilteredDomains, 'a+', newline='') as file:
                    writer = csv.writer(file)
                    # these are the record types we are interesting in 
                    CNAME = 'CNAME'
                    A = 'A'
                    ALIAS = 'ALIAS'
                    MX = 'MX'
                    if (CNAME in record_type) or (A in record_type) or (ALIAS in record_type) or (MX in record_type):
                        writer.writerow(domain.split() + record_type.split() + [messages] )
                    
                # writes the dangling domains to the CSV
                with open(DanglingDomains, 'a+', newline='') as file:
                    writer = csv.writer(file)
                    for x in messages:
                        writer.writerow(domain.split()+ messages)


if __name__ == "__main__":
    main()    