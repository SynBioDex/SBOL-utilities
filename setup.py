from setuptools import setup

setup(name='sbol-utilities',
      description='SBOL-utilities',
      long_description='SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that '
                       'can be imported as packages or run from the command line.',
      long_description_content_type='text/markdown',
      version='1.0a5',
      install_requires=[
            'sbol3',
            'graphviz',
            'tyto',
            'openpyxl'
            ],
      scripts=['graph-sbol'],
      entry_points = {
            'console_scripts': ['excel-to-sbol=sbol_utilities.excel_to_sbol:main',
                                'sbol-expand-derivations=sbol_utilities.expand_combinatorial_derivations:main']
      },
      packages=['sbol_utilities'],
      )
