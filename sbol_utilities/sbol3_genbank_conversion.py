import os
import sbol3
import csv
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
SAMPLE_GENBANK_FILE_1 = os.path.join(os.path.abspath(os.path.curdir), 
                                "test/test_files", "BBa_J23101.gb")
SAMPLE_SBOL3_FILE_1 = os.path.join(os.path.abspath(os.path.curdir), "test/test_files",
                                "BBa_J23101_from_genbank_to_sbol3_direct.nt")
SAMPLE_GENBANK_FILE_2 = os.path.join(os.path.abspath(os.path.curdir), "test/test_files",
                                "iGEM_SBOL2_imports.gb")
SAMPLE_SBOL3_FILE_2 = os.path.join(os.path.abspath(os.path.curdir), "test/test_files",
                                "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt")
GB2SO_MAPPINGS = {}
SO2GB_MAPPINGS = {}
SO_SEQ_FEAT_ROLE_NS = "http://identifiers.org/so/"
GB2SO_MAPPINGS_CSV = os.path.join(os.path.abspath(os.path.curdir), "gb2so.csv")
SO2GB_MAPPINGS_CSV = os.path.join(os.path.abspath(os.path.curdir), "so2gb.csv")


class GenBank_SBOL3_Converter:
    def create_GB2SO_role_mappings(self, gb2so_csv: str = GB2SO_MAPPINGS_CSV, so2gb_csv: str = SO2GB_MAPPINGS_CSV):
        """Reads 2 CSV Files containing mappings for converting between GenBank and SO ontologies roles
        :param gb2so_csv: path to read genbank to so conversion csv file
        :param so2gb_csv: path to read so to genbank conversion csv file
        """
        with open(gb2so_csv, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                GB2SO_MAPPINGS[row["GenBank_Ontology"]] = row["SO_Ontology"]
        with open(so2gb_csv, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                SO2GB_MAPPINGS[row["SO_Ontology"]] = row["GenBank_Ontology"]


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
        records = list(SeqIO.parse(gb_file, "genbank").records)
        for record in records:
            # NOTE: Currently we assume only linear or circular topology is possible
            COMP_TYPES.append(sbol3.SO_LINEAR 
                              if record.annotations['topology'] == "linear" else sbol3.SO_CIRCULAR)
            comp = sbol3.Component(identity=record.name,
                                   types=COMP_TYPES,
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
                # create updated py dict to store mappings between gb and so ontologies
                self.create_GB2SO_role_mappings(gb2so_csv=GB2SO_MAPPINGS_CSV, so2gb_csv=SO2GB_MAPPINGS_CSV)
                comp.features = []
                for i in range(len(record.features)):
                    # create "Range" FeatureLocation by parsing genbank record location
                    gb_feat = record.features[i]
                    gb_loc = gb_feat.location
                    # adding roles to feature?
                    locs = sbol3.Range(sequence=seq, start=int(gb_loc.start),
                                       end=int(gb_loc.end), orientation=SEQ_FEAT_RANGE_ORIENTATION)
                    # Obtain sequence feature role from gb2so mappings
                    feat_role = GB2SO_MAPPINGS[record.features[i].type]
                    feat_role = SO_SEQ_FEAT_ROLE_NS + feat_role
                    feat = sbol3.SequenceFeature(locations=[locs], 
                                                 roles=feat_role,
                                                 name=gb_feat.qualifiers['label'][0])
                    comp.features.append(feat)
        if write:
            doc.write(fpath=sbol3_file, file_format=sbol3.SORTED_NTRIPLES)
        return doc


# Currently we don't parse input for gb and sbol3 files (hardcoded)
def main():
    converter = GenBank_SBOL3_Converter()
    converter.convert_genbank_to_sbol3(gb_file=SAMPLE_GENBANK_FILE_2, sbol3_file=SAMPLE_SBOL3_FILE_2, write=True)


if __name__ == '__main__':
    main()
