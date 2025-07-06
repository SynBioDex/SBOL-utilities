from __future__ import annotations

import json

from typing import List, Optional, Dict

import datetime
import argparse
import logging
import uuid
from requests import post
from requests.auth import HTTPBasicAuth
from abc import ABC, abstractmethod

import sbol3
import tyto

from sbol_utilities.workarounds import type_to_standard_extension

COMPLEXITY_SCORE_NAMESPACE = 'http://igem.org/IDT_complexity_score'
REPORT_ACTIVITY_TYPE = 'https://github.com/SynBioDex/SBOL-utilities/compute-sequence-complexity'


class BaseAccountAccessor(ABC):
    @staticmethod
    @abstractmethod
    def from_json(json_object):
        pass

    @abstractmethod
    def get_sequence_complexity(self, sequences: List[sbol3.Sequence]) -> Dict[sbol3.Sequence, Optional[float]]:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class AuthenticatedAccountAccessor(BaseAccountAccessor):
    @abstractmethod
    def _setup_authentication(self):
        pass


class IDTAccountAccessor(AuthenticatedAccountAccessor):
    """Class that wraps access to the IDT API"""

    _SUBDOMAINS = ['https://www.idtdna.com/', 'https://eu.idtdna.com/', 'https://sg.idtdna.com/']
    _TOKEN_ENDPOINT = 'Identityserver/connect/token'
    """API ENDPOINT for obtaining session tokens"""
    _SCORE_ENDPOINT = 'api/complexities/screengBlockSequences'
    """API ENDPOINT for obtaining sequence scores"""
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
        self.base_url = None
        self.token = self._setup_authentication()

    @staticmethod
    def from_json(json_object) -> IDTAccountAccessor:
        """Initialize IDT account accessor from a JSON object with field values

        :param json_object: object with account information
        :return: Account accessor object
        """
        return IDTAccountAccessor(
            username=json_object['username'],
            password=json_object['password'],
            client_id=json_object['ClientID'],
            client_secret=json_object['ClientSecret'],
        )

    def _setup_authentication(self) -> str:
        """Get access token for IDT API (see: https://www.idtdna.com/pages/tools/apidoc)

        :return: access token string
        """
        logging.info('Connecting to IDT API')
        data = {'grant_type': 'password', 'username': self.username, 'password': self.password, 'scope': 'test'}
        auth = HTTPBasicAuth(self.client_id, self.client_secret)

        for domain in IDTAccountAccessor._SUBDOMAINS:
            try:
                result = post(
                    f'{domain}{IDTAccountAccessor._TOKEN_ENDPOINT}',
                    data,
                    auth=auth,
                    timeout=IDTAccountAccessor.SCORE_TIMEOUT,
                )
                # FIX: Add robust error checking for the HTTP request
                result.raise_for_status()
                self.base_url = domain
                return result.json()['access_token']
            except Exception as e:
                logging.debug(f'Failed to authenticate with IDT domain {domain}: {e}')

        raise ValueError(
            'Access token for IDT API could not be generated. Check your credentials and network connection.'
        )

    def get_sequence_scores(self, sequences: list[sbol3.Sequence]) -> list[list[dict]]:
        """Retrieve synthesis complexity scores of sequences from the IDT API
        This system uses the gBlock API, which is intended for sequences from 125 to 3000 bp in length. If it is more
        than 3000 bp or less than 125 bp your returned score will be 0. A complexity score in the range from 0 to 10 means
        your sequence is synthesizable, if the score is greater or equal than 10 means it is not synthesizable.

        :param sequences: sequences for which we want to calculate the complexity score
        :return: A list of assessment lists. Each inner list contains assessment dictionaries for one sequence.
        """
        seq_dict = [{'Name': str(seq.display_name), 'Sequence': str(seq.elements)} for seq in sequences]
        partitions_sequences = [
            seq_dict[x : x + IDTAccountAccessor._BLOCK_SIZE]
            for x in range(0, len(seq_dict), IDTAccountAccessor._BLOCK_SIZE)
        ]

        results = []
        for idx, partition in enumerate(partitions_sequences):
            logging.debug(f'Sequence score request {idx + 1} of {len(partitions_sequences)}')
            resp = post(
                f'{self.base_url}{IDTAccountAccessor._SCORE_ENDPOINT}',
                json=partition,
                timeout=IDTAccountAccessor.SCORE_TIMEOUT,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json; charset=utf-8',
                },
            )
            resp.raise_for_status()
            response_json = resp.json()

            results.extend(response_json)

        logging.info('Requests to IDT API finished.')
        return results

    def get_sequence_complexity(self, sequences: list[sbol3.Sequence]) -> dict[sbol3.Sequence, Optional[float]]:
        """Extract complexity scores from IDT API for a list of SBOL Sequence objects
        This works by computing full sequence evaluations, then compressing down to a single score for each sequence.

        :param sequences: list of SBOL Sequences to evaluate
        :return: dictionary mapping sequences to a single complexity score, or None if no score was returned.
        """
        if not sequences:
            return {}

        # This now returns a clean list of assessment lists, e.g., [[...], [...]]
        all_assessments = self.get_sequence_scores(sequences)
        score_list = []

        for assessment_list in all_assessments:
            # Safely get 'Score' (defaulting to 0.0 if missing) and sum up for the sequence.
            complexity_score = sum(assessment.get('Score', 0.0) for assessment in assessment_list)
            score_list.append(round(complexity_score, 1))

        # Associate each sequence to its calculated score
        return dict(zip(sequences, score_list))

    @property
    def provider_name(self) -> str:
        """Return the name of the provider."""
        return 'IDT'


