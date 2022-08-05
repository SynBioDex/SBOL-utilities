import os
import csv
import math
import sbol3
import rdflib
import logging
from typing import List, Sequence, Union, Optional, Any
from sbol3 import ListProperty, Property
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation, Reference, CompoundLocation
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
    DEFAULT_SO_TERM = "SO:0000110"
    DEFAULT_GB_TERM = "misc_feature"
    BIO_STRAND_FORWARD = 1
    BIO_STRAND_REVERSE = -1
    DEFAULT_GB_REC_VERSION = 1

    def __init__(self) -> None:
        def build_component_genbank_extension(*, identity, type_uri) -> GenBank_SBOL3_Converter.Component_GenBank_Extension:
            """A builder function to be called by the SBOL3 parser
            when it encounters a Component in an SBOL file.
            :param identity: identity for new component class instance to have
            :param type_uri: type_uri for new component class instance to have
            """
            # `types` is required and not known at build time.
            # Supply a missing value to the constructor, then clear
            # the missing value before returning the built object.
            obj = self.Component_GenBank_Extension(identity=identity, types=[sbol3.PYSBOL3_MISSING], type_uri=type_uri)
            # Remove the placeholder value
            obj.clear_property(sbol3.SBOL_TYPE)
            return obj
        # set up logging
        log_level = logging.INFO
        logging.getLogger().setLevel(level=log_level)
        # Register the builder function so it can be invoked by
        # the SBOL3 parser to build objects with a Component type URI
        sbol3.Document.register_builder(sbol3.SBOL_COMPONENT, build_component_genbank_extension)

    class Component_GenBank_Extension(sbol3.Component):
        """Overrides the sbol3 Component class to include fields to directly read and write 
        extraneous properties of GenBank not storeable in any SBOL3 datafield.
        :extends: sbol3.Component class
        """
        GENBANK_EXTRA_PROPERTY_NS = "http://www.ncbi.nlm.nih.gov/genbank"
        def __init__(self, identity: str, types: Optional[Union[str, Sequence[str]]], **kwargs) -> None:
            # instantiating sbol3 component object
            super().__init__(identity=identity, types=types, **kwargs)
            # Setting properties for GenBank's extraneous properties not settable in any SBOL3 field.
            self.genbank_date          = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#date"    , 0, 1)
            self.genbank_division      = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#division", 0, 1)
            self.genbank_keywords      = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#keywords", 0, 1)
            self.genbank_locus         = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#locus"   , 0, 1)
            self.genbank_molecule_type = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#molecule", 0, 1)
            self.genbank_organism      = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#organism", 0, 1)
            self.genbank_source        = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#source"  , 0, 1)
            # there can be multiple taxonomy, thus upper bound needs to be > 1 in order to use TextListProperty
            self.genbank_taxonomy      = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#taxonomy", 0, math.inf)
            self.genbank_reference_authors = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#authors", 0, math.inf)
            self.genbank_reference_comment = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#comment", 0, math.inf)
            self.genbank_reference_journal = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#journal", 0, math.inf)
            self.genbank_reference_consrtm = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#consrtm", 0, math.inf)
            self.genbank_reference_title = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#title", 0, math.inf)
            self.genbank_reference_medline_id = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#medline_id", 0, math.inf)
            self.genbank_reference_pubmed_id = sbol3.TextProperty(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference#pubmed_id", 0, math.inf)
            # self.genbank_references    = self.ReferenceProperty(self.GENBANK_EXTRA_PROPERTY_NS + "#reference")
        #     self.genbank_references    = self.REFERENCE_Property(self, f"{self.GENBANK_EXTRA_PROPERTY_NS}#reference", 0, 2)
        #
        # class ReferenceProperty:
        #     def __init__(self, GENBANK_EXTRA_PROPERTY_NS: str, Property_Owner: Any) -> None:
        #         self.authors = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#author", 0, 1)
        #         self.comment = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#comment", 0, 1)
        #         self.journal = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#journal", 0, 1)
        #         self.consrtm = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#consrtm", 0, 1)
        #         self.title = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#title", 0, 1)
        #         self.medline_id = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#medline_id", 0, 1)
        #         self.pubmed_id = sbol3.TextProperty(Property_Owner, f"{GENBANK_EXTRA_PROPERTY_NS}#pubmed_id", 0, 1)
        #         # self.location = 
        #        
        #
        # class ReferencePropertyMixin:
        #     def from_user(self, value: Any) -> Union[None, rdflib.Literal]:
        #         if value is None:
        #             return None
        #         # return value
        #         # if not isinstance(value, str):
        #         #     raise TypeError(f'Expecting string, got {type(value)}')
        #         rdflib.PROV
        #         return rdflib.Literal(value)
        #     def to_user(self, value: Any) -> str:
        #         # return str(value)
        #         return str(value)
        # class ReferenceListProperty(ReferencePropertyMixin, ListProperty):
        #     def __init__(self, property_owner: Any, property_uri: str,
        #                  lower_bound: int, upper_bound: int,
        #                  validation_rules: Optional[List] = None,
        #                  initial_value: Optional[str] = None):
        #         super().__init__(property_owner, property_uri,
        #                          lower_bound, upper_bound, validation_rules)
        #         if initial_value is not None:
        #             if isinstance(initial_value, str):
        #                 # Wrap the singleton in a list
        #                 initial_value = [initial_value]
        #             self.set(initial_value)
        # def REFERENCE_Property(self, property_owner: Any, property_uri: str,
        #                  lower_bound: int, upper_bound: Union[int, float],
        #                  validation_rules: Optional[List] = None,
        #                  initial_value: Optional[Union[str, List[str]]] = None
        #                  # ) -> Union[str, list[str], Property]:
        #                  ):
        #     return self.ReferenceListProperty(property_owner, property_uri,
        #                             lower_bound, upper_bound,
        #                             validation_rules, initial_value)

    def create_GB_SO_role_mappings(self, gb2so_csv: str = GB2SO_MAPPINGS_CSV, so2gb_csv: str = SO2GB_MAPPINGS_CSV,
                                   convert_gb2so: bool = True, convert_so2gb: bool = True) -> int:
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

    def convert_genbank_to_sbol3(self, gb_file: str, sbol3_file: str = "sbol3.out", namespace: str = TEST_NAMESPACE,
                                 write: bool = False) -> sbol3.Document:
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
                "Required CSV data files are not present in your package.\n    Please reinstall the sbol_utilities package.\n \
                Stopping current conversion process.\n    Reverting to legacy converter if new Conversion process is not forced."
            )
        # access records by parsing gb file using SeqIO class
        logging.info(
            f"Parsing Genbank records using SeqIO class.\n    Using GenBank file {gb_file}"
        )
        for record in list(SeqIO.parse(gb_file, "genbank").records):
            # TODO: Currently we assume only linear or circular topology is possible
            logging.info(f"Parsing record - `{record.id}` in genbank file.")
            if record.annotations["topology"] == "linear":
                extra_comp_types = [sbol3.SO_LINEAR]
            else:
                extra_comp_types = [sbol3.SO_CIRCULAR]
            # creating component extended Component class to include GenBank extraneous properties
            comp = self.Component_GenBank_Extension(
                identity=record.name,
                types=COMP_TYPES + extra_comp_types,
                roles=COMP_ROLES,
                description=record.description,
            )
            doc.add(comp)
            # Setting properties for GenBank's extraneous properties not settable in any SBOL3 field.
            # 1. GenBank Record Date
            # TODO: Let it be able to accept date into sbol3.DateTimeProperty() instead
            comp.genbank_date = record.annotations['date']
            # 2. GenBank Record Division
            comp.genbank_division = record.annotations['data_file_division']
            # 3. GenBank Record Keywords
            # TODO: Keywords are a list, need to use another property type
            comp.genbank_keywords = record.annotations['keywords'][0]
            # 4. GenBank Record Locus
            # TODO: BioPython's parsing doesn't explicitly place a "locus" datafield?
            comp.genbank_locus = record.name
            # 5. GenBank Record Molecule Type
            comp.genbank_molecule_type = record.annotations['molecule_type']
            # 6. GenBank Record Organism
            comp.genbank_organism = record.annotations['organism']
            # 7. GenBank Record Source
            comp.genbank_source = record.annotations['source']
            # 8. GenBank Record Taxonomy
            comp.genbank_taxonomy = sorted(record.annotations['taxonomy'])
            # 9. GenBank Record References
            # record_references = []
            # if record.annotations['references']:
            if 'references' in record.annotations:
                for index in range(len(record.annotations['references'])):
                    reference = record.annotations['references'][index]
                    print(reference)
                    comp.genbank_reference_authors.append(f"{index+1}:" + reference.authors)
                    comp.genbank_reference_comment.append(f"{index+1}:" + reference.comment)
                    comp.genbank_reference_journal.append(f"{index+1}:" + reference.journal)
                    comp.genbank_reference_title.append(f"{index+1}:" + reference.title)
                    comp.genbank_reference_consrtm.append(f"{index+1}:" + reference.consrtm)
                    comp.genbank_reference_medline_id.append(f"{index+1}:" + reference.medline_id)
                    comp.genbank_reference_pubmed_id.append(f"{index+1}:" + reference.pubmed_id)
            # comp.genbank_references = record_references
            # print(comp.genbank_reference_authors)
            # TODO: Currently we use a fixed method of encoding (IUPAC)
            seq = sbol3.Sequence(
                identity=record.name + "_sequence",
                elements=str(record.seq.lower()),
                encoding=SEQUENCE_ENCODING,
            )
            doc.add(seq)
            comp.sequences = [seq]
            # Sending out warnings for genbank info not storeable in sbol3
            # TODO: Have them stored as properties for a SBOL3 Component under a different ncbi namespace, as the old converter does.
            for keys in record.annotations:
                logging.warning(
                    f"Extraneous information not storeable in SBOL3 - {keys}: {record.annotations[keys]}"
                )
            if record.features:
                comp.features = []
                for gb_feat in record.features:
                    feat_locations = []
                    logging.info(
                        f"Parsing feature `{gb_feat.qualifiers['label'][0]}` for record `{record.id}`"
                    )
                    for gb_loc in gb_feat.location.parts:
                        # Default orientation is "inline" except if complement is specified via strand
                        feat_loc_orientation = sbol3.SO_FORWARD
                        if gb_loc.strand == -1:
                            feat_loc_orientation = sbol3.SO_REVERSE
                        # create "Range/Cut" FeatureLocation by parsing genbank record location
                        # Create a cut or range as featurelocation depending on whether location is specified as
                        # Cut (eg: "n^n+1", parsed as [n:n] by biopython) or Range (eg: "n..m", parsed as [n:m] by biopython)
                        if gb_loc.start == gb_loc.end:
                            locs = sbol3.Cut(
                                sequence=seq,
                                at=int(gb_loc.start),
                                orientation=feat_loc_orientation,
                            )
                        else:
                            locs = sbol3.Range(
                                sequence=seq,
                                start=int(gb_loc.start),
                                end=int(gb_loc.end),
                                orientation=feat_loc_orientation,
                            )
                        feat_locations.append(locs)
                    # Obtain sequence feature role from gb2so mappings
                    feat_role = sbol3.SO_NS[:-3]
                    if self.gb2so_map.get(gb_feat.type):
                        feat_role += self.gb2so_map[gb_feat.type]
                    else:
                        logging.warning(f"Feature type: `{gb_feat.type}` for feature: `{gb_feat.qualifiers['label'][0]}` of record: `{record.name}` has no corresponding ontology term for SO, using the default SO term, {self.DEFAULT_SO_TERM}")
                        feat_role += self.DEFAULT_SO_TERM
                    feat_orientation = sbol3.SO_FORWARD
                    if gb_feat.strand == -1:
                        feat_orientation = sbol3.SO_REVERSE
                    feat = sbol3.SequenceFeature(
                        locations=feat_locations,
                        roles=[feat_role],
                        name=gb_feat.qualifiers["label"][0],
                        orientation=feat_orientation
                    )
                    comp.features.append(feat)
        if write:
            logging.info(
                f"Writing created sbol3 document to disk in sorted ntriples format.\n    With path {sbol3_file}"
            )
            doc.write(fpath=sbol3_file, file_format=sbol3.SORTED_NTRIPLES)
        return doc

    def convert_sbol3_to_genbank(self, sbol3_file: str, doc: sbol3.Document = None, gb_file: str = "genbank.out",
                                 write: bool = False) -> List[SeqRecord]:
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
        seq_records = []
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
                # NOTE: A single component/record cannot have multiple sequences
                seq = None # If no sequence is found for a component
                if obj.sequences and len(obj.sequences) == 1:
                    obj_seq = doc.find(obj.sequences[0])
                    seq = Seq(obj_seq.elements.upper())
                elif len(obj.sequences) > 1:
                    raise ValueError(f"Component `{obj.display_id}` of given SBOL3 document has more than 1 sequnces (`{len(obj.sequences)}`). This is invalid; a component may only have 1 or 0 sequences.")
                # TODO: "Version" annotation information currently not stored when converted genbank to sbol3
                seq_rec = SeqRecord(
                    seq=seq,
                    id=obj.display_id,
                    description=obj.description,
                    name=obj.display_id,
                )
                # Resetting extraneous genbank properties from extended component-genbank class
                # TODO: check if these fields are actually getting reset; apparently they are still using defaults
                if isinstance(obj, self.Component_GenBank_Extension):
                    # 1. GenBank Record Date
                    seq_rec.annotations['date'] = obj.genbank_date
                    # 2. GenBank Record Division
                    seq_rec.annotations['data_file_division'] = obj.genbank_division
                    # 3. GenBank Record Keywords
                    # TODO: Keywords are a list, need to use another property type
                    # seq_rec.annotations['keywords'] = obj.genbank_keywords
                    # 4. GenBank Record Locus
                    # TODO: No explicit way to set locus via BioPython?
                    # 5. GenBank Record Molecule Type
                    seq_rec.annotations['molecule_type'] = obj.genbank_molecule_type
                    # 6. GenBank Record Organism
                    seq_rec.annotations['organism'] = obj.genbank_organism
                    # 7. GenBank Record Source
                    # FIXME: Apparently, if a default source was used during in the GenBank file
                    #        during conversion of GenBank -> SBOL, component.genbank_source is "", 
                    #        and while plugging it back in during conversion of SBOL -> GenBank, it
                    #        simply prints "", whereas the default "." should have been printed
                    if obj.genbank_source != "": seq_rec.annotations['source'] = obj.genbank_source
                    # 8. GenBank Record taxonomy
                    # FIXME: Even though component.genbank_taxonomy is stored in sorted order, it 
                    #        becomes unsorted while retrieving from the sbol file
                    seq_rec.annotations['taxonomy'] = sorted(list(obj.genbank_taxonomy))
                    # 9. GenBank Record References
                    record_references = []
                    list(obj.genbank_reference_authors).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_comment).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_title).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_journal).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_consrtm).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_pubmed_id).sort(key=lambda value: value.split(":", 1)[0])
                    list(obj.genbank_reference_medline_id).sort(key=lambda value: value.split(":", 1)[0])
                    for index in range(len(obj.genbank_reference_journal)):
                        reference = Reference()
                        reference.authors = list(obj.genbank_reference_authors)[index].split(":", 1)[1]
                        reference.comment = list(obj.genbank_reference_comment)[index].split(":", 1)[1]
                        reference.journal = list(obj.genbank_reference_journal)[index].split(":", 1)[1]
                        reference.title = list(obj.genbank_reference_title)[index].split(":", 1)[1]
                        reference.consrtm = list(obj.genbank_reference_consrtm)[index].split(":", 1)[1]
                        reference.medline_id = list(obj.genbank_reference_medline_id)[index].split(":", 1)[1]
                        reference.pubmed_id = list(obj.genbank_reference_pubmed_id)[index].split(":", 1)[1]
                        record_references.append(reference)
                    seq_rec.annotations['references'] = record_references

                # TODO: hardcoded molecule_type as DNA, derivation?
                seq_rec.annotations["molecule_type"] = "DNA"
                # TODO: hardcoded topology as linear, derivation?
                seq_rec.annotations["topology"] = "linear"
                # TODO: temporalily hardcoding version as "1"
                # FIXME: Version still not being displayed on record's VERSION
                seq_rec.annotations["sequence_version"] = self.DEFAULT_GB_REC_VERSION
                seq_rec_features = []
                if obj.features:
                    feat_order = {}
                    # converting all sequence features
                    for obj_feat in obj.features:
                        # TODO: Also add ability to parse subcomponent feature type
                        # Note: Currently we only parse sequence features from sbol3 to genbank
                        if isinstance(obj_feat, sbol3.SequenceFeature):
                            logging.info(
                                f"Parsing feature `{obj_feat.name}` for component `{obj.display_id}`"
                            )
                            # TODO: There may be multiple locations for a feature from sbol3; 
                            #       add ability to parse them into a single genbank feature
                            feat_loc_parts = []
                            feat_loc_object = None
                            feat_loc_positions = []
                            feat_strand = self.BIO_STRAND_FORWARD
                            for obj_feat_loc in obj_feat.locations:
                                feat_strand = self.BIO_STRAND_FORWARD
                                # feature strand value which denotes orientation of the location of the feature
                                # By default its 1 for SO_FORWARD orientation of sbol3 feature location, and -1 for SO_REVERSE
                                if obj_feat_loc.orientation == sbol3.SO_REVERSE:
                                    feat_strand = self.BIO_STRAND_REVERSE
                                elif obj_feat_loc.orientation != sbol3.SO_FORWARD:
                                    raise ValueError(f"Location orientation: `{obj_feat_loc.orientation}` for feature: `{obj_feat.name}` of component: `{obj.display_id}` is not a valid orientation.\n Valid orientations are `{sbol3.SO_FORWARD}`, `{sbol3.SO_REVERSE}`")
                                # TODO: Raise custom converter class ERROR for `else:`
                                feat_loc_object = FeatureLocation(
                                    start=obj_feat_loc.start,
                                    end=obj_feat_loc.end,
                                    strand=feat_strand,
                                )
                                feat_loc_parts.append(feat_loc_object)
                            # sort feature locations lexicographically internally first
                            # NOTE: If the feature location has an outer "complement" location operator, the sort needs to be in reverse order
                            if obj_feat.orientation == sbol3.SO_REVERSE:
                                feat_loc_parts.sort(key=lambda loc: (loc.start, loc.end), reverse=True)
                            else:
                                feat_loc_parts.sort(key=lambda loc: (loc.start, loc.end))
                            for loc in feat_loc_parts:
                                feat_loc_positions += [loc.start, loc.end]
                            if len(feat_loc_parts) > 1:
                                feat_loc_object = CompoundLocation(parts=feat_loc_parts, operator="join")
                            elif len(feat_loc_parts) == 1:
                                feat_loc_object = feat_loc_parts[0]
                            # action to perform if no location found?
                            # else:

                            # FIXME: order of features not same as original genbank doc?
                            obj_feat_role = obj_feat.roles[0]
                            # NOTE: The so2gb.csv data file has rows of format 'SO:xxxxxxx,<GenBank_Term>', 
                            # and the obj_feat_role returns the URI (i.e 'https://identifiers.org/SO:xxxxxx').
                            # The slicing and subtracting is done to obtain the 'SO:xxxxxxx' portion from the URI.
                            obj_feat_role = obj_feat_role[
                                obj_feat_role.index(":", 6) - 2 :
                            ]
                            # Obtain sequence feature role from so2gb mappings
                            feat_role = self.DEFAULT_GB_TERM
                            if self.so2gb_map.get(obj_feat_role):
                                feat_role = self.so2gb_map[obj_feat_role]
                            else:
                                logging.warning(f"Feature role: `{obj_feat_role}` for feature: `{obj_feat}` of component: `{obj.display_id}` has no corresponding ontology term for GenBank, using the default GenBank term, {self.DEFAULT_GB_TERM}")
                            # create sequence feature object with label qualifier
                            # TODO: feat_strand value ambiguous in case of mulitple locations?
                            feat = SeqFeature(
                                location=feat_loc_object, strand=feat_strand, type=feat_role
                            )
                            feat_order[feat] = feat_loc_positions
                            if obj_feat.name:
                                feat.qualifiers["label"] = obj_feat.name
                            # add feature to list of features
                            seq_rec_features.append(feat)
                # Sort features based on feature location start/end, lexicographically
                seq_rec_features.sort(key=lambda feat: feat_order[feat])
                seq_rec.features = seq_rec_features
                seq_records.append(seq_rec)
        # writing generated genbank document to disk at path provided
        if write:
            logging.info(
                f"Writing created genbank file to disk.\n    With path {gb_file}"
            )
            SeqIO.write(seq_records, gb_file, "genbank")
        return seq_records

