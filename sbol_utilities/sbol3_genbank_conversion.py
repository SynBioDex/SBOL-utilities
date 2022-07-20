import os
import csv
import sbol3
import logging
from typing import List
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from sbol3.constants import SBOL_SEQUENCE_FEATURE

# Conversion Constants (NOTE: most are placeholding and temporary for now)
TEST_NAMESPACE = "https://test.sbol3.genbank/"
# TODO: Temporarily assuming only dna components to be dealt with in genbank files
COMP_TYPES = [sbol3.SBO_DNA]
# TODO: Temporarily assuming components to only have the engineered_region role
COMP_ROLES = [sbol3.SO_ENGINEERED_REGION]
# TODO: Temporarily encoding sequnce objects in IUPUC mode only
SEQUENCE_ENCODING = sbol3.IUPAC_DNA_ENCODING
# Complete file paths to pass as paramteres for testing
SAMPLE_GENBANK_FILE_1 = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.pardir,
        "test/test_files",
        "BBa_J23101.gb",
    )
)
SAMPLE_GENBANK_FILE_2 = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.pardir,
        "test/test_files",
        "iGEM_SBOL2_imports.gb",
    )
)
SAMPLE_SBOL3_FILE_1 = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.pardir,
        "test/test_files",
        "BBa_J23101_from_genbank_to_sbol3_direct.nt",
    )
)
SAMPLE_SBOL3_FILE_2 = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.pardir,
        "test/test_files",
        "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt",
    )
)
GB2SO_MAPPINGS_CSV = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "gb2so.csv"
)
SO2GB_MAPPINGS_CSV = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "so2gb.csv"
)


