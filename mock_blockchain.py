#!/usr/bin/env python3
"""
Mock blockchain simulation for SC_reg, SC_access, and SC_consent smart contracts.
Simple in-memory storage for performance testing.
"""

import time
import hashlib
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    PATIENT = "Patient"
    DOCTOR = "Doctor"
    VIEWER = "Viewer"


@dataclass
class User:
    user_id: str
    role: Role
    public_key: bytes
    registered_at: float


@dataclass
class Record:
    record_id: str
    owner_vid: str
    uploader_vid: str
    cid: str
    hash: str
    stored_at: float


@dataclass
class Consent:
    owner_vid: str
    viewer_vid: str
    record_id: str
    status: str  # "requested", "approved", "revoked"
    capsule_cid: Optional[str] = None
    capsule_hash: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0


class MockBlockchain:
    """Mock blockchain simulation with audit logging"""
    
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all blockchain state"""
        self.users: Dict[str, User] = {}
        self.records: Dict[str, Record] = {}
        self.consents: Dict[str, Consent] = {}
        self.audit_log: list = []
    
    def _log_audit(self, action: str, details: dict):
        """Log an audit entry"""
        entry = {
            'timestamp': time.time(),
            'action': action,
            'details': details
        }
        self.audit_log.append(entry)
    
    def register_user(self, user_id: str, role: Role, public_key: bytes) -> float:
        """PHASE 1: Register user and return execution time"""
        start_time = time.perf_counter()
        
        if user_id in self.users:
            raise ValueError(f"User {user_id} already registered")
        
        self.users[user_id] = User(
            user_id=user_id,
            role=role,
            public_key=public_key,
            registered_at=time.time()
        )
        
        self._log_audit('registration', {
            'user_id': user_id,
            'role': role.value
        })
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return execution_time
    
    def store_record(self, record_id: str, owner_vid: str, uploader_vid: str, 
                     cid: str, file_hash: str) -> float:
        """PHASE 4: Store record metadata and return execution time"""
        start_time = time.perf_counter()
        
        if record_id in self.records:
            raise ValueError(f"Record {record_id} already exists")
        
        self.records[record_id] = Record(
            record_id=record_id,
            owner_vid=owner_vid,
            uploader_vid=uploader_vid,
            cid=cid,
            hash=file_hash,
            stored_at=time.time()
        )
        
        self._log_audit('store_record', {
            'record_id': record_id,
            'owner_vid': owner_vid,
            'uploader_vid': uploader_vid,
            'cid': cid
        })
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return execution_time
    
    def get_record(self, record_id: str) -> Optional[Record]:
        """Get record by ID"""
        return self.records.get(record_id)
    
    def request_access(self, owner_vid: str, viewer_vid: str, record_id: str) -> float:
        """PHASE 5: Request access and return execution time"""
        start_time = time.perf_counter()
        
        consent_key = f"{owner_vid}:{viewer_vid}:{record_id}"
        
        if consent_key in self.consents:
            raise ValueError(f"Consent already exists for {consent_key}")
        
        self.consents[consent_key] = Consent(
            owner_vid=owner_vid,
            viewer_vid=viewer_vid,
            record_id=record_id,
            status="requested",
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self._log_audit('request_access', {
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id
        })
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return execution_time
    
    def approve_access(self, owner_vid: str, viewer_vid: str, record_id: str,
                      capsule_cid: str, capsule_hash: str) -> float:
        """PHASE 6: Approve access and return execution time"""
        start_time = time.perf_counter()
        
        consent_key = f"{owner_vid}:{viewer_vid}:{record_id}"
        
        if consent_key not in self.consents:
            raise ValueError(f"Consent not found for {consent_key}")
        
        consent = self.consents[consent_key]
        consent.status = "approved"
        consent.capsule_cid = capsule_cid
        consent.capsule_hash = capsule_hash
        consent.updated_at = time.time()
        
        self._log_audit('approve_access', {
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id,
            'capsule_cid': capsule_cid
        })
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return execution_time
    
    def revoke_access(self, owner_vid: str, viewer_vid: str, record_id: str) -> float:
        """PHASE 8: Revoke access and return execution time"""
        start_time = time.perf_counter()
        
        consent_key = f"{owner_vid}:{viewer_vid}:{record_id}"
        
        if consent_key not in self.consents:
            raise ValueError(f"Consent not found for {consent_key}")
        
        consent = self.consents[consent_key]
        consent.status = "revoked"
        consent.capsule_cid = None  # Invalidate capsule
        consent.capsule_hash = None
        consent.updated_at = time.time()
        
        self._log_audit('revoke_access', {
            'owner_vid': owner_vid,
            'viewer_vid': viewer_vid,
            'record_id': record_id
        })
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return execution_time
    
    def get_consent(self, owner_vid: str, viewer_vid: str, record_id: str) -> Optional[Consent]:
        """Get consent status"""
        consent_key = f"{owner_vid}:{viewer_vid}:{record_id}"
        return self.consents.get(consent_key)

