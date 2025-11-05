#!/usr/bin/env python3
"""
IPFS helper for uploading and downloading files.
"""

import time
import sys
from pathlib import Path

# Try to import from parent directory
try:
    from ipfs_pre.ipfs_helper import connect_ipfs
except ImportError:
    # Fallback: add parent directory to path
    parent_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(parent_dir))
    try:
        from ipfs_pre.ipfs_helper import connect_ipfs
    except ImportError:
        # Last resort: use direct import with version bypass
        import ipfshttpclient
        def connect_ipfs(addr='/ip4/127.0.0.1/tcp/5001'):
            try:
                return ipfshttpclient.connect(addr)
            except Exception as e:
                if 'VersionMismatch' in type(e).__name__ or 'version' in str(e).lower():
                    # Patch version check
                    import ipfshttpclient.client as ipfs_client
                    original_assert = ipfs_client.assert_version
                    ipfs_client.assert_version = lambda *args, **kwargs: None
                    try:
                        return ipfshttpclient.connect(addr)
                    finally:
                        ipfs_client.assert_version = original_assert
                raise


class IPFSManager:
    """Manages IPFS operations"""
    
    def __init__(self, ipfs_addr='/ip4/127.0.0.1/tcp/5001'):
        self.ipfs_addr = ipfs_addr
        self._client = None
    
    def _get_client(self):
        """Get or create IPFS client"""
        if self._client is None:
            self._client = connect_ipfs(self.ipfs_addr)
        return self._client
    
    def upload(self, data: bytes, filename: str = None, is_capsule: bool = False, is_original: bool = False) -> tuple[str, float, str]:
        """
        Upload data to IPFS.
        Returns: (cid, execution_time_ms)
        """
        start_time = time.perf_counter()
        client = self._get_client()

        # Add appropriate file extension and metadata
        if filename is None:
            filename = f"record_{int(time.time())}"

        # If filename already contains an extension, don't append another one
        has_ext = Path(filename).suffix != ''

        if is_capsule:
            filename = f"{filename}" if has_ext else f"{filename}.capsule"
        elif is_original:
            filename = f"{filename}" if has_ext else f"{filename}.txt"
        else:
            filename = f"{filename}" if has_ext else f"{filename}.enc"

        # Upload raw data first
        cid = client.add_bytes(data)
        
        # Pin the file to ensure persistence
        try:
            client.pin.add(cid)
            
            # Add to MFS (Files tab in WebUI)
            mfs_path = f"/records/{filename}"
            
            # Create directory if it doesn't exist
            try:
                client.files.mkdir("/records", parents=True)
            except Exception:
                pass  # Directory might already exist
                
            # Add to MFS with proper naming and create metadata file
            try:
                # Create records directory
                client.files.mkdir("/records", parents=True)
                
                # Create content directory for this file
                dir_path = f"/records/{filename}"
                client.files.mkdir(dir_path, parents=True)
                
                # Add content file
                content_path = f"{dir_path}/content"
                client.files.cp(f"/ipfs/{cid}", content_path)
                
                # Create metadata file
                metadata = {
                    "name": filename,
                    "type": "application/octet-stream" if is_capsule else "application/encrypted",
                    "size": len(data),
                    "cid": cid,
                    "timestamp": int(time.time())
                }
                
                # Add metadata to MFS
                metadata_cid = client.add_json(metadata)
                client.files.cp(f"/ipfs/{metadata_cid}", f"{dir_path}/metadata.json")
                
                print(f"File added to IPFS Files: {dir_path}")
                mfs_path = dir_path
                    
            except Exception as e:
                print(f"Warning: Could not add to IPFS Files: {e}")
                
        except Exception as e:
            print(f"Warning: Pin operation failed: {e}")
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        # If mfs_path wasn't set (e.g., MFS operations failed), set to empty string
        try:
            mfs_path
        except NameError:
            mfs_path = ''
        return cid, execution_time, mfs_path
    
    def download(self, cid: str) -> tuple[bytes, float]:
        """
        Download data from IPFS.
        Returns: (data, execution_time_ms)
        """
        start_time = time.perf_counter()
        client = self._get_client()
        data = client.cat(cid)
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        return data, execution_time

