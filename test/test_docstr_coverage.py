from pathlib import Path
import unittest
from interrogate import coverage
from interrogate import config

class TestDocStringsCoverage(unittest.TestCase):
    def test_using_interrogate(self):
        """Tests each module, function, classes, methods for presence of docstrings"""
        # Parsing config (looks for pyproject.toml by default) 
        project_root = Path(__file__).parent.parent
        toml = config.find_project_config('.')
        interrogate_config: config.InterrogateConfig = config.InterrogateConfig(config.parse_pyproject_toml(toml))
        # Obtaining and printing results
        cov: coverage.InterrogateCoverage = coverage.InterrogateCoverage(paths=[project_root], conf=interrogate_config)
        results: coverage.InterrogateResults = cov.get_coverage()
        # For some reason, fail_under prop occurs twice in `interrogate_config`, and editing it from .toml only updates the second occurence
        interrogate_config.__setattr__("fail_under", interrogate_config.color["fail_under"])
        # return code does not update on its own 
        covered_percent = round((results.covered * 100)/ results.total, 2)
        results.ret_code = covered_percent < interrogate_config.fail_under
        # covered % must satisfy min % set in .toml
        print("\n")
        cov.print_results(results, None, interrogate_config.color["verbose"])
        self.assertGreaterEqual(covered_percent, interrogate_config.fail_under, 'Required minimum percent of code covered by docstrings not achieved.')

if __name__ == '__main__':
    unittest.main()
