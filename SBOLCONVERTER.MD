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

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Install libraries locally:**

    You may also have to `setuptools` using:
    ```bash
    pip install setuptools
    ```
    
    Install SBOL Utilities locally
    ```bash
    python setup.py install
    ```

5. **Ensure that you are able to run the tests:**
    ```bash
    python test/test_conversion.py
    ```
    