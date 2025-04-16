# Contributing to SBOL Converter

This document outlines the process for contributing to the SBOL Converter project. We welcome contributions of all kinds, including bug fixes, new features, and improvements to documentation.

## Table of Contents

-   [Finding Issues](#finding-issues)
-   [Code Location](#code-location)
-   [Local Installation](#local-installation)
-   [Writing Tests](#writing-tests)

## Finding Issues

-   **GitHub Issues:** The primary place to find issues is on the [SBOL-utilities GitHub repository](https://github.com/SynBioDex/SBOL-utilities/issues?q=is%3Aissue%20state%3Aopen%20%22SBOL%202-3%20converter%22%20label%3Asbol-converter).
-   **Issue Labels:** Issues are labeled to help you find relevant tasks. Look for labels like `sbol-converter`.

## Code Location

The SBOL Converter code is located within the `sbol-utilities` repository.
- The core code for the converter is located in the `sbol_utilities/sbol3_sbol2_conversion.py` file.
- The tests for the converter are located in the `test/test_sbol2_sbol3_direct.py` directory.

## Local Installation

To work on the SBOL Converter, you'll need to install it locally. Follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/SynBioDex/SBOL-utilities.git
    cd SBOL-utilities
    ```

2.  **Create a virtual environment and activate it:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **Install libraries locally:**

    You may also have to `setuptools` using:
    ```bash
    pip install setuptools
    ```
    
    Install SBOL Utilities locally
    ```bash
    python setup.py install
    ```

4. **Ensure that you are able to run the tests:**
    ```bash
    python test/test_sbol2_sbol3_direct.py
    ```

## Writing Tests

It's recommended that you prepare a test and a test file before starting to write your converter code.

To make a new test:

- Take a file from [SBOL Test Suite](https://github.com/SynBioDex/SBOLTestSuite), or make one using pySBOL2 (suggested: use the existing [SBOL Notebooks](https://github.com/SynBioDex/SBOL-Notebooks))

- In case you're using pySBOL2, make sure to have these configurations:
    ```
    Config.setOption(ConfigOptions.SBOL_COMPLIANT_URIS, True)
    Config.setOption(ConfigOptions.SBOL_TYPED_URIS, False)
    ```

- Validate the file with the [online Validator](https://validator.sbolstandard.org/). It shouldn't throw any validation errors

- Put the file in the `test/test_files`

- Write a new test function in `test_sbol2_sbol3_direct.py` (follow what the other tests are doing: create a document based on the file, call conversion, convert back to original SBOL version, and check for differences)
