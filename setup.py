from setuptools import setup

setup(name='sbol-utilities',
      description='SBOL utilities',
      long_description='SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that '
                       'can be imported as packages or run from the command line.',
      long_description_content_type='text/markdown',
      url='https://github.com/SynBioDex/SBOL-utilities',
      license='MIT License',
      version='1.0a15',
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
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10'
      ],
      # What does your project relate to?
      keywords='synthetic biology',
      install_requires=[
            'sbol3>=1.0b11',
            'sbol2>=1.4',
            'rdflib',
            'biopython',
            'graphviz',
            'tyto>=1.0',
            'openpyxl',
            'sbol_factory>=1.0a11'
            ],
      extras_require={  # requirements for development
          'dev': ['pytest', 'interrogate']
      },
      scripts=['graph-sbol'],
      entry_points={
            'console_scripts': ['excel-to-sbol=sbol_utilities.excel_to_sbol:main',
                                'sbol-expand-derivations=sbol_utilities.expand_combinatorial_derivations:main',
                                'sbol-calculate-sequences=sbol_utilities.calculate_sequences:main',
                                'sbol-converter=sbol_utilities.conversion:main',
                                'sbol2to3=sbol_utilities.conversion:sbol2to3',
                                'sbol3to2=sbol_utilities.conversion:sbol3to2',
                                'sbol2genbank=sbol_utilities.conversion:sbol2genbank',
                                'sbol2fasta=sbol_utilities.conversion:sbol2fasta',
                                'genbank2sbol=sbol_utilities.conversion:genbank2sbol',
                                'fasta2sbol=sbol_utilities.conversion:fasta2sbol',
                                'sbol-diff=sbol_utilities.sbol_diff:main']
      },
      packages=['sbol_utilities'],
      package_data={'sbol_utilities': ['sbolgraph-standalone.js']},
      include_package_data=True
      )
