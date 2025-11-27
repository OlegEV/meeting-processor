#!/usr/bin/env python3
"""
Test runner script for Confluence integration test suite
"""

import os
import sys
import argparse
import subprocess
import time
from typing import List, Dict, Any


class TestRunner:
    """Test runner for Confluence integration tests"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.tests_dir = os.path.join(self.project_root, 'tests')
        
        # Test categories
        self.test_categories = {
            'unit': [
                'tests/test_database_models.py',
                'tests/test_confluence_client.py',
                'tests/test_confluence_encryption.py'
            ],
            'integration': [
                'tests/test_database_integration.py',
                'tests/test_flask_integration.py'
            ],
            'security': [
                'tests/test_security.py'
            ],
            'frontend': [
                'tests/test_frontend_ui.py'
            ],
            'performance': [
                'tests/test_performance.py'
            ],
            'e2e': [
                'tests/test_end_to_end.py'
            ]
        }
    
    def run_command(self, command: List[str], capture_output: bool = False) -> Dict[str, Any]:
        """Run a command and return results"""
        print(f"Running: {' '.join(command)}")
        
        start_time = time.time()
        
        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
            else:
                result = subprocess.run(
                    command,
                    cwd=self.project_root,
                    timeout=300
                )
            
            execution_time = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'execution_time': execution_time,
                'stdout': result.stdout if capture_output else None,
                'stderr': result.stderr if capture_output else None
            }
            
        except subprocess.TimeoutExpired:
            print("Command timed out after 5 minutes")
            return {
                'success': False,
                'returncode': -1,
                'execution_time': time.time() - start_time,
                'stdout': None,
                'stderr': "Command timed out"
            }
        except Exception as e:
            print(f"Error running command: {e}")
            return {
                'success': False,
                'returncode': -1,
                'execution_time': time.time() - start_time,
                'stdout': None,
                'stderr': str(e)
            }
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        print("Checking dependencies...")
        
        required_packages = [
            'pytest',
            'coverage',
            'selenium',
            'psutil'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"✗ {package} (missing)")
        
        if missing_packages:
            print(f"\nMissing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("All dependencies satisfied!")
        return True
    
    def run_tests(self, categories: List[str] = None, coverage: bool = False, 
                  verbose: bool = False, parallel: bool = False) -> bool:
        """Run tests for specified categories"""
        
        if not self.check_dependencies():
            return False
        
        # Determine which tests to run
        if categories:
            test_files = []
            for category in categories:
                if category in self.test_categories:
                    test_files.extend(self.test_categories[category])
                else:
                    print(f"Unknown test category: {category}")
                    return False
        else:
            # Run all tests
            test_files = []
            for category_files in self.test_categories.values():
                test_files.extend(category_files)
        
        # Build pytest command
        command = ['python', '-m', 'pytest']
        
        # Add test files
        command.extend(test_files)
        
        # Add options
        if verbose:
            command.append('-v')
        
        if parallel:
            command.extend(['-n', 'auto'])
        
        if coverage:
            command.extend([
                '--cov=.',
                '--cov-report=html',
                '--cov-report=term',
                '--cov-report=xml'
            ])
        
        # Run tests
        print(f"\nRunning tests: {', '.join(categories) if categories else 'all'}")
        print("=" * 60)
        
        result = self.run_command(command)
        
        print("=" * 60)
        print(f"Test execution completed in {result['execution_time']:.2f} seconds")
        
        if result['success']:
            print("✓ All tests passed!")
            
            if coverage:
                print("\nCoverage report generated:")
                print("- HTML: htmlcov/index.html")
                print("- XML: coverage.xml")
        else:
            print("✗ Some tests failed!")
        
        return result['success']
    
    def run_quick_tests(self) -> bool:
        """Run quick tests (unit tests only)"""
        print("Running quick test suite (unit tests only)...")
        return self.run_tests(['unit'], verbose=True)
    
    def run_full_tests(self) -> bool:
        """Run full test suite with coverage"""
        print("Running full test suite with coverage...")
        return self.run_tests(coverage=True, verbose=True)
    
    def run_security_tests(self) -> bool:
        """Run security tests only"""
        print("Running security test suite...")
        return self.run_tests(['security'], verbose=True)
    
    def run_performance_tests(self) -> bool:
        """Run performance tests only"""
        print("Running performance test suite...")
        return self.run_tests(['performance'], verbose=True)
    
    def generate_coverage_report(self) -> bool:
        """Generate coverage report without running tests"""
        print("Generating coverage report...")
        
        command = [
            'python', '-m', 'pytest',
            '--cov=.',
            '--cov-report=html',
            '--cov-report=term',
            '--cov-report=xml',
            '--cov-only'
        ]
        
        result = self.run_command(command)
        
        if result['success']:
            print("Coverage report generated successfully!")
            print("Open htmlcov/index.html to view detailed coverage")
        else:
            print("Failed to generate coverage report")
        
        return result['success']
    
    def lint_tests(self) -> bool:
        """Run linting on test files"""
        print("Running linting on test files...")
        
        # Check if pylint is available
        try:
            import pylint
        except ImportError:
            print("Pylint not installed. Install with: pip install pylint")
            return False
        
        command = ['python', '-m', 'pylint', 'tests/']
        result = self.run_command(command, capture_output=True)
        
        if result['success']:
            print("✓ All tests pass linting!")
        else:
            print("✗ Linting issues found:")
            if result['stdout']:
                print(result['stdout'])
        
        return result['success']
    
    def clean_test_artifacts(self):
        """Clean up test artifacts"""
        print("Cleaning test artifacts...")
        
        artifacts = [
            'htmlcov/',
            'coverage.xml',
            '.coverage',
            '.pytest_cache/',
            'test-results.xml',
            'test-report.html',
            'test-report.json'
        ]
        
        for artifact in artifacts:
            artifact_path = os.path.join(self.project_root, artifact)
            if os.path.exists(artifact_path):
                if os.path.isdir(artifact_path):
                    import shutil
                    shutil.rmtree(artifact_path)
                    print(f"Removed directory: {artifact}")
                else:
                    os.remove(artifact_path)
                    print(f"Removed file: {artifact}")
        
        print("Test artifacts cleaned!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Confluence Integration Test Runner')
    
    parser.add_argument(
        'action',
        choices=['quick', 'full', 'security', 'performance', 'coverage', 'lint', 'clean'],
        help='Test action to perform'
    )
    
    parser.add_argument(
        '--categories',
        nargs='+',
        choices=['unit', 'integration', 'security', 'frontend', 'performance', 'e2e'],
        help='Specific test categories to run'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Execute requested action
    if args.action == 'quick':
        success = runner.run_quick_tests()
    elif args.action == 'full':
        success = runner.run_full_tests()
    elif args.action == 'security':
        success = runner.run_security_tests()
    elif args.action == 'performance':
        success = runner.run_performance_tests()
    elif args.action == 'coverage':
        success = runner.generate_coverage_report()
    elif args.action == 'lint':
        success = runner.lint_tests()
    elif args.action == 'clean':
        runner.clean_test_artifacts()
        success = True
    elif args.categories:
        success = runner.run_tests(
            categories=args.categories,
            coverage=args.coverage,
            verbose=args.verbose,
            parallel=args.parallel
        )
    else:
        success = runner.run_tests(
            coverage=args.coverage,
            verbose=args.verbose,
            parallel=args.parallel
        )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()