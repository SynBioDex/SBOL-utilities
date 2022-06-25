import csv
import sys

def main(file_name):
    """Read vim modified mappings of gb and so ontologies"""
    hmp = {}; mappings = 82
    while mappings:
        line = input().split(" ")
        if len(line) > 1:
            line[0] = line[0].lstrip('("')
            line[0] = line[0].rstrip('")')
            line[1] = line[1].lstrip('("')
            line[1] = line[1].rstrip('")')
            if not hmp.get(line[0]): hmp[line[0]] = line[1]
            else: print(f"DUPLICATE KEY!: KEY: {line[0]} VALUE {line[1]}")
        mappings -= 1
    writeCSV(hmp, file_name)

def writeCSV(mappings: dict, file_name):
    """Write GenBank to SO ontologies dict to a csv"""
    with open(file_name, mode='w') as csv_file:
        fieldnames = ['GenBank_Ontology', 'SO_Ontology']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames if file_name == 'sbol_utilities/gb2so.csv' else list(reversed(fieldnames)))
        writer.writeheader()
        for mapping in mappings:
            if file_name == 'sbol_utilities/gb2so.csv':
                writer.writerow({'GenBank_Ontology': mapping, 'SO_Ontology': mappings[mapping]})
            else:
                writer.writerow({'SO_Ontology': mapping, 'GenBank_Ontology': mappings[mapping]})

def readCSV(file_name):
    with open(file_name, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        hmp = {}
        for row in csv_reader:
            hmp[row["GenBank_Ontology"]] = row["SO_Ontology"]
        return hmp

if __name__ == '__main__':
    FILE_NAME = "sbol_utilities/gb2so.csv"
    IN_FILE = "GB2SO"
    if sys.argv[1] == "GB2SO":
        FILE_NAME = 'sbol_utilities/gb2so.csv'
        IN_FILE = "GB2SO"
    elif sys.argv[1] == "SO2GB":
        FILE_NAME = 'sbol_utilities/so2gb.csv'
        IN_FILE = "SO2GB"
    sys.stdin = open(IN_FILE, "r")
    main(FILE_NAME)
    print(readCSV(FILE_NAME))
    print(len(readCSV(FILE_NAME)))
