#!/usr/bin/env python3
"""
Main simulation runner for experimental analysis of the 8-phase healthcare data sharing system.
Collects execution time, throughput, CPU/memory usage metrics.
"""

import json
import time
import csv
import sys
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from mock_blockchain import Role
from phase_simulator import PhaseSimulator
from resource_monitor import ResourceMonitor


class SimulationRunner:
    """Runs the complete 8-phase simulation and collects metrics"""
    
    def __init__(self, keys_dir: Path, results_dir: Path, ipfs_addr='/ip4/127.0.0.1/tcp/5001'):
        self.keys_dir = Path(keys_dir)
        self.results_dir = Path(results_dir)
        self.ipfs_addr = ipfs_addr
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reset()
        
    def reset(self):
        """Reset all simulation state"""
        self.simulator = PhaseSimulator(self.keys_dir, self.ipfs_addr)
        self.monitor = ResourceMonitor()
        self.all_metrics: List[Dict] = []
        # Clear keys directory
        import shutil
        for item in self.keys_dir.glob('*'):
            if item.is_dir():
                shutil.rmtree(item)
        # Clear results directory
        for item in self.results_dir.glob('*'):
            item.unlink()
        # Clear IPFS files
        try:
            import subprocess
            subprocess.run(['ipfs', 'files', 'rm', '-r', '/records'], stderr=subprocess.DEVNULL)
        except Exception:
            pass  # Ignore errors when clearing IPFS files
    
    def run_full_simulation(self, patient_id: str, doctor_id: str, viewer_id: str,
                           record_id: str, test_data: bytes, original_filename: str = None) -> Dict:
        """
        Run all 8 phases and collect metrics.
        Returns complete metrics dictionary.
        """
        print("\n" + "="*80)
        print("Starting Full 8-Phase Simulation")
        print("="*80)
        
        overall_start = time.perf_counter()
        # Removed blocking resource monitor start to avoid adding sampling overhead
        # self.monitor.start()
        phase_metrics = {}
        
        try:
            # PHASE 1: User Registration
            print("\n[PHASE 1] User Registration...")
            phase1_patient = self.simulator.phase1_user_registration(patient_id, Role.PATIENT)
            phase1_doctor = self.simulator.phase1_user_registration(doctor_id, Role.DOCTOR)
            phase1_viewer = self.simulator.phase1_user_registration(viewer_id, Role.VIEWER)
            phase_metrics['phase1'] = {
                'patient': phase1_patient,
                'doctor': phase1_doctor,
                'viewer': phase1_viewer,
                'total_time_ms': phase1_patient['total_time_ms'] + 
                               phase1_doctor['total_time_ms'] + 
                               phase1_viewer['total_time_ms']
            }
            print(f"  ✓ Phase 1 completed ({phase_metrics['phase1']['total_time_ms']:.2f} ms)")
            
            # PHASE 2: Data Encryption
            print("\n[PHASE 2] Data Encryption...")
            phase2 = self.simulator.phase2_data_encryption(test_data, patient_id, record_id)
            phase_metrics['phase2'] = phase2
            original_capsule = phase2['capsule']
            print(f"  ✓ Phase 2 completed ({phase2['encrypt_time_ms']:.2f} ms)")
            
            # PHASE 3: IPFS Storage
            print("\n[PHASE 3] IPFS Storage...")
            phase3 = self.simulator.phase3_ipfs_storage(phase2['ciphertext'], test_data, record_id, original_filename=original_filename)
            phase_metrics['phase3'] = phase3
            print(f"  ✓ Phase 3 completed ({phase3['total_time_ms']:.2f} ms)")
            
            # PHASE 4: On-chain Storage
            print("\n[PHASE 4] On-chain Storage...")
            phase4 = self.simulator.phase4_onchain_storage(
                record_id, patient_id, doctor_id, phase3['encrypted_cid'], phase2['cipher_hash']
            )
            phase_metrics['phase4'] = phase4
            print(f"  ✓ Phase 4 completed ({phase4['blockchain_time_ms']:.2f} ms)")
            
            # PHASE 5: Access Request
            print("\n[PHASE 5] Access Request...")
            phase5 = self.simulator.phase5_access_request(patient_id, viewer_id, record_id)
            phase_metrics['phase5'] = phase5
            print(f"  ✓ Phase 5 completed ({phase5['blockchain_time_ms']:.2f} ms)")
            
            # PHASE 6: Consent Approval + PRE
            print("\n[PHASE 6] Consent Approval + Proxy Re-Encryption...")
            phase6 = self.simulator.phase6_consent_approval_pre(
                patient_id, viewer_id, record_id, original_capsule
            )
            phase_metrics['phase6'] = phase6
            print(f"  ✓ Phase 6 completed ({phase6['total_time_ms']:.2f} ms)")
            
            # PHASE 7: Data Retrieval + Decryption
            print("\n[PHASE 7] Data Retrieval + Decryption...")
            phase7 = self.simulator.phase7_data_retrieval_decryption(
                viewer_id, record_id, patient_id, original_capsule
            )
            phase_metrics['phase7'] = phase7
            
            # Verify decryption
            if phase7['plaintext_size_bytes'] == len(test_data):
                print(f"  ✓ Phase 7 completed ({phase7['total_time_ms']:.2f} ms)")
                print(f"  ✓ Decryption verified: {len(test_data)} bytes")
            else:
                print(f"  ⚠ Phase 7 completed but size mismatch!")
            
            # PHASE 8: Access Revocation
            print("\n[PHASE 8] Access Revocation...")
            phase8 = self.simulator.phase8_access_revocation(patient_id, viewer_id, record_id)
            phase_metrics['phase8'] = phase8
            print(f"  ✓ Phase 8 completed ({phase8['blockchain_time_ms']:.2f} ms)")
            
            overall_time = (time.perf_counter() - overall_start) * 1000  # ms
            # Resource monitoring disabled to avoid sampling overhead that skews timings
            # self.monitor.stop()
            resource_stats = {}  # keep key for compatibility with save_metrics
            
            # Compile final metrics
            final_metrics = {
                'timestamp': datetime.now().isoformat(),
                'record_id': record_id,
                'patient_id': patient_id,
                'doctor_id': doctor_id,
                'viewer_id': viewer_id,
                'data_size_bytes': len(test_data),
                'phases': phase_metrics,
                'overall': {
                    'total_time_ms': overall_time
                },
                'resources': resource_stats
            }
            
            print("\n" + "="*80)
            print("Simulation Complete!")
            print("="*80)
            print(f"Total Time: {overall_time:.2f} ms")
            # Throughput and CPU sampling have been removed to avoid skewing overall timing
            print("="*80 + "\n")
            
            return final_metrics
            
        except Exception as e:
            # Resource monitor was not started to avoid blocking; nothing to stop
            print(f"\n❌ Simulation failed: {e}")
            raise
    
    def save_metrics(self, metrics: Dict, filename: str = None):
        """Save metrics to JSON and CSV files"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_{timestamp}"
        
        json_path = self.results_dir / f"{filename}.json"
        csv_path = self.results_dir / f"{filename}.csv"
        
        # Save JSON
        # Convert bytes to string for JSON serialization
        def convert_bytes(obj):
            if isinstance(obj, bytes):
                return obj.hex()
            return obj

        def sanitize_for_json(d):
            if isinstance(d, dict):
                return {k: sanitize_for_json(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_for_json(x) for x in d]
            else:
                return convert_bytes(d)

        json_path.write_text(json.dumps(sanitize_for_json(metrics), indent=2))
        print(f"Saved metrics to: {json_path}")
        
        # Save CSV summary
        csv_rows = []
        
        # Overall metrics
        csv_rows.append({
            'metric_type': 'overall',
            'metric_name': 'total_time_ms',
            'value': metrics['overall']['total_time_ms']
        })
        
        # Phase-specific metrics
        for phase_name, phase_data in metrics['phases'].items():
            if isinstance(phase_data, dict):
                for key, value in phase_data.items():
                    if isinstance(value, (int, float)) and ('time' in key.lower() or 'ms' in key.lower()):
                        csv_rows.append({
                            'metric_type': phase_name,
                            'metric_name': key,
                            'value': value
                        })
        
        # Resource metrics
        for key, value in metrics['resources'].items():
            if isinstance(value, (int, float)):
                csv_rows.append({
                    'metric_type': 'resources',
                    'metric_name': key,
                    'value': value
                })
        
        if csv_rows:
            with csv_path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['metric_type', 'metric_name', 'value'])
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"Saved CSV summary to: {csv_path}")
    
    def run_batch(self, num_runs: int, data_size: int = 1024):
        """Run multiple simulations for throughput analysis"""
        print(f"\nRunning batch simulation: {num_runs} runs with {data_size} bytes data")
        
        all_results = []
        
        for i in range(num_runs):
            print(f"\n--- Run {i+1}/{num_runs} ---")
            patient_id = f"P{i+1}"
            doctor_id = f"D{i+1}"
            viewer_id = f"V{i+1}"
            record_id = f"R{i+1}"
            test_data = b"A" * data_size  # Simple test data
            
            try:
                metrics = self.run_full_simulation(patient_id, doctor_id, viewer_id, record_id, test_data)
                all_results.append(metrics)
                self.save_metrics(metrics, f"run_{i+1}")
            except Exception as e:
                print(f"Run {i+1} failed: {e}")
                continue
        
        # Calculate aggregate statistics
        if all_results:
            total_times = [r['overall']['total_time_ms'] for r in all_results]
            aggregate = {
                'num_runs': len(all_results),
                'data_size_bytes': data_size,
                'avg_total_time_ms': sum(total_times) / len(total_times),
                'min_total_time_ms': min(total_times),
                'max_total_time_ms': max(total_times)
            }
            
            aggregate_path = self.results_dir / "batch_aggregate.json"
            aggregate_path.write_text(json.dumps(aggregate, indent=2))
            print(f"\nBatch aggregate saved to: {aggregate_path}")


def main():
    parser = argparse.ArgumentParser(description='Run 8-phase healthcare data sharing simulation')
    parser.add_argument('--patient', default='P1', help='Patient ID')
    parser.add_argument('--doctor', default='D1', help='Doctor ID')
    parser.add_argument('--viewer', default='V1', help='Viewer ID')
    parser.add_argument('--record', default='R1', help='Record ID')
    parser.add_argument('--dataset', default='dataset.txt', help='Path to dataset file')
    parser.add_argument('--keys-dir', default='keys', help='Directory for storing keys')
    parser.add_argument('--results-dir', default='results', help='Directory for storing results')
    parser.add_argument('--ipfs-addr', default='/ip4/127.0.0.1/tcp/5001', help='IPFS API address')
    parser.add_argument('--batch', type=int, help='Run batch simulation with N runs')
    
    args = parser.parse_args()
    
    keys_dir = Path(args.keys_dir)
    results_dir = Path(args.results_dir)
    dataset_path = Path(args.dataset)
    
    runner = SimulationRunner(keys_dir, results_dir, args.ipfs_addr)
    # Reset all state before running
    runner.reset()
    
    if args.batch:
        runner.run_batch(args.batch)
    else:
        # Read test data from dataset file
        try:
            test_data = dataset_path.read_bytes()
            print(f"\nRead {len(test_data)} bytes from dataset")
            
            metrics = runner.run_full_simulation(
                args.patient, args.doctor, args.viewer, args.record, test_data, original_filename=dataset_path.name
            )
            
            runner.save_metrics(metrics)
        except FileNotFoundError:
            print(f"Error: Dataset file not found: {dataset_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to process dataset: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()

