#!/usr/bin/env python3
"""
Phase simulation functions implementing all 8 phases with performance metrics.
"""

import time
from typing import Dict, Tuple
from pathlib import Path

from mock_blockchain import MockBlockchain, Role
from crypto_utils import CryptoManager
from ipfs_manager import IPFSManager


class PhaseSimulator:
    """Simulates all 8 phases with performance tracking"""
    
    def __init__(self, keys_dir: Path, ipfs_addr='/ip4/127.0.0.1/tcp/5001'):
        self.keys_dir = keys_dir
        self.ipfs_addr = ipfs_addr
        self.reset()

    def reset(self):
        """Reset all simulation state"""
        self.blockchain = MockBlockchain()
        self.crypto = CryptoManager(self.keys_dir)
        self.ipfs = IPFSManager(self.ipfs_addr)
        self.metrics: Dict[str, float] = {}
        self.capsule_storage: Dict[str, bytes] = {}
    
    def phase1_user_registration(self, user_id: str, role: Role) -> Dict:
        """
        PHASE 1: User Registration (SC_reg)
        Returns metrics dict with execution_time_ms
        """
        # Generate key pair
        start_time = time.perf_counter()
        priv_key, pub_key = self.crypto.generate_keypair(user_id)
        keygen_time = (time.perf_counter() - start_time) * 1000
        
        # Register on blockchain (store public key as bytes)
        blockchain_time = self.blockchain.register_user(user_id, role, bytes(pub_key))
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        return {
            'phase': 'PHASE_1_User_Registration',
            'user_id': user_id,
            'role': role.value,
            'keygen_time_ms': keygen_time,
            'blockchain_time_ms': blockchain_time,
            'total_time_ms': total_time
        }
    
    def phase2_data_encryption(self, data: bytes, patient_id: str, record_id: str = None) -> Dict:
        """
        PHASE 2: Data Encryption
        Returns metrics dict with ciphertext, capsule, and execution_time_ms
        """
        # Load patient's public key
        patient_pub_key = self.crypto.load_public_key(patient_id)
        
        # Encrypt data
        ciphertext, capsule, encrypt_time = self.crypto.encrypt(data, patient_pub_key)
        
        # Compute hash
        cipher_hash = self.crypto.compute_hash(ciphertext)
        
        # Store capsule for later use in PRE (use record_id if provided, otherwise patient_id)
        storage_key = record_id if record_id else patient_id
        self.capsule_storage[storage_key] = capsule
        
        return {
            'phase': 'PHASE_2_Data_Encryption',
            'ciphertext': ciphertext,
            'capsule': capsule,
            'cipher_hash': cipher_hash,
            'encrypt_time_ms': encrypt_time,
            'data_size_bytes': len(data)
        }
    
    def phase3_ipfs_storage(self, ciphertext: bytes, original_data: bytes, record_id: str = None, original_filename: str = None) -> Dict:
        """
        PHASE 3: Off-chain Storage in IPFS
        Returns metrics dict with CID and execution_time_ms
        """
        start_time = time.perf_counter()
        
        # Upload original data first. Use provided original_filename when available
        original_name = None
        if original_filename:
            original_name = original_filename
        elif record_id:
            original_name = f"original_{record_id}"

        original_cid, original_upload_time, original_mfs_path = self.ipfs.upload(
            original_data,
            filename=original_name,
            is_original=True
        )

        # Upload encrypted data. If original filename provided, derive encrypted name from it
        if original_filename:
            # replace extension with .enc
            try:
                encrypted_name = str(Path(original_filename).with_suffix('.enc'))
            except Exception:
                encrypted_name = f"record_{record_id}.enc" if record_id else None
        else:
            # fallback to record-based naming
            encrypted_name = f"record_{record_id}.enc" if record_id else None
        encrypted_cid, encrypted_upload_time, encrypted_mfs_path = self.ipfs.upload(
            ciphertext,
            filename=encrypted_name,
            is_capsule=False
        )
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        return {
            'phase': 'PHASE_3_IPFS_Storage',
            'original_cid': original_cid,
            'original_mfs_path': original_mfs_path,
            'encrypted_cid': encrypted_cid,
            'encrypted_mfs_path': encrypted_mfs_path,
            'original_upload_time_ms': original_upload_time,
            'encrypted_upload_time_ms': encrypted_upload_time,
            'total_time_ms': total_time,
            'original_size_bytes': len(original_data),
            'encrypted_size_bytes': len(ciphertext)
        }
    
    def phase4_onchain_storage(self, record_id: str, owner_vid: str, 
                               uploader_vid: str, cid: str, cipher_hash: str) -> Dict:
        """
        PHASE 4: On-chain Storage (SC_access)
        Returns metrics dict with execution_time_ms
        """
        blockchain_time = self.blockchain.store_record(
            record_id, owner_vid, uploader_vid, cid, cipher_hash
        )
        
        return {
            'phase': 'PHASE_4_Onchain_Storage',
            'record_id': record_id,
            'blockchain_time_ms': blockchain_time
        }
    
    def phase5_access_request(self, owner_vid: str, viewer_vid: str, record_id: str) -> Dict:
        """
        PHASE 5: Access Request (SC_consent)
        Returns metrics dict with execution_time_ms
        """
        blockchain_time = self.blockchain.request_access(owner_vid, viewer_vid, record_id)
        
        return {
            'phase': 'PHASE_5_Access_Request',
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id,
            'blockchain_time_ms': blockchain_time
        }
    
    def phase6_consent_approval_pre(self, owner_vid: str, viewer_vid: str, 
                                    record_id: str, original_capsule: bytes = None) -> Dict:
        """
        PHASE 6: Consent Approval + Proxy Re-Encryption
        Returns metrics dict with transformed capsule CID and execution_time_ms
        """
        start_time = time.perf_counter()
        
        # Get original capsule if not provided
        if original_capsule is None:
            original_capsule = self.capsule_storage.get(record_id)
            if original_capsule is None:
                raise ValueError(f"Original capsule not found for record {record_id}")
        
        # Load keys
        owner_priv_key = self.crypto.load_private_key(owner_vid)
        viewer_pub_key = self.crypto.load_public_key(viewer_vid)
        
        # Generate re-encryption key (kfrags)
        re_key_start = time.perf_counter()
        kfrags = self.crypto.generate_reencryption_key(owner_priv_key, viewer_pub_key)
        re_key_time = (time.perf_counter() - re_key_start) * 1000
        
        # Re-encrypt capsule to create cfrag
        transformed_capsule, reencrypt_time = self.crypto.reencrypt(original_capsule, kfrags)
        
        # Upload transformed capsule (cfrag) to IPFS
        capsule_cid, capsule_upload_time, capsule_mfs_path = self.ipfs.upload(
            transformed_capsule,
            filename=f"capsule_{record_id}",
            is_capsule=True
        )
        
        # Compute hash
        capsule_hash = self.crypto.compute_hash(transformed_capsule)
        
        # Update blockchain consent
        blockchain_time = self.blockchain.approve_access(
            owner_vid, viewer_vid, record_id, capsule_cid, capsule_hash
        )
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        return {
            'phase': 'PHASE_6_Consent_Approval_PRE',
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id,
            'capsule_cid': capsule_cid,
            'capsule_hash': capsule_hash,
            're_key_generation_time_ms': re_key_time,
            'reencrypt_time_ms': reencrypt_time,
            'capsule_upload_time_ms': capsule_upload_time,
            'capsule_mfs_path': capsule_mfs_path,
            'blockchain_time_ms': blockchain_time,
            'total_time_ms': total_time,
            'cfrag': transformed_capsule  # Store for phase 7
        }
    
    def phase7_data_retrieval_decryption(self, viewer_vid: str, record_id: str,
                                         owner_vid: str, original_capsule: bytes = None) -> Dict:
        """
        PHASE 7: Data Retrieval + Decryption
        Returns metrics dict with plaintext and execution_time_ms
        """
        start_time = time.perf_counter()
        
        # Get consent and record from blockchain
        consent = self.blockchain.get_consent(owner_vid, viewer_vid, record_id)
        if not consent or consent.status != 'approved':
            raise ValueError(f"Consent not approved for {owner_vid}:{viewer_vid}:{record_id}")
        
        record = self.blockchain.get_record(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")
        
        # Download ciphertext from IPFS
        ciphertext, cipher_download_time = self.ipfs.download(record.cid)
        
        # Download transformed capsule (cfrag) from IPFS
        cfrag_data, capsule_download_time = self.ipfs.download(consent.capsule_cid)
        
        # Verify hashes
        cipher_hash = self.crypto.compute_hash(ciphertext)
        capsule_hash = self.crypto.compute_hash(cfrag_data)
        
        if cipher_hash != record.hash:
            raise ValueError("Ciphertext hash mismatch")
        if capsule_hash != consent.capsule_hash:
            raise ValueError("Capsule hash mismatch")
        
        # Get original capsule if not provided
        if original_capsule is None:
            original_capsule = self.capsule_storage.get(record_id)
            if original_capsule is None:
                raise ValueError(f"Original capsule not found for record {record_id}")
        
        # Decrypt using original capsule + cfrag + viewer's private key
        viewer_priv_key = self.crypto.load_private_key(viewer_vid)
        owner_pub_key = self.crypto.load_public_key(owner_vid)
        plaintext, decrypt_time = self.crypto.decrypt_with_cfrag(
            ciphertext, original_capsule, cfrag_data, viewer_priv_key, owner_pub_key
        )
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        return {
            'phase': 'PHASE_7_Data_Retrieval_Decryption',
            'viewer_vid': viewer_vid,
            'record_id': record_id,
            'cipher_download_time_ms': cipher_download_time,
            'capsule_download_time_ms': capsule_download_time,
            'decrypt_time_ms': decrypt_time,
            'total_time_ms': total_time,
            'plaintext_size_bytes': len(plaintext)
        }
    
    def phase8_access_revocation(self, owner_vid: str, viewer_vid: str, record_id: str) -> Dict:
        """
        PHASE 8: Access Revocation (SC_consent)
        Returns metrics dict with execution_time_ms
        """
        blockchain_time = self.blockchain.revoke_access(owner_vid, viewer_vid, record_id)
        
        return {
            'phase': 'PHASE_8_Access_Revocation',
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id,
            'blockchain_time_ms': blockchain_time
        }

