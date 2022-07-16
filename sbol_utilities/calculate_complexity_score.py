import os
import requests
from Bio import SeqIO
import git

IDT_API_TOKEN_URL = "https://www.idtdna.com/Identityserver/connect/token"
IDT_API_SCORE_URL = "https://www.idtdna.com/api/complexities/screengBlockSequences"
DISTRIBUTION_FASTA = 'distribution_synthesis_inserts.fasta'
"""File name for the distribution FASTA export for synthesis, to be located in the root directory"""


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
        sequence = { "Name": record.name, "Sequence": str(record.seq) }
        sequences.append(sequence)

    partition_size = 10
    partitions_sequences = [sequences[x:x+partition_size] for x in range(0, len(sequences), partition_size)]

    results = []
    for idx, partition in enumerate(partitions_sequences):
        print('Request {0} of {1} with size {2}'.format(idx, len(partitions_sequences), len(partition)))
        resp = requests.post(IDT_API_SCORE_URL,
                headers={'Authorization': 'Bearer {}'.format(token),
                'Content-Type': 'application/json; charset=utf-8'},
                json=partition,
                timeout = 180)
        results.append(resp.json())

    print('Requests to IDT API finished.')

    return results

def check_synthesizability(username: str, password: str, ClientID: str, ClientSecret: str, fasta_path: str):
    #root = "www" #ver como agarrar direccion

    print(f'Importing distribution sequences')

    with open(fasta_path) as handle:
        sequences = SeqIO.parse(handle, "fasta")
        print(f'Connecting to IDT DNA')
        token = get_token(username, password, ClientID, ClientSecret)
        scores = screening(token, sequences)
        print(scores)


root = git.Repo('.', search_parent_directories=True).working_tree_dir
fasta_path = os.path.join(root, DISTRIBUTION_FASTA)
#username = 'username'
#password = 'password'
#ClientID = 'ClientID'
#ClientSecret = 'ClientSecret'

check_synthesizability(username, password, ClientID, ClientServer, fasta_path)