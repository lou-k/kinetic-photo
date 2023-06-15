import hashlib
import os

class ObjectStore:

    def __init__(self, directory: str):
        self.directory = directory
    
    def _hash_path(self, hash: str) -> str:
        return os.path.join(self.directory, hash)

    def add(self, file: bytes) -> str:
        hash = hashlib.sha256(file).hexdigest()
        with open(self._hash_path(hash), "wb") as fout:
            fout.write(file)
        return hash
    
    def get(self, hash: str) -> bytes:
        with open(self._hash_path(hash), "rb") as fin:
            return fin.read()
    
    def exists(self, hash: str) -> bool:
        return os.path.exists(self._hash_path(hash))
        