# class TwistAccountAccessor(BaseAccountAccessor):
#     """
#     Class that wraps access to the Twist API for complexity scores.
#     """
#
#     # the score url is not correct
#     _SCORE_URL = 'https://api.twistdna.com/api/v1/screening/complexity-and-rules'
#
#     def __init__(
#         self,
#         api_key: str,
#         end_user_token: Optional[str] = None,
#         default_sequence_type: str = 'cloned',  # Or 'non-cloned' - clarify default/necessity
#         default_vector_id: Optional[str] = None,
#         default_insertion_point_id: Optional[str] = None,
#         timeout: int = DEFAULT_TIMEOUT,
#     ):
#         """
#         Initialize with Twist API access information.
#
#         :param api_key: Your Twist API Key (required).
#         :param end_user_token: Optional X-END-USER-TOKEN.
#         :param default_sequence_type: Default sequence type ('cloned' or 'non-cloned') if not found in SBOL.
#         :param default_vector_id: Default vector ID (if applicable) if not found in SBOL.
#         :param default_insertion_point_id: Default insertion point ID (if applicable) if not found in SBOL.
#         :param timeout: Request timeout in seconds.
#         """
#         super().__init__(TWIST_COMPLEXITY_SCORE_NAMESPACE, TWIST_REPORT_ACTIVITY_TYPE, TWIST_SERVICE_NAME, timeout)
#         if not api_key:
#             raise ValueError('Twist API Key (AUTH header) is required.')
#         self.api_key = api_key
#         self.end_user_token = end_user_token
#         # Store defaults, maybe overridden by SBOL data later
#         self.default_sequence_type = default_sequence_type
#         self.default_vector_id = default_vector_id
#         self.default_insertion_point_id = default_insertion_point_id
#         self._headers: Optional[Dict[str, str]] = None  # Cache headers after first _authenticate call
#
#     @classmethod
#     def from_creds_json(cls: Type[TwistAccountAccessor], json_path: str) -> TwistAccountAccessor:
#         """Initialize Twist account accessor from a JSON file path."""
#         creds_data = cls._load_json_file(json_path)
#         # Expect credentials under a 'twist' key
#         if 'twist' not in creds_data:
#             raise ValueError(f"Credentials file {json_path} must contain a top-level 'twist' key.")
#         twist_creds = creds_data['twist']
#
#         required_keys = {'api_key'}
#         missing_keys = required_keys - twist_creds.keys()
#         if missing_keys:
#             raise ValueError(f'Twist credentials in {json_path} are missing keys: {missing_keys}')
#
#         timeout = int(twist_creds.get('timeout', DEFAULT_TIMEOUT))
#
#         # Include optional fields from JSON if present, allowing overrides of class defaults
#         return cls(
#             api_key=twist_creds['api_key'],
#             end_user_token=twist_creds.get('end_user_token'),
#             default_sequence_type=twist_creds.get(
#                 'default_sequence_type', 'cloned'
#             ),  # Default fallback if not in JSON
#             default_vector_id=twist_creds.get('default_vector_id'),
#             default_insertion_point_id=twist_creds.get('default_insertion_point_id'),
#             timeout=timeout,
#         )
#
#     def _authenticate(self):
#         """Prepares the authorization headers for Twist API calls. Idempotent."""
#         if self._headers:
#             logging.debug('Using existing Twist headers.')
#             return
#
#         logging.info('Preparing Twist API headers.')
#         self._headers = {
#             'AUTH': self.api_key,
#             'Content-Type': 'application/json',
#             'Accept': 'application/json',  # Explicitly accept JSON responses
#         }
#         if self.end_user_token:
#             self._headers['X-END-USER-TOKEN'] = self.end_user_token
#         logging.debug('Twist headers prepared.')
#         # No actual API call for auth needed here, just setting headers. No errors expected unless config is bad.
#
#     # --- Placeholder Methods for SBOL Data Extraction (Needs Implementation) ---
#     def _get_twist_vector_id_from_sbol(self, sequence: sbol3.Sequence) -> Optional[str]:
#         """
#         Placeholder: Extracts the TWIST vector ID associated with a sequence from SBOL data.
#         Needs implementation based on how this info is stored (e.g., annotation, related component).
#
#         :param sequence: The SBOL Sequence object.
#         :return: Vector ID string or None if not found.
#         """
#         # TODO: Implement logic to find vector_id from sequence. Example: Check sequence.description, or sequence.wasDerivedFrom linking to a vector Component? Or a custom annotation?
#         # Example using a hypothetical annotation namespace:
#         # twist_ns = "http://twistbioscience.com/sbol/annotation/"
#         # vector_id = sequence.get_annotation(twist_ns + "vector_id")
#         # if vector_id: return str(vector_id)
#         logging.debug(f'SBOL extraction for Twist vector_id not implemented for {sequence.identity}. Using default.')
#         return None
#
#     def _get_twist_insertion_point_id_from_sbol(self, sequence: sbol3.Sequence) -> Optional[str]:
#         """
#         Placeholder: Extracts the TWIST insertion point ID associated with a sequence from SBOL data.
#
#         :param sequence: The SBOL Sequence object.
#         :return: Insertion point ID string or None if not found.
#         """
#         # TODO: Implement logic similar to _get_twist_vector_id_from_sbol
#         logging.debug(
#             f'SBOL extraction for Twist insertion_point_id not implemented for {sequence.identity}. Using default.'
#         )
#         return None
#
#     def _get_twist_sequence_type_from_sbol(self, sequence: sbol3.Sequence) -> Optional[str]:
#         """
#         Placeholder: Determines the TWIST sequence type ('cloned'/'non-cloned') from SBOL data.
#
#         :param sequence: The SBOL Sequence object.
#         :return: 'cloned' or 'non-cloned' string, or None if not determinable.
#         """
#         # TODO: Implement logic. Maybe based on presence/absence of vector features, or specific roles/types?
#         # Example: If sequence has wasDerivedFrom linking to a vector, maybe it's 'cloned'?
#         logging.debug(
#             f'SBOL extraction for Twist sequence_type not implemented for {sequence.identity}. Using default.'
#         )
#         return None
#
#     # --- End Placeholder Methods ---
#
#     def _get_api_scores(self, sequences: List[sbol3.Sequence]) -> Dict[sbol3.Sequence, Optional[float]]:
#         """
#         Retrieve synthesis complexity scores from the Twist API.
#
#         **ASSUMPTIONS (Verify with Twist Docs):**
#         1. API endpoint `_SCORE_URL` is correct.
#         2. API expects one sequence per request (batching not implemented).
#         3. Request requires 'sequence', 'sequence_type', and possibly 'vector_id', 'insertion_point_id'.
#         4. Response is JSON containing a 'complexity_score' field (float). E.g., `{'complexity_score': 5.2, ...}`.
#
#         :param sequences: List of sequences for which to calculate the complexity score.
#         :return: Dictionary mapping sequences to complexity Scores (float) or None if failed.
#         """
#         if not self._headers:
#             # Should be caught by calculate_complexity_scores, but check again.
#             logging.error('Twist Authentication headers not available. Authentication might have failed.')
#             return {seq: None for seq in sequences}
#
#         results_map: Dict[sbol3.Sequence, Optional[float]] = {}
#         for seq in sequences:
#             seq_elements = str(seq.elements) if seq.elements else ''
#             if not seq_elements:
#                 logging.warning(f'Sequence {seq.identity} has empty elements. Skipping Twist API call.')
#                 results_map[seq] = None
#                 continue
#
#             # Determine payload parameters, preferring SBOL data extraction over defaults
#             sequence_type = self._get_twist_sequence_type_from_sbol(seq) or self.default_sequence_type
#             vector_id = self._get_twist_vector_id_from_sbol(
#                 seq
#             )  # Use default only if needed AND if SBOL extraction returns None
#             insertion_point_id = self._get_twist_insertion_point_id_from_sbol(
#                 seq
#             )  # Use default only if needed AND if SBOL extraction returns None
#
#             # Construct payload based on API requirements (VERIFY THESE!)
#             payload = {'sequence': seq_elements, 'sequence_type': sequence_type}
#             # Only include vector/insertion point if they are available (from SBOL or default)
#             # Check Twist docs if these are conditionally required based on sequence_type
#             final_vector_id = vector_id or self.default_vector_id
#             final_insertion_point_id = insertion_point_id or self.default_insertion_point_id
#
#             if final_vector_id:
#                 payload['vector_id'] = final_vector_id
#             if final_insertion_point_id:
#                 payload['insertion_point_id'] = final_insertion_point_id
#
#             logging.debug(f'Requesting Twist score for {seq.identity} with payload: {payload}')
#             try:
#                 response = self._make_request('POST', self._SCORE_URL, headers=self._headers, json_payload=payload)
#                 response_data = response.json()
#
#                 # --- PARSE RESPONSE ---
#                 # !!! This part is critical and depends entirely on the Twist API response structure !!!
#                 # Example Assumption: response is {'complexity_score': 1.23, ...} or similar
#                 if isinstance(response_data, dict) and 'complexity_score' in response_data:
#                     try:
#                         # Attempt to convert the score to float
#                         score = float(response_data['complexity_score'])
#                         results_map[seq] = score
#                         logging.debug(f'Twist Score for {seq.identity}: {score}')
#                     except (ValueError, TypeError) as e:
#                         logging.error(
#                             f"Could not parse 'complexity_score' field ({response_data.get('complexity_score')}) as float for {seq.identity}. Error: {e}. Score set to None."
#                         )
#                         results_map[seq] = None
#                 elif isinstance(response_data, dict) and 'score' in response_data:  # Try alternative key 'score'
#                     try:
#                         score = float(response_data['score'])
#                         results_map[seq] = score
#                         logging.debug(f"Twist Score (using 'score' key) for {seq.identity}: {score}")
#                     except (ValueError, TypeError) as e:
#                         logging.error(
#                             f"Could not parse 'score' field ({response_data.get('score')}) as float for {seq.identity}. Error: {e}. Score set to None."
#                         )
#                         results_map[seq] = None
#                 else:
#                     # Handle unexpected response format
#                     logging.warning(
#                         f"Unexpected Twist score response format for {seq.identity}. Expected dict with 'complexity_score' or 'score', got: {str(response_data)[:500]}... Score set to None."
#                     )
#                     results_map[seq] = None
#                 # -----------------------
#
#             except (ValueError, requests.RequestException) as e:  # Catch errors from _make_request or response.json()
#                 logging.error(f'Twist API request failed for {seq.identity}: {e}. Score set to None.')
#                 results_map[seq] = None
#             except Exception as e:  # Catch any other unexpected errors
#                 logging.error(
#                     f'Unexpected error processing Twist score for {seq.identity}: {e}. Score set to None.',
#                     exc_info=True,
#                 )
#                 results_map[seq] = None
#
#         # Ensure all initially requested sequences are in the results map
#         final_results_map = {seq: results_map.get(seq) for seq in sequences}
#
#         logging.info(f'Finished Twist score requests. Returning results for {len(final_results_map)} sequences.')
#         return final_results_map


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


