import sbol3
import sbol2


class SBOL2SBOL3Converter:
    @staticmethod
    def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
        """Convert an SBOL3 document to an SBOL2 document

        :param doc3: SBOL3 document to convert
        :returns: SBOL2 document
        """
        doc2 = sbol2.Document()
        # TODO: build converter here
        return doc2

    @staticmethod
    def convert2to3(doc2: sbol2.Document) -> sbol3.Document:
        """Convert an SBOL2 document to an SBOL3 document

        :param doc2: SBOL2 document to convert
        :returns: SBOL3 document
        """
        doc3 = sbol3.Document()
        # TODO: build converter here
        return doc3
