#!/usr/bin/env python3
"""
Cryptography utilities for encryption, decryption, and proxy re-encryption.
Uses pyUmbral for PRE operations.
"""

import hashlib
import time
from pathlib import Path
from typing import Tuple, Optional
from umbral import pre, keys, signing

# Try to set default curve if available
try:
    from umbral import config as umbral_config
    umbral_config.set_default_curve()
except ImportError:
    # Some versions don't have config module, curve is set by default
    pass


class CryptoManager:
    """Manages cryptographic operations"""
    
    def __init__(self, keys_dir: Path):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_keypair(self, user_id: str) -> Tuple[keys.SecretKey, keys.PublicKey]:
        """Generate a new key pair for a user"""
        priv_key = keys.SecretKey.random()
        pub_key = priv_key.public_key()
        
        # Save keys
        user_dir = self.keys_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Use correct serialization methods
        user_dir.joinpath('private_key.umbral').write_bytes(priv_key.to_secret_bytes())
        user_dir.joinpath('public_key.umbral').write_bytes(bytes(pub_key))
        
        return priv_key, pub_key
    
    def load_public_key(self, user_id: str) -> keys.PublicKey:
        """Load public key for a user"""
        pub_key_path = self.keys_dir / user_id / 'public_key.umbral'
        if not pub_key_path.exists():
            raise FileNotFoundError(f"Public key not found for {user_id}")
        return keys.PublicKey.from_bytes(pub_key_path.read_bytes())
    
    def load_private_key(self, user_id: str) -> keys.SecretKey:
        """Load private key for a user"""
        priv_key_path = self.keys_dir / user_id / 'private_key.umbral'
        if not priv_key_path.exists():
            raise FileNotFoundError(f"Private key not found for {user_id}")
        return keys.SecretKey.from_bytes(priv_key_path.read_bytes())
    
    def encrypt(self, data: bytes, recipient_public_key: keys.PublicKey) -> Tuple[bytes, bytes, float]:
        """
        Encrypt data using recipient's public key.
        Returns: (ciphertext, capsule, execution_time_ms)
        """
        start_time = time.perf_counter()
        
        capsule, ciphertext = pre.encrypt(recipient_public_key, data)
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return ciphertext, bytes(capsule), execution_time
    
    def generate_reencryption_key(self, owner_private_key: keys.SecretKey,
                                  viewer_public_key: keys.PublicKey):
        """Generate re-encryption key (kfrags) for proxy re-encryption"""
        try:
            signer = signing.Signer(private_key=owner_private_key)
        except TypeError:
            signer = signing.Signer(owner_private_key)
        
        # Use correct parameter names for umbral 0.3.0
        kfrags = pre.generate_kfrags(
            delegating_sk=owner_private_key,
            signer=signer,
            receiving_pk=viewer_public_key,
            threshold=1,
            shares=1
        )
        return kfrags
    
    def reencrypt(self, capsule_bytes: bytes, kfrags) -> Tuple[bytes, float]:
        """
        Re-encrypt capsule using re-encryption key (kfrags).
        Returns the cfrag bytes (serialized).
        Returns: (cfrag_bytes, execution_time_ms)
        """
        start_time = time.perf_counter()
        
        # Deserialize capsule
        capsule = pre.Capsule.from_bytes(capsule_bytes)
        
        # Re-encrypt using first kfrag (threshold=1, so only need one)
        cfrag = pre.reencrypt(kfrag=kfrags[0], capsule=capsule)
        
        # Serialize cfrag
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return bytes(cfrag), execution_time
    
    def decrypt(self, ciphertext: bytes, capsule_bytes: bytes, 
                private_key: keys.SecretKey) -> Tuple[bytes, float]:
        """
        Decrypt ciphertext using private key and capsule (original decryption).
        Returns: (plaintext, execution_time_ms)
        """
        start_time = time.perf_counter()
        
        # Deserialize capsule
        capsule = pre.Capsule.from_bytes(capsule_bytes)
        
        # Decrypt using decrypt_original (for owner)
        plaintext = pre.decrypt_original(private_key, capsule, ciphertext)
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return plaintext, execution_time
    
    def decrypt_with_cfrag(self, ciphertext: bytes, original_capsule_bytes: bytes, 
                          cfrag_bytes: bytes, viewer_private_key: keys.SecretKey,
                          owner_public_key: keys.PublicKey) -> Tuple[bytes, float]:
        """
        Decrypt ciphertext using original capsule, cfrag, and viewer's private key.
        Returns: (plaintext, execution_time_ms)
        """
        start_time = time.perf_counter()
        
        # Deserialize capsule and cfrag
        capsule = pre.Capsule.from_bytes(original_capsule_bytes)
        cfrag = pre.CapsuleFrag.from_bytes(cfrag_bytes)
        
        # Verify cfrag: verify(capsule, verifying_pk, delegating_pk, receiving_pk)
        viewer_public_key = viewer_private_key.public_key()
        verified_cfrag = cfrag.verify(capsule, owner_public_key, owner_public_key, viewer_public_key)
        
        # Decrypt using decrypt_reencrypted (for viewer with cfrag)
        plaintext = pre.decrypt_reencrypted(
            receiving_sk=viewer_private_key,
            delegating_pk=owner_public_key,
            capsule=capsule,
            verified_cfrags=[verified_cfrag],
            ciphertext=ciphertext
        )
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return plaintext, execution_time
    
    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Compute SHA-256 hash of data"""
        return hashlib.sha256(data).hexdigest()

