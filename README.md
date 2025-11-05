# Healthcare Data Sharing Simulation - Experimental Analysis

This simulation framework implements the 8-phase healthcare data sharing system with proxy re-encryption for experimental analysis. It collects execution time, throughput, CPU/memory usage metrics.

## Overview

The simulation implements:

1. **PHASE 1** — User Registration (SC_reg): Patient/Doctor/Viewer registration with key pair generation
2. **PHASE 2** — Data Encryption: Encrypt EHR using Patient's public key with PRE capsule
3. **PHASE 3** — Off-chain Storage in IPFS: Upload encrypted file to IPFS
4. **PHASE 4** — On-chain Storage (SC_access): Store metadata on blockchain
5. **PHASE 5** — Access Request (SC_consent): Viewer requests access
6. **PHASE 6** — Consent Approval + Proxy Re-Encryption: Generate re-encryption key and transform capsule
7. **PHASE 7** — Data Retrieval + Decryption: Viewer downloads and decrypts data
8. **PHASE 8** — Access Revocation (SC_consent): Patient revokes access

## Prerequisites

- Python 3.10+
- IPFS daemon running (start with `ipfs daemon`)
- Dependencies installed: `pip install -r requirements.txt`

## Installation

```bash
cd start-fresh
pip install -r requirements.txt
```

## Usage

### Single Simulation Run

```bash
python simulate.py --patient P1 --doctor D1 --viewer V1 --record R1 --data-size 1024
```

### Batch Simulation (for throughput analysis)

```bash
python simulate.py --batch 10 --data-size 1024
```

### Options

- `--patient`: Patient ID (default: P1)
- `--doctor`: Doctor ID (default: D1)
- `--viewer`: Viewer ID (default: V1)
- `--record`: Record ID (default: R1)
- `--data-size`: Test data size in bytes (default: 1024)
- `--keys-dir`: Directory for storing keys (default: keys)
- `--results-dir`: Directory for storing results (default: results)
- `--ipfs-addr`: IPFS API address (default: /ip4/127.0.0.1/tcp/5001)
- `--batch`: Run batch simulation with N runs

## Output

The simulation generates:

1. **JSON metrics file**: Detailed metrics for each phase including:
   - Execution times for each operation
   - Resource usage (CPU, memory)
   - Throughput calculations
   - Phase-by-phase breakdown

2. **CSV summary file**: Summary metrics in CSV format for easy analysis

3. **Console output**: Real-time progress and summary statistics

## Metrics Collected

- **Execution Time**: Time for each phase and operation (in milliseconds)
- **Throughput**: Data processing rate (bytes/sec, MB/sec)
- **CPU Usage**: Average and maximum CPU percentage
- **Memory Usage**: Average and maximum memory usage (MB and percentage)

## Example Output

```
================================================================================
Starting Full 8-Phase Simulation
================================================================================

[PHASE 1] User Registration...
  ✓ Phase 1 completed (45.23 ms)

[PHASE 2] Data Encryption...
  ✓ Phase 2 completed (12.45 ms)

[PHASE 3] IPFS Storage...
  ✓ Phase 3 completed (234.56 ms)

[PHASE 4] On-chain Storage...
  ✓ Phase 4 completed (0.12 ms)

[PHASE 5] Access Request...
  ✓ Phase 5 completed (0.15 ms)

[PHASE 6] Consent Approval + Proxy Re-Encryption...
  ✓ Phase 6 completed (156.78 ms)

[PHASE 7] Data Retrieval + Decryption...
  ✓ Phase 7 completed (298.34 ms)
  ✓ Decryption verified: 1024 bytes

[PHASE 8] Access Revocation...
  ✓ Phase 8 completed (0.18 ms)

================================================================================
Simulation Complete!
================================================================================
Total Time: 747.81 ms
Throughput: 1.37 MB/s
Avg CPU: 23.45%
Max Memory: 125.67 MB
================================================================================
```

## Project Structure

```
start-fresh/
├── simulate.py              # Main simulation runner
├── phase_simulator.py        # Phase implementation
├── mock_blockchain.py       # Mock blockchain (in-memory)
├── crypto_utils.py          # Encryption/PRE utilities
├── ipfs_manager.py          # IPFS operations
├── resource_monitor.py      # CPU/memory monitoring
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── keys/                    # Generated keys (created automatically)
└── results/                 # Metrics output (created automatically)
```

## Notes

- The blockchain is simulated in-memory for performance testing
- IPFS must be running (`ipfs daemon`) before starting simulation
- Keys are stored locally in the `keys/` directory
- Results are saved with timestamps for multiple runs

