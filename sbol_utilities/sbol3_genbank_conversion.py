import os
import csv
import sbol3
import logging
from Bio import SeqIO
from sbol3.constants import SBOL_SEQUENCE_FEATURE

# Conversion Constants (NOTE: most are placeholding and temporary for now)
TEST_NAMESPACE = "https://test.sbol3.genbank/"
# TODO: Temporarily assuming only dna components to be dealt with in genbank files
COMP_TYPES = [sbol3.SBO_DNA]
# TODO: Temporarily assuming components to only have the engineered_region role
COMP_ROLES = [sbol3.SO_ENGINEERED_REGION]
# TODO: Need to find a way to infer SequenceFeature Range/Cut Orientation from the genbank file
SEQ_FEAT_RANGE_ORIENTATION = "https://identifiers.org/SO:0001030"  # inline orientation
# TODO: Temporarily encoding sequnce objects in IUPUC mode only
SEQUENCE_ENCODING = sbol3.IUPAC_DNA_ENCODING
# Complete file paths to pass as paramteres for testing
SAMPLE_GENBANK_FILE_1 = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                     os.pardir, "test/test_files", "BBa_J23101.gb"))
SAMPLE_GENBANK_FILE_2 = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                     os.pardir, "test/test_files", "iGEM_SBOL2_imports.gb"))
SAMPLE_SBOL3_FILE_1 = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                         os.pardir, "test/test_files", "BBa_J23101_from_genbank_to_sbol3_direct.nt"))
SAMPLE_SBOL3_FILE_2 = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                         os.pardir, "test/test_files", "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"))
SO_SEQ_FEAT_ROLE_NS = "http://identifiers.org/so/"
GB2SO_MAPPINGS_CSV = os.path.join(os.path.dirname(os.path.realpath(__file__)), "gb2so.csv")
SO2GB_MAPPINGS_CSV = os.path.join(os.path.dirname(os.path.realpath(__file__)), "so2gb.csv")


class GenBank_SBOL3_Converter:
    gb2so_map = {}
    so2gb_map = {}
    default_SO_ontology = "SO:0000110"
    default_GB_ontology = "" # TODO: Whats the default here?
    def create_GB_SO_role_mappings(self, gb2so_csv: str = GB2SO_MAPPINGS_CSV, so2gb_csv: str = SO2GB_MAPPINGS_CSV, 
                                   convert_gb2so: bool = True, convert_so2gb: bool = True):
        """Reads 2 CSV Files containing mappings for converting between GenBank and SO ontologies roles
        :param gb2so_csv: path to read genbank to so conversion csv file
        :param so2gb_csv: path to read so to genbank conversion csv file
        :param convert_gb2so: bool stating whether to read csv for gb2so mappings
        :param convert_so2gb: bool stating whether to read csv for so2gb mappings
        """
        if convert_gb2so:
            logging.info("Reading GB to SO ontology mappings csv")
            with open(gb2so_csv, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    self.gb2so_map[row["GenBank_Ontology"]] = row["SO_Ontology"]
        if convert_so2gb:
            logging.info("Reading SO to GB ontology mappings csv")
            with open(so2gb_csv, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    self.so2gb_map[row["SO_Ontology"]] = row["GenBank_Ontology"]


    def convert_genbank_to_sbol3(self, gb_file: str, sbol3_file: str = "sbol3.out", namespace: str =
                                TEST_NAMESPACE, write: bool = False) -> sbol3.Document:
        """Convert a GenBank document on disk into an SBOL3 document
        Specifically, the GenBank document is first imported to SBOL2, then converted from SBOL2 to SBOL3

        :param gb_file: path to read GenBank file from
        :param sbol3_file: path to write SBOL3 file to, if write set to true
        :param namespace: URIs of Components will be set to {namespace}/{genbank_id},
                          defaults to "https://test.sbol3.genbank/" 
        :param write: writes the generated sbol3 document in SORTED_NTRIPLES
                          format to provided sbol3_file path
        :return: SBOL3 document containing converted materials
        """
        # create sbol3 document, and record parser handler for gb file
        sbol3.set_namespace(namespace)
        doc = sbol3.Document()
        # access records by parsing gb file using SeqIO class
        logging.info("Parsing Genbank records using SeqIO class.")
        records = list(SeqIO.parse(gb_file, "genbank").records)
        # create updated py dict to store mappings between gb and so ontologies
        logging.info("Creating GenBank and SO ontologies mappings for sequence feature roles")
        self.create_GB_SO_role_mappings(gb2so_csv=GB2SO_MAPPINGS_CSV, convert_so2gb=False)
        for record in records:
            # NOTE: Currently we assume only linear or circular topology is possible
            extra_comp_types = [sbol3.SO_LINEAR 
                              if record.annotations['topology'] == "linear" else sbol3.SO_CIRCULAR]
            comp = sbol3.Component(identity=record.name,
                                   types=COMP_TYPES + extra_comp_types,
                                   roles=COMP_ROLES,
                                   description=record.description)
            doc.add(comp)
            # NOTE: Currently we use a fixed method of encoding (IUPAC)
            seq = sbol3.Sequence(identity=record.name + "_sequence",
                                 elements=str(record.seq.lower()),
                                 encoding=SEQUENCE_ENCODING)
            doc.add(seq)
            comp.sequences = [seq]
            if record.features:
                comp.features = []
                for i in range(len(record.features)):
                    # create "Range/Cut" FeatureLocation by parsing genbank record location
                    gb_feat = record.features[i]
                    gb_loc = gb_feat.location
                    # Default orientation is "inline" except if complement is specified via strand
                    feat_orientation = SEQ_FEAT_RANGE_ORIENTATION
                    if gb_loc.strand == -1: feat_orientation = "https://identifiers.org/SO:0001031"
                    # Create a cut or range as featurelocation depending on whether location is specified as 
                    # Cut (eg: "n^n+1", parsed as [n:n] by biopython) or Range (eg: "n..m", parsed as [n:m] by biopython)
                    if gb_loc.start == gb_loc.end:
                       # TODO: Biopython parses both "276" (range) and "276^277" (cut) in locations as [276:276], distinction?
                        locs = sbol3.Cut(sequence=seq, at=int(gb_loc.start), orientation=feat_orientation)
                    else:
                        locs = sbol3.Range(sequence=seq, start=int(gb_loc.start),
                                           end=int(gb_loc.end), orientation=feat_orientation)
                    # TODO: Add defaults below if mappings are not found / key does not exist
                    # Obtain sequence feature role from gb2so mappings
                    feat_role = SO_SEQ_FEAT_ROLE_NS
                    if self.gb2so_map.get(record.features[i].type):
                        feat_role += self.gb2so_map[record.features[i].type]
                    else:
                        logging.info(i)
                        feat_role += self.default_SO_ontology
                    feat = sbol3.SequenceFeature(locations=[locs], 
                                                 roles=[feat_role],
                                                 name=gb_feat.qualifiers['label'][0])
                    comp.features.append(feat)
        if write:
            logging.info("Writing created sbol3 document to disk.")
            doc.write(fpath=sbol3_file, file_format=sbol3.SORTED_NTRIPLES)
        return doc


# Currently we don't parse input for gb and sbol3 files (hardcoded)
def main():
    log_level = logging.INFO
    logging.getLogger().setLevel(level=log_level)
    converter = GenBank_SBOL3_Converter()
    converter.convert_genbank_to_sbol3(gb_file=SAMPLE_GENBANK_FILE_2, sbol3_file=SAMPLE_SBOL3_FILE_2, write=True)


if __name__ == '__main__':
    main()
