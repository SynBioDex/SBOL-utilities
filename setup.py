import importlib.util
import os

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


def _bundle_validation_data():
    """Copy the SBOLTestSuite rule catalogs and ontology facts into sbol_utilities/validation/data/."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sbol_utilities', 'validation', 'runtime_data.py')
    spec = importlib.util.spec_from_file_location('sbol_utilities_runtime_data', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.bundle()


class BuildPyWithValidationData(build_py):
    """Bundle the validation data before building, so installed packages need no network access."""

    def run(self):
        _bundle_validation_data()
        super().run()


class SdistWithValidationData(sdist):
    """Bundle the validation data before making a source distribution."""

    def run(self):
        _bundle_validation_data()
        super().run()


setup(name='sbol-utilities',
      description='SBOL utilities',
      long_description='SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that '
                       'can be imported as packages or run from the command line.',
      long_description_content_type='text/markdown',
      url='https://github.com/SynBioDex/SBOL-utilities',
      license='MIT License',
      version='1.0a17',
      # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',

            # Indicate who your project is intended for
            'Intended Audience :: Developers',

            # Pick your license as you wish (should match "license" above)
            'License :: OSI Approved :: MIT License',

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13'
      ],
      python_requires='>=3.9',
      # What does your project relate to?
      keywords='synthetic biology',
      install_requires=[
            'sbol3>=1.2',
            'sbol2>=1.4',
            'rdflib>=6.2',
            'biopython',
            'graphviz',
            'tyto>=1.4',
            'openpyxl',
            'requests',
            'sbol_factory>=1.1.2'
            ],
      extras_require={  # requirements for development
          'dev': ['pytest', 'interrogate']
      },
      entry_points={
            'console_scripts': ['excel-to-sbol=sbol_utilities.excel_to_sbol:main',
                                'graph-sbol=sbol_utilities.graph_sbol:main',
                                'sbol-expand-derivations=sbol_utilities.expand_combinatorial_derivations:main',
                                'sbol-calculate-sequences=sbol_utilities.calculate_sequences:main',
                                'sbol-calculate-complexity=sbol_utilities.calculate_complexity_scores:main',
                                'sbol-converter=sbol_utilities.conversion:main',
                                'sbol2-to-sbol3=sbol_utilities.conversion:sbol2to3',
                                'sbol3-to-sbol2=sbol_utilities.conversion:sbol3to2',
                                'sbol-to-genbank=sbol_utilities.conversion:sbol2genbank',
                                'sbol-to-fasta=sbol_utilities.conversion:sbol2fasta',
                                'genbank-to-sbol=sbol_utilities.conversion:genbank2sbol',
                                'fasta-to-sbol=sbol_utilities.conversion:fasta2sbol',
                                'sbol-diff=sbol_utilities.sbol_diff:main']
      },
      packages=find_packages(include=['sbol_utilities', 'sbol_utilities.*']),
      package_data={
          'sbol_utilities': [
              'gb2so.csv',
              'so2gb.csv',
              'validation/data/COMMIT',
              'validation/data/Rules/*.json',
              'validation/data/Ontology/*.tsv',
          ],
      },
      include_package_data=True,
      cmdclass={'build_py': BuildPyWithValidationData, 'sdist': SdistWithValidationData},
      )
