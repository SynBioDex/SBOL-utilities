import os
import sbol3
from Bio import GenBank, SeqIO
GENBANK_PARSER = GenBank.RecordParser()

# Conversion Constants (NOTE: most are placeholding and temporary for now)
SAMPLE_GB_FILE_1 = "BBa_J23101.gb"          
# Simplest file in genbank consisting only of a singular sequence
SAMPLE_SBOL3_FILE_1 = "BBa_J23101_from_genbank_to_sbol3_direct.nt"
# Temporarily assuming only dna components to be dealt with in genbank files
COMP_TYPES = [sbol3.SBO_DNA]                
# Temporarilty assuming components to only have the engineered_region role
COMP_ROLES = [sbol3.SO_ENGINEERED_REGION]   
GENBANK_FILE_1 = os.path.join(os.path.abspath(os.path.curdir),
                    "test/test_files", SAMPLE_GB_FILE_1)
SBOL3_FILE_1 = os.path.join(os.path.abspath(os.path.curdir),
                    "test/test_files", SAMPLE_SBOL3_FILE_1)

def convert_genbank_to_sbol3(gb_file: str, sbol3_file: str, 
                    namespace: str = "https://testing.sbol3.genbank/", write: bool = False):
    # create sbol3 document, and record parser handler for gb file
    sbol3.set_namespace(namespace)
    doc = sbol3.Document()
    # access records by parsing gb file using SeqIO class
    records = list(SeqIO.parse(gb_file, "genbank").records)
    for record in records:
        # NOTE: Currently we assume only linear or circular topology is possible
        COMP_TYPES.append(sbol3.SO_LINEAR if record.annotations['topology'] == "linear" else sbol3.SO_CIRCULAR)
        comp = sbol3.Component(identity=record.name,
                        types=COMP_TYPES,
                        roles=COMP_ROLES,
                        description=record.description)
        doc.add(comp)
        # NOTE: Currently we use a single method of encoding (IUPAC)
        seq = sbol3.Sequence(identity=record.name + "_sequence",
                        elements=str(record.seq.lower()),
                        encoding=sbol3.IUPAC_DNA_ENCODING)
        doc.add(seq)
        comp.sequences = [seq]
    if write: 
        doc.write(fpath=sbol3_file, file_format=sbol3.SORTED_NTRIPLES)
    return doc


# Currently we don't parse input for gb and sbol3 files (hardcoded)
def main():
    convert_genbank_to_sbol3(gb_file=GENBANK_FILE_1, sbol3_file=SBOL3_FILE_1, write=True)

if __name__ == '__main__':
    main()
