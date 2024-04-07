from __future__ import annotations

import json

from typing import Optional

import datetime
import argparse
import logging
import uuid
from requests import post
from requests.auth import HTTPBasicAuth

import sbol3
import tyto

from sbol_utilities.workarounds import type_to_standard_extension

COMPLEXITY_SCORE_NAMESPACE = 'http://igem.org/IDT_complexity_score'
REPORT_ACTIVITY_TYPE = 'https://github.com/SynBioDex/SBOL-utilities/compute-sequence-complexity'


class IDTAccountAccessor:
    """Class that wraps access to the IDT API"""

    _TOKEN_URL = 'https://www.idtdna.com/Identityserver/connect/token'
    """API URL for obtaining session tokens"""
    _SCORE_URL = 'https://www.idtdna.com/api/complexities/screengBlockSequences'
    """APR URL for obtaining sequence scores"""
    _BLOCK_SIZE = 1  # TODO: determine if it is possible to run multiple sequences in a single query
    SCORE_TIMEOUT = 120
    """Number of seconds to wait for score query requests to complete"""

    def __init__(self, username: str, password: str, client_id: str, client_secret: str):
        """Initialize with required access information for IDT API (see: https://www.idtdna.com/pages/tools/apidoc)
        Automatically logs in and obtains a session token

        :param username: Username of your IDT account
        :param password: Password of your IDT account
        :param client_id: ClientID key of your IDT account
        :param client_secret: ClientSecret key of your IDT account
        """
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = self._get_idt_access_token()

    @staticmethod
    def from_json(json_object) -> IDTAccountAccessor:
        """Initialize IDT account accessor from a JSON object with field values

        :param json_object: object with account information
        :return: Account accessor object
        """
        return IDTAccountAccessor(username=json_object['username'], password=json_object['password'],
                                  client_id=json_object['ClientID'], client_secret=json_object['ClientSecret'])

    def _get_idt_access_token(self) -> str:
        """Get access token for IDT API (see: https://www.idtdna.com/pages/tools/apidoc)

        :return: access token string
        """
        logging.info('Connecting to IDT API')
        data = {'grant_type': 'password', 'username': self.username, 'password': self.password, 'scope': 'test'}
        auth = HTTPBasicAuth(self.client_id, self.client_secret)
        result = post(IDTAccountAccessor._TOKEN_URL, data, auth=auth, timeout=IDTAccountAccessor.SCORE_TIMEOUT)

        if 'access_token' in result.json():
            return result.json()['access_token']
        else:
            raise ValueError('Access token for IDT API could not be generated. Check your credentials.')

    def get_sequence_scores(self, sequences: list[sbol3.Sequence]) -> list:
        """Retrieve synthesis complexity scores of sequences from the IDT API
        This system uses the gBlock API, which is intended for sequences from 125 to 3000 bp in length. If it is more 
        than 3000 bp or less than 125 bp your returned score will be 0. A complexity score in the range from 0 to 10 means 
        your sequence is synthesizable, if the score is greater or equal than 10 means it is not synthesizable.

        :param sequences: sequences for which we want to calculate the complexity score
        :return: dictionary mapping sequences to complexity Scores
        :return: List of lists of dictionaries with information about sequence synthesis features
        """
        # Set up list of query dictionaries
        seq_dict = [{'Name': str(seq.display_name), 'Sequence': str(seq.elements)} for seq in sequences]
        # Break into query blocks
        partitions_sequences = [seq_dict[x:x + 1] for x in range(0, len(seq_dict), IDTAccountAccessor._BLOCK_SIZE)]
        # Send each query to IDT and collect results
        results = []
        for idx, partition in enumerate(partitions_sequences):
            logging.debug('Sequence score request %i of %i', idx+1, len(partitions_sequences))
            resp = post(IDTAccountAccessor._SCORE_URL, json=partition, timeout=IDTAccountAccessor.SCORE_TIMEOUT,
                        headers={'Authorization': 'Bearer {}'.format(self.token),
                                 'Content-Type': 'application/json; charset=utf-8'})
            response_list = resp.json()
            if len(response_list) != len(partition):
                raise ValueError(f'Unexpected complexity score: expected {len(partition)} scores, '
                                 f'but got {len(response_list)}')
            results.append(resp.json())
        logging.info('Requests to IDT API finished.')
        return results

    def get_sequence_complexity(self, sequences: list[sbol3.Sequence]) -> dict[sbol3.Sequence, float]:
        """ Extract complexity scores from IDT API for a list of SBOL Sequence objects
        This works by computing full sequence evaluations, then compressing down to a single score for each sequence.

        :param sequences: list of SBOL Sequences to evaluate
        :return: dictionary mapping sequences to complexity Scores
        """
        # Retrieve full evaluations for sequences
        scores = self.get_sequence_scores(sequences)
        # Compute total score for each sequence as the sum all complexity scores for the sequence
        score_list = []
        for score_set in scores:
            for sequence_scores in score_set:
                complexity_score = sum(score.get('Score') for score in sequence_scores)
                score_list.append(complexity_score)
        # Associate each sequence to its score
        return dict(zip(sequences, score_list))


def get_complexity_score(seq: sbol3.Sequence) -> Optional[float]:
    """Given a sequence, return its previously computed complexity score, if such exists

    :param seq: SBOL Sequence object to check for score
    :return: score if set, None if not
    """
    scores = [score for score in seq.measures if tyto.EDAM.sequence_complexity_report in score.types]
    if scores:
        if len(scores) > 1:
            raise ValueError(f'Found multiple complexity scores on Sequence {seq.identity}')
        return scores[0].value
    else:
        return None


