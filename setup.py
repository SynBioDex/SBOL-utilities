from setuptools import setup

setup(name='sbol-utilities',
      description='SBOL-utilities',
      version='1.0a1.post0',
      install_requires=[
            'sbol3',
            'graphviz',
            'tyto',
            'openpyxl'
            ],
      scripts=['graph-sbol'],
      entry_points = {
            'console_scripts': ['excel-to-sbol=sbol_utilities.excel_to_sbol:main']
      },
      packages=['sbol_utilities'],
      )
