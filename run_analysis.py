#!/usr/bin/env python3
"""
Performance analysis script for the healthcare data sharing system.
Runs multiple tests with different data sizes and generates a detailed report.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from statistics import mean, stdev

# Number of runs for each test to get average timings
NUM_RUNS = 1

# Test configurations
TEST_CONFIGS = [
    # {"size": "500B", "file": "500B.txt", "runs": NUM_RUNS},
    {"size": "1KB", "file": "1KB.txt", "runs": NUM_RUNS},
    # {"size": "2KB", "file": "2KB.txt", "runs": NUM_RUNS},
    {"size": "10KB", "file": "10KB.txt", "runs": NUM_RUNS},
    # {"size": "20KB", "file": "20KB.txt", "runs": NUM_RUNS},
    {"size": "50KB", "file": "50KB.txt", "runs": NUM_RUNS},
]

def run_simulation(dataset_file: str) -> dict:
    """Run a single simulation and return the metrics"""
    from simulate import SimulationRunner
    
    # Setup paths
    keys_dir = Path("keys")
    results_dir = Path("results")
    dataset_path = Path("datasets") / dataset_file
    
    # Create runner and reset state
    runner = SimulationRunner(keys_dir, results_dir)
    runner.reset()
    
    # Read test data
    test_data = dataset_path.read_bytes()
    
    # Run simulation
    metrics = runner.run_full_simulation(
        patient_id="P1",
        doctor_id="D1",
        viewer_id="V1",
        record_id="R1",
        test_data=test_data
    )
    
    return metrics

def analyze_metrics(metrics_list: List[Dict], size: str) -> Dict:
    """Analyze metrics from multiple runs"""
    on_chain_times = []
    off_chain_times = []
    retrieval_times = []
    
    for metrics in metrics_list:
        # On-chain storage (Phase 4)
        on_chain_times.append(metrics['phases']['phase4']['blockchain_time_ms'] / 1000)  # Convert to seconds
        
        # Off-chain storage (Phase 3)
        off_chain_times.append(metrics['phases']['phase3']['total_time_ms'] / 1000)
        
        # Data retrieval (Phase 7)
        retrieval_times.append(metrics['phases']['phase7']['total_time_ms'] / 1000)
    
    def get_range(times):
        return {
            'min': min(times),
            'max': max(times),
            'avg': mean(times),
            'std': stdev(times) if len(times) > 1 else 0
        }
    
    return {
        'size': size,
        'on_chain': get_range(on_chain_times),
        'off_chain': get_range(off_chain_times),
        'retrieval': get_range(retrieval_times)
    }

def generate_report(results: List[Dict]):
    """Generate a markdown report with the analysis results"""
    report = """# Healthcare Data Sharing Performance Analysis

## Test Configuration
- Each test run {NUM_RUNS} times
- All times in seconds
- Tests run on {date}

## Results

| Operation | Data Size | Execution Time (s) | Statistics |
|-----------|-----------|-------------------|------------|
""".format(NUM_RUNS=NUM_RUNS, date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Add results for each operation and size
    for result in results:
        # On-chain storage
        report += "| **On-chain Storage** | {} | {:.2f} – {:.2f} | avg: {:.2f}, std: {:.2f} |\n".format(
            result['size'],
            result['on_chain']['min'],
            result['on_chain']['max'],
            result['on_chain']['avg'],
            result['on_chain']['std']
        )
        
        # Off-chain storage
        report += "| **Off-chain Storage** | {} | {:.2f} – {:.2f} | avg: {:.2f}, std: {:.2f} |\n".format(
            result['size'],
            result['off_chain']['min'],
            result['off_chain']['max'],
            result['off_chain']['avg'],
            result['off_chain']['std']
        )
        
        # Data retrieval
        report += "| **Data Retrieval** | {} | {:.2f} – {:.2f} | avg: {:.2f}, std: {:.2f} |\n".format(
            result['size'],
            result['retrieval']['min'],
            result['retrieval']['max'],
            result['retrieval']['avg'],
            result['retrieval']['std']
        )
    
    # Write report to file
    report_path = Path("results") / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report)
    print(f"\nAnalysis report saved to: {report_path}")

def main():
    all_results = []
    
    # Ensure datasets directory exists
    if not Path("datasets").exists():
        print("Error: datasets directory not found!")
        sys.exit(1)
    
    print("\nStarting performance analysis...")
    print("="*80)
    
    for config in TEST_CONFIGS:
        print(f"\nTesting with {config['size']} dataset...")
        metrics_list = []
        
        for run in range(config['runs']):
            print(f"  Run {run + 1}/{config['runs']}...")
            try:
                metrics = run_simulation(config['file'])
                metrics_list.append(metrics)
            except Exception as e:
                print(f"Error in run {run + 1}: {e}")
                continue
        
        if metrics_list:
            results = analyze_metrics(metrics_list, config['size'])
            all_results.append(results)
            print(f"  Completed {len(metrics_list)} successful runs")
        else:
            print(f"  No successful runs for {config['size']}")
    
    if all_results:
        generate_report(all_results)
    else:
        print("\nNo results to analyze!")

if __name__ == '__main__':
    main()