def get_complexity_scores(sequences: list[sbol3.Sequence], include_missing=False) -> \
        dict[sbol3.Sequence, Optional[float]]:
    """Retrieve complexity scores for a list of sequences

    :param sequences: Sequences to get scores for
    :param include_missing: if true, Sequences without scores are included, mapping to none
    :return: dictionary mapping Sequence to score
    """
    # TODO: change to run computations only on DNA sequences
    score_map = {seq: get_complexity_score(seq) for seq in sequences}
    if not include_missing:
        score_map = {k: v for k, v in score_map.items() if v is not None}
    return score_map


def idt_calculate_sequence_complexity_scores(accessor: IDTAccountAccessor, sequences: list[sbol3.Sequence]) -> \
        dict[sbol3.Sequence, float]:
    """Given a list of sequences, compute the complexity scores for any sequences not currently scored
    by sending the sequences to IDT's online service for calculating sequence synthesis complexity.
    Also records the complexity computation with an activity

    :param accessor: IDT API access object
    :param sequences: list of SBOL Sequences to evaluate
    :return: Dictionary mapping Sequences to complexity scores for newly computed sequences
    """
    # Determine which sequences need scores
    need_scores = [seq for seq, score in get_complexity_scores(sequences, include_missing=True).items()
                   if score is None]
    if not need_scores:
        return dict()

    # Query for the scores of the sequences
    score_dictionary = accessor.get_sequence_complexity(need_scores)

    # Create report generation activity
    doc = need_scores[0].document
    timestamp = datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    report_id = f'{COMPLEXITY_SCORE_NAMESPACE}/Complexity_Report_{timestamp.replace(":", "").replace("-", "")}_' \
                f'{str(uuid.uuid4())[0:8]}'
    report_generation = sbol3.Activity(report_id, end_time=timestamp, types=[REPORT_ACTIVITY_TYPE])
    doc.add(report_generation)

    # Mark the sequences with their scores, where each score is a dimensionless measure
    for sequence, score in score_dictionary.items():
        measure = sbol3.Measure(score, unit=tyto.OM.number_unit, types=[tyto.EDAM.sequence_complexity_report])
        measure.generated_by.append(report_generation)
        sequence.measures.append(measure)
    # return the dictionary of newly computed scores
    return score_dictionary


def idt_calculate_complexity_scores(accessor: IDTAccountAccessor, doc: sbol3.Document) -> dict[sbol3.Sequence, float]:
    """Given an SBOL Document, compute the complexity scores for any sequences in the Document not currently scored
    by sending the sequences to IDT's online service for calculating sequence synthesis complexity.
    Also records the complexity computation with an activity

    :param accessor: IDT API access object
    :param doc: SBOL document with sequences of interest in it
    :return: Dictionary mapping Sequences to complexity scores
    """
    sequences = [obj for obj in doc if isinstance(obj, sbol3.Sequence)]
    return idt_calculate_sequence_complexity_scores(accessor, sequences)


def main():
    """
    Main wrapper: read from input file, invoke idt_calculate_complexity_scores, then write to output file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--credentials',
                        help="""JSON file containing IDT API access credentials.
To obtain access credentials, follow the directions at https://www.idtdna.com/pages/tools/apidoc
The values of the IDT access credentials should be stored in a JSON of the following form:
{ "username": "username", "password": "password", "ClientID": "####", "ClientSecret": "XXXXXXXXXXXXXXXXXXX" }"
""")
    parser.add_argument('--username', help="Username of your IDT account (if not using JSON credentials)")
    parser.add_argument('--password', help="Password of your IDT account (if not using JSON credentials)")
    parser.add_argument('--ClientID', help="ClientID of your IDT account (if not using JSON credentials)")
    parser.add_argument('--ClientSecret', help="ClientSecret of your IDT account (if not using JSON credentials)")
    parser.add_argument('input_file', help="Absolute path to sbol file with sequences")
    parser.add_argument('output_name', help="Name of SBOL file to be written")
    parser.add_argument('-t', '--file-type', dest='file_type', default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0)
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    logging.getLogger().setLevel(level=(logging.WARN if verbosity == 0 else
                                        logging.INFO if verbosity == 1 else logging.DEBUG))
    input_file = args_dict['input_file']
    output_name = args_dict['output_name']

    if args_dict['credentials'] != None:
        with open(args_dict['credentials']) as credentials:
            idt_accessor = IDTAccountAccessor.from_json(json.load(credentials))
    else:
        idt_accessor = IDTAccountAccessor(args_dict['username'], args_dict['password'], args_dict['ClientID'],
                                          args_dict['ClientSecret'])

    extension = type_to_standard_extension[args_dict['file_type']]
    outfile_name = output_name if output_name.endswith(extension) else output_name + extension

    # Read file, convert, and write resulting document
    logging.info('Reading SBOL file ' + input_file)
    doc = sbol3.Document()
    doc.read(input_file)
    results = idt_calculate_complexity_scores(idt_accessor, doc)
    doc.write(outfile_name, args_dict['file_type'])
    logging.info('SBOL file written to %s with %i new scores calculated', outfile_name, len(results))


if __name__ == '__main__':
    main()