def get_complexity_scores(
    sequences: list[sbol3.Sequence], include_missing=False
) -> dict[sbol3.Sequence, Optional[float]]:
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


def idt_calculate_sequence_complexity_scores(
    accessor: IDTAccountAccessor, sequences: list[sbol3.Sequence]
) -> dict[sbol3.Sequence, float]:
    """Given a list of sequences, compute the complexity scores for any sequences not currently scored
    by sending the sequences to IDT's online service for calculating sequence synthesis complexity.
    Also records the complexity computation with an activity

    :param accessor: IDT API access object
    :param sequences: list of SBOL Sequences to evaluate
    :return: Dictionary mapping Sequences to complexity scores for newly computed sequences
    """
    # Determine which sequences need scores
    need_scores = [
        seq for seq, score in get_complexity_scores(sequences, include_missing=True).items() if score is None
    ]
    if not need_scores:
        return dict()

    # Query for the scores of the sequences
    score_dictionary = accessor.get_sequence_complexity(need_scores)

    # Create report generation activity
    doc = need_scores[0].document
    timestamp = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds') + 'Z'
    report_id = (
        f'{COMPLEXITY_SCORE_NAMESPACE}/Complexity_Report_{timestamp.replace(":", "").replace("-", "")}_'
        f'{str(uuid.uuid4())[0:8]}'
    )
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
    parser.add_argument(
        '-c',
        '--credentials',
        help="""JSON file containing IDT API access credentials.
To obtain access credentials, follow the directions at https://www.idtdna.com/pages/tools/apidoc
The values of the IDT access credentials should be stored in a JSON of the following form:
{ "username": "username", "password": "password", "ClientID": "####", "ClientSecret": "XXXXXXXXXXXXXXXXXXX" }"
""",
    )
    parser.add_argument('--username', help='Username of your IDT account (if not using JSON credentials)')
    parser.add_argument('--password', help='Password of your IDT account (if not using JSON credentials)')
    parser.add_argument('--ClientID', help='ClientID of your IDT account (if not using JSON credentials)')
    parser.add_argument('--ClientSecret', help='ClientSecret of your IDT account (if not using JSON credentials)')
    parser.add_argument('input_file', help='Absolute path to sbol file with sequences')
    parser.add_argument('output_name', help='Name of SBOL file to be written')
    parser.add_argument(
        '-t',
        '--file-type',
        dest='file_type',
        default=sbol3.SORTED_NTRIPLES,
        help='Name of SBOL file to output to (excluding type)',
    )
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0)
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    logging.getLogger().setLevel(
        level=(logging.WARN if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG)
    )
    input_file = args_dict['input_file']
    output_name = args_dict['output_name']

    if args_dict['credentials'] != None:
        with open(args_dict['credentials']) as credentials:
            idt_accessor = IDTAccountAccessor.from_json(json.load(credentials))
    else:
        idt_accessor = IDTAccountAccessor(
            args_dict['username'], args_dict['password'], args_dict['ClientID'], args_dict['ClientSecret']
        )

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
