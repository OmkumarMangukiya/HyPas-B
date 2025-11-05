import re
import csv
from pathlib import Path

def extract_phase_times(log_content):
    # Dictionary to store phase timings
    phases = {}
    
    # Regular expressions for phase extraction
    phase_pattern = r'\[PHASE (\d+)\].*?completed \((\d+\.\d+) ms\)'
    
    # Find all phase timings
    current_run = {}
    for line in log_content.split('\n'):
        phase_match = re.search(phase_pattern, line)
        if phase_match:
            phase_num = int(phase_match.group(1))
            time = float(phase_match.group(2))
            current_run[phase_num] = time
            
        total_match = re.search(r'Total Time: (\d+\.\d+) ms', line)
        if total_match:
            current_run['total'] = float(total_match.group(1))
            
        throughput_match = re.search(r'Throughput: (\d+\.\d+) MB/s', line)
        if throughput_match:
            current_run['throughput'] = float(throughput_match.group(1))
            
        memory_match = re.search(r'Max Memory: (\d+\.\d+) MB', line)
        if memory_match:
            current_run['memory'] = float(memory_match.group(1))
            
    return current_run

def process_size_section(content):
    runs = []
    current_run = ""
    
    for line in content.split('\n'):
        if "Starting Full 8-Phase Simulation" in line:
            if current_run:
                phases = extract_phase_times(current_run)
                if phases:
                    runs.append(phases)
            current_run = ""
        current_run += line + "\n"
        
    # Don't forget the last run
    if current_run:
        phases = extract_phase_times(current_run)
        if phases:
            runs.append(phases)
            
    return runs

def main():
    # Read the log file
    with open('results/analysis_report_20251105_195458.md', 'r') as f:
        content = f.read()
    
    # Split into sections by file size
    sections = content.split("Testing with")
    size_data = {}
    
    for section in sections[1:]:  # Skip the first empty section
        size = section.split('...')[0].strip()
        runs = process_size_section(section)
        if runs:
            size_data[size] = runs
    
    # Process results
    results = []
    headers = ['File Size', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Phase 5', 
              'Phase 6', 'Phase 7', 'Phase 8', 'Total Time', 'Throughput', 'Max Memory']
    
    for size, runs in size_data.items():
        # Calculate averages
        avg_phases = {i: 0.0 for i in range(1, 9)}
        avg_total = 0.0
        avg_throughput = 0.0
        avg_memory = 0.0
        
        for run in runs:
            for phase in range(1, 9):
                avg_phases[phase] += run.get(phase, 0)
            avg_total += run.get('total', 0)
            avg_throughput += run.get('throughput', 0)
            avg_memory += run.get('memory', 0)
        
        n_runs = len(runs)
        if n_runs > 0:
            for phase in avg_phases:
                avg_phases[phase] /= n_runs
            avg_total /= n_runs
            avg_throughput /= n_runs
            avg_memory /= n_runs
            
            row = [size]
            row.extend([f"{avg_phases[phase]:.2f}" for phase in range(1, 9)])
            row.extend([
                f"{avg_total:.2f}",
                f"{avg_throughput:.3f}",
                f"{avg_memory:.2f}"
            ])
            results.append(row)
    
    # Write to CSV
    with open('results/phase_analysis.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(results)

if __name__ == "__main__":
    main()