import os
import requests
from Bio import SeqIO
import git
import sbol3
from sbol3 import Measure
import tyto
import datetime
import argparse
import logging

IDT_API_TOKEN_URL = "https://www.idtdna.com/Identityserver/connect/token"
IDT_API_SCORE_URL = "https://www.idtdna.com/api/complexities/screengBlockSequences"
DISTRIBUTION_FASTA = 'distribution_synthesis_inserts.fasta'
"""File name for the distribution FASTA export for synthesis, to be located in the root directory"""
partition_size = 10

def get_token(username: str, password: str, ClientID: str, ClientSecret: str):
    data = {'grant_type': 'password', 'username': username, 'password': password, 'scope': 'test'}
    r = requests.post(IDT_API_TOKEN_URL, data, auth=requests.auth.HTTPBasicAuth(ClientID, ClientSecret), timeout = 60)
    if(not('access_token' in r.json())):
        raise Exception("Access token could not be generated. Check your credentials.")
    access_token = r.json()['access_token']
    return access_token

def screening(token, listOfSequences):
    sequences = []

    for record in listOfSequences:
        sequence = {"Name": record.name, "Sequence": str(record.seq)}
        sequences.append(sequence)

    partitions_sequences = [sequences[x:x+partition_size] for x in range(0, len(sequences), partition_size)]
    results = []
    batches = len(partitions_sequences)

    for idx, partition in enumerate(partitions_sequences):
        print('Request {0} of {1} with size {2}'.format(idx+1, len(partitions_sequences), len(partition)))
        resp = requests.post(IDT_API_SCORE_URL,
                headers={'Authorization': 'Bearer {}'.format(token),
                'Content-Type': 'application/json; charset=utf-8'},
                json=partition,
                timeout=300)
        results.append(resp.json())

    print('Requests to IDT API finished.')

    return results, len(sequences), batches

def check_synthesizability(username: str, password: str, ClientID: str, ClientSecret: str, fasta_path: str):

    print(f'Importing distribution sequences')
    with open(fasta_path) as handle:
        sequences = SeqIO.parse(handle, "fasta")
        print(f'Connecting to IDT DNA')
        token = get_token(username, password, ClientID, ClientSecret)
        scores, length_sequences, batches = screening(token, sequences)

    #Extract sequence identities and elements from fasta file
    with open(fasta_path) as handle:
        sequences = SeqIO.parse(handle, "fasta")
        ids = []
        sequence_elements = []
        for seque in sequences:
            sequence_elements.append(str(seque.seq[:]))
            ids.append(str(seque.name))

    #Retrieve only complexity scores from IDT info
    scores_list = []
    cont = 0
    #Iterate through results from IDT
    for i in range(0, batches):
        for j in range(0, partition_size):
            if cont == length_sequences:
                break
            cont += 1
            complexity_score = 0
            for k in range(0, len(scores[i][j])):
                complexity_score += scores[i][j][k].get('Score')
            scores_list.append(complexity_score)

    return scores_list, ids, sequence_elements

def main():
    #Retrieve datetime with UTC offset
    DateTime = datetime.datetime.utcnow()

    #Default path of fasta file for iGEM Distribution sequences
    root = git.Repo('.', search_parent_directories=True).working_tree_dir
    fasta_path = os.path.join(root, DISTRIBUTION_FASTA)

    #Define arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help="Username of your IDT account")
    parser.add_argument('password', help="Password of your IDT account")
    parser.add_argument('ClientID', help="ClientID of your IDT account")
    parser.add_argument('ClientSecret', help="ClientSecret of your IDT account")
    parser.add_argument('fasta_path', help="Absolute path to fasta file with sequences")
    args_dict = vars(parser.parse_args())

    # Extract arguments
    username = args_dict['username']
    password = args_dict['password']
    ClientID = args_dict['ClientID']
    ClientSecret = args_dict['ClientSecret']


    scores_list, ids, sequence_elements = check_synthesizability(username, password, ClientID, ClientSecret, fasta_path)
    #Create SBOL document
    doc = sbol3.Document()
    sbol3.set_namespace('http://sbolstandard.org/testfiles')
    #Define unit measure as dimensionless
    number_unit = tyto.OM.number_unit
    #Create an Activity object to store timestamp
    sequence_timestamp = sbol3.Activity('Timestamp', end_time=DateTime.isoformat(timespec='seconds') + 'Z')
    doc.add(sequence_timestamp)

    #Create several variables to store sequence SBOL objects
    variable_sequence = ["Sequence%d" % x for x in range(0, len(ids))]

    results = []
    for i in range(0, len(scores_list)):
        #Create SBOL sequence objects
        variable_sequence[i] = sbol3.Sequence(ids[i], elements=sequence_elements[i], encoding=sbol3.IUPAC_DNA_ENCODING)
        #Add IDT complexity score measure
        variable_sequence[i].measures.append(Measure(scores_list[i], unit=number_unit, name='Measure_'+ids[i]))
        #Link sequence objects with timestamp
        variable_sequence[i].generated_by = [sequence_timestamp]
        doc.add(variable_sequence[i])
        #Create list of dictionaries with results
        results.append(dict(Object=variable_sequence[i], IDTcomplexity_score=scores_list[i]))

    doc.write('SBOL_document_IDT_Complexity_Scores.nt', sbol3.SORTED_NTRIPLES)

    return results

if __name__ == '__main__':
    main()
