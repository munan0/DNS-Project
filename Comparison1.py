import csv
from datetime import date

# opens list of domains from UpGuard
with open(f'{date.today()}_Comparison.csv') as check_file:
    check_set = set([row.split(',')[0].strip().upper() for row in check_file])

# opens list of domains from NS1 and a comparison CSV
with open(f'{date.today()}_ADDCSVNAME.csv', 'r') as in_file, open(f'{date.today()}_ADDDIFFCSVNAME.csv', 'w') as out_file:
    for line in in_file:
        # writes domain to the comparison CSV if domain not found in UpGuard 
        if line.split(',')[0].strip().upper() in check_set:
            writer = csv.writer(out_file)
            if "*" not in line:
                writer.writerow([line.split(',')[0]])
                # prints to terminal
                print(line.split(',')[0])