class GenBank_SBOL3_Converter:
    gb2so_map = {}
    so2gb_map = {}
    default_SO_ontology = "SO:0000110"
    default_GB_ontology = "todo"  # TODO: Whats the default here?

    def create_GB_SO_role_mappings(
        self,
        gb2so_csv: str = GB2SO_MAPPINGS_CSV,
        so2gb_csv: str = SO2GB_MAPPINGS_CSV,
        convert_gb2so: bool = True,
        convert_so2gb: bool = True,
    ):
        """Reads 2 CSV Files containing mappings for converting between GenBank and SO ontologies roles
        :param gb2so_csv: path to read genbank to so conversion csv file
        :param so2gb_csv: path to read so to genbank conversion csv file
        :param convert_gb2so: bool stating whether to read csv for gb2so mappings
        :param convert_so2gb: bool stating whether to read csv for so2gb mappings
        """
        if convert_gb2so:
            logging.info(f"Parsing {gb2so_csv} for GenBank to SO ontology mappings.")
            try:
                with open(gb2so_csv, mode="r") as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        self.gb2so_map[row["GenBank_Ontology"]] = row["SO_Ontology"]
            except FileNotFoundError:
                logging.error(f"No GenBank to SO Ontology Mapping CSV File Exists!")
                return 0
        if convert_so2gb:
            logging.info(f"Parsing {so2gb_csv} for SO to GenBank ontology mappings.")
            try:
                with open(so2gb_csv, mode="r") as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        self.so2gb_map[row["SO_Ontology"]] = row["GenBank_Ontology"]
            except FileNotFoundError:
                logging.error(f"No SO to Genbank Ontology Mapping CSV File Exists!")
                return 0
        return 1

    def convert_genbank_to_sbol3(
        self,
        gb_file: str,
        sbol3_file: str = "sbol3.out",
        namespace: str = TEST_NAMESPACE,
        write: bool = False,
    ) -> sbol3.Document:
        """Convert a GenBank document on disk into an SBOL3 document
        The GenBank document is parsed using BioPython, and corresponding objects of SBOL3 document are created

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
        # create updated py dict to store mappings between gb and so ontologies
        logging.info(
            "Creating GenBank and SO ontologies mappings for sequence feature roles"
        )
        map_created = self.create_GB_SO_role_mappings(
            gb2so_csv=GB2SO_MAPPINGS_CSV, convert_so2gb=False
        )
        if not map_created:
            # TODO: Need better SBOL3-GenBank specific error classes in future
            raise ValueError(
                f"Required CSV data files are not present in your package.\n    Please reinstall the sbol_utilities package.\n \
                Stopping current conversion process.\n    Reverting to legacy converter if new Conversion process is not forced."
            )
        # access records by parsing gb file using SeqIO class
        logging.info(
            f"Parsing Genbank records using SeqIO class.\n    Using GenBank file {gb_file}"
        )
        for record in list(SeqIO.parse(gb_file, "genbank").records):
            # NOTE: Currently we assume only linear or circular topology is possible
            logging.info(f"Parsing record - `{record.id}` in genbank file.")
            if record.annotations["topology"] == "linear":
                extra_comp_types = [sbol3.SO_LINEAR]
            else:
                extra_comp_types = [sbol3.SO_CIRCULAR]
            comp = sbol3.Component(
                identity=record.name,
                types=COMP_TYPES + extra_comp_types,
                roles=COMP_ROLES,
                description=record.description,
            )
            doc.add(comp)
            # NOTE: Currently we use a fixed method of encoding (IUPAC)
            seq = sbol3.Sequence(
                identity=record.name + "_sequence",
                elements=str(record.seq.lower()),
                encoding=SEQUENCE_ENCODING,
            )
            doc.add(seq)
            comp.sequences = [seq]
            # Sending out warnings for genbank info not storeable in sbol3
            for keys in record.annotations:
                logging.warning(
                    f"Extraneous information not storeable in SBOL3 - {keys}: {record.annotations[keys]}"
                )
            if record.features:
                comp.features = []
                for gb_feat in record.features:
                    logging.info(
                        f"Parsing feature `{gb_feat.qualifiers['label'][0]}` for record `{record.id}`"
                    )
                    # create "Range/Cut" FeatureLocation by parsing genbank record location
                    gb_loc = gb_feat.location
                    # Default orientation is "inline" except if complement is specified via strand
                    feat_orientation = sbol3.SO_FORWARD
                    if gb_loc.strand == -1:
                        feat_orientation = sbol3.SO_REVERSE
                    # Create a cut or range as featurelocation depending on whether location is specified as
                    # Cut (eg: "n^n+1", parsed as [n:n] by biopython) or Range (eg: "n..m", parsed as [n:m] by biopython)
                    if gb_loc.start == gb_loc.end:
                        locs = sbol3.Cut(
                            sequence=seq,
                            at=int(gb_loc.start),
                            orientation=feat_orientation,
                        )
                    else:
                        locs = sbol3.Range(
                            sequence=seq,
                            start=int(gb_loc.start),
                            end=int(gb_loc.end),
                            orientation=feat_orientation,
                        )
                    # Obtain sequence feature role from gb2so mappings
                    feat_role = sbol3.SO_NS[:-3]
                    if self.gb2so_map.get(gb_feat.type):
                        feat_role += self.gb2so_map[gb_feat.type]
                    else:
                        feat_role += self.default_SO_ontology
                    feat = sbol3.SequenceFeature(
                        locations=[locs],
                        roles=[feat_role],
                        name=gb_feat.qualifiers["label"][0],
                    )
                    comp.features.append(feat)
        if write:
            logging.info(
                f"Writing created sbol3 document to disk in sorted ntriples format.\n    With path {sbol3_file}"
            )
            doc.write(fpath=sbol3_file, file_format=sbol3.SORTED_NTRIPLES)
        return doc

    def convert_sbol3_to_genbank(
        self,
        sbol3_file: str,
        doc: sbol3.Document = None,
        gb_file: str = "genbank.out",
        write: bool = False,
    ) -> List[SeqRecord]:
        """Convert a SBOL3 document on disk into a GenBank document
        The GenBank document is made using an array of SeqRecords using BioPython, by parsing SBOL3 objects

        :param sbol3_file: path to read SBOL3 file from
        :param gb_file: path to write GenBank file to, if write set to true
        :param write: writes the generated genbank document to provided path
        :return: Array of SeqRecord objects which comprise the generated GenBank document
        """
        if not doc:
            doc = sbol3.Document()
            doc.read(sbol3_file)
        SEQ_RECORDS = []
        logging.info(
            "Creating GenBank and SO ontologies mappings for sequence feature roles"
        )
        # create updated py dict to store mappings between gb and so ontologies
        map_created = self.create_GB_SO_role_mappings(
            so2gb_csv=SO2GB_MAPPINGS_CSV, convert_gb2so=False
        )
        if not map_created:
            # TODO: Need better SBOL3-GenBank specific error classes in future
            raise ValueError(
                f"Required CSV data files are not present in your package.\n    Please reinstall the sbol_utilities package.\n \
                Stopping current conversion process.\n    Reverting to legacy converter if new Conversion process is not forced."
            )
        # consider sbol3 objects which are components
        logging.info(f"Parsing SBOL3 Document components using SBOL3 Document: \n{doc}")
        for obj in doc.objects:
            if isinstance(obj, sbol3.Component):
                logging.info(f"Parsing component - `{obj.display_id}` in sbol3 document.")
                # TODO: can component have multiple sequences? How should we handle Seq objects for those
                obj_seq = doc.find(obj.sequences[0])
                seq = Seq(obj_seq.elements.upper())
                # TODO: "Version" annotation information currently not stored when converted genbank to sbol3
                seq_rec = SeqRecord(
                    seq=seq,
                    id=obj.display_id,
                    description=obj.description,
                    name=obj.display_id,
                )
                # TODO: hardcoded molecule_type as DNA, derivation?
                seq_rec.annotations["molecule_type"] = "DNA"
                # TODO: hardcoded topology as linear, derivation?
                seq_rec.annotations["topology"] = "linear"
                SEQ_REC_FEATURES = []
                if obj.features:
                    # converting all sequence features
                    for obj_feat in obj.features:
                        logging.info(
                            f"Parsing feature `{obj_feat.name}` for component `{obj.display_id}`"
                        )
                        obj_feat_loc = obj_feat.locations[0]
                        feat_strand = 1
                        # feature strand value which denotes orientation of the location of the feature
                        if obj_feat_loc.orientation == sbol3.SO_FORWARD:
                            feat_strand = 1
                        elif obj_feat_loc.orientation == sbol3.SO_REVERSE:
                            feat_strand = -1
                        # TODO: Raise custom converter class ERROR for `else:`
                        feat_loc = FeatureLocation(
                            start=obj_feat_loc.start,
                            end=obj_feat_loc.end,
                            strand=feat_strand,
                        )
                        # FIXME: order of features not same as original genbank doc?
                        obj_feat_role = obj_feat.roles[0]
                        obj_feat_role = obj_feat_role[
                            obj_feat.roles[0].index(":", 6) - 2 :
                        ]
                        # Obtain sequence feature role from so2gb mappings
                        feat_role = self.default_GB_ontology
                        if self.so2gb_map.get(obj_feat_role):
                            feat_role = self.so2gb_map[obj_feat_role]
                        # create sequence feature object with label qualifier
                        feat = SeqFeature(
                            location=feat_loc, strand=feat_strand, type=feat_role
                        )
                        if obj_feat.name:
                            feat.qualifiers["label"] = obj_feat.name
                        # add feature to list of features
                        SEQ_REC_FEATURES.append(feat)
                # Sort features based on feature location start/end, lexicographically
                SEQ_REC_FEATURES.sort(key=lambda feat: (feat.location.start, feat.location.end))
                seq_rec.features = SEQ_REC_FEATURES
                SEQ_RECORDS.append(seq_rec)
        # writing generated genbank document to disk at path provided
        if write:
            logging.info(
                f"Writing created genbank file to disk.\n    With path {gb_file}"
            )
            SeqIO.write(SEQ_RECORDS, gb_file, "genbank")
        return SEQ_RECORDS


# Currently we don't parse input for gb and sbol3 files (hardcoded)
def main():
    log_level = logging.INFO
    logging.getLogger().setLevel(level=log_level)
    converter = GenBank_SBOL3_Converter()
    # converter.convert_genbank_to_sbol3(
    #     gb_file=SAMPLE_GENBANK_FILE_2, sbol3_file=SAMPLE_SBOL3_FILE_2, write=True
    # )
    converter.convert_sbol3_to_genbank(sbol3_file="iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt", write=True)


if __name__ == "__main__":
    main()
