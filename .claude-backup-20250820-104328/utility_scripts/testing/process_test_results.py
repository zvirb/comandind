#!/usr/bin/env python3
"""
Result Processing Script for Browser Automation Tests

This script processes test results, generates reports, 
and provides visual and statistical analysis.
"""

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from junit2htmlreport.parser import Junit2HtmlReport

def load_test_results(junit_xml_path):
    """Load and parse JUnit XML test results"""
    with open(junit_xml_path, 'r') as f:
        report_generator = Junit2HtmlReport(f)
        test_suites = report_generator.testsuites

    return test_suites

def generate_performance_summary(test_results):
    """Generate a summary of test performance"""
    summary = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'skipped_tests': 0,
        'test_duration': 0.0
    }

    for suite in test_results:
        summary['total_tests'] += suite.tests
        summary['passed_tests'] += suite.tests - suite.failures - suite.errors
        summary['failed_tests'] += suite.failures + suite.errors
        summary['skipped_tests'] += suite.skipped
        summary['test_duration'] += suite.time

    return summary

def create_test_result_bar_chart(summary):
    """Create a bar chart visualizing test results"""
    df = pd.DataFrame({
        'Category': ['Passed', 'Failed', 'Skipped'],
        'Count': [
            summary['passed_tests'], 
            summary['failed_tests'], 
            summary['skipped_tests']
        ]
    })

    fig = px.bar(df, x='Category', y='Count', 
                 title='Browser Automation Test Results',
                 color='Category', 
                 color_discrete_map={
                     'Passed': 'green', 
                     'Failed': 'red', 
                     'Skipped': 'gray'
                 })
    
    fig.write_image("/app/reports/test_results_chart.png")
    fig.write_html("/app/reports/test_results_chart.html")

def collect_performance_metrics():
    """Collect performance metrics from log files"""
    performance_metrics = []
    
    try:
        with open('/app/browser_test_evidence_*.log', 'r') as log_file:
            # Parse log for performance metrics
            # This would be expanded based on specific log format
            pass
    except Exception as e:
        print(f"Error collecting performance metrics: {e}")

def save_performance_report(test_results, summary):
    """Save comprehensive performance report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_summary': summary,
        'test_details': [
            {
                'name': suite.name,
                'passed': suite.tests - suite.failures - suite.errors,
                'failed': suite.failures + suite.errors,
                'skipped': suite.skipped,
                'duration': suite.time
            } for suite in test_results
        ]
    }

    with open('/app/reports/performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)

def main():
    try:
        test_results = load_test_results('/app/test_results.xml')
        summary = generate_performance_summary(test_results)
        
        create_test_result_bar_chart(summary)
        save_performance_report(test_results, summary)
        collect_performance_metrics()
        
        print("Test result processing completed successfully.")
    except Exception as e:
        print(f"Error processing test results: {e}")

if __name__ == "__main__":
    main()