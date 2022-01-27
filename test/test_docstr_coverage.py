"""
    Tests each module, function, classes, methods for presence of docstrings
"""
import unittest
from interrogate import coverage
from interrogate import config

"""
    Setting up test config
"""
print("\nProject Root taken as:")
print(config.find_project_root("."))
print("\nProject Config taken as:")
print(config.find_project_config("."))
print("\nUsing Parsed Project config:   (To changemodify project config file)")
interrogate_config = config.InterrogateConfig(config.parse_pyproject_toml(config.find_project_config(".")))
print(interrogate_config)

"""
    Obtaining and printing results
"""
cov = coverage.InterrogateCoverage(paths=["."], conf=interrogate_config)
results = cov.get_coverage()
print("\nParsed Results:")
cov.print_results(results, None, interrogate_config.color["verbose"])


if __name__ == '__main__':
    unittest.main()
