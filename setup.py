from setuptools import setup

setup(name='sbol-utilities',
      description='SBOL utilities',
      long_description='SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that '
                       'can be imported as packages or run from the command line.',
      long_description_content_type='text/markdown',
      url='https://github.com/SynBioDex/SBOL-utilities',
      license='MIT License',
      version='1.0a8',
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
            'Programming Language :: Python :: 3 :: Only'
      ],
      # What does your project relate to?
      keywords='synthetic biology',
      install_requires=[
            'sbol3==1.0b5',
            'graphviz',
            'tyto',
            'openpyxl'
            ],
      scripts=['graph-sbol'],
      entry_points = {
            'console_scripts': ['excel-to-sbol=sbol_utilities.excel_to_sbol:main',
                                'sbol-expand-derivations=sbol_utilities.expand_combinatorial_derivations:main',
                                'sbol-calculate-sequences=sbol_utilities.calculate_sequences:main']
      },
      packages=['sbol_utilities'],
      )
