"""Security management module for PyAutoUpdater.

This module provides security features for the update process, including
digital signature verification and encryption.
"""

import os
import logging
import hashlib
import base64
from typing import Dict, Optional, Union, Tuple, Any
from pathlib import Path

# Optional imports for advanced security features
try:
    import gnupg
    GPG_AVAILABLE = True
except ImportError:
    GPG_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security aspects of the update process."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the security manager.

        Args:
            config: Optional configuration dictionary with the following keys:
                - signature_verification: Whether to verify signatures (default: True)
                - signature_type: Type of signature verification ('gpg', 'rsa', 'simple')
                - public_key_path: Path to the public key file for verification
                - gpg_home: Path to the GPG home directory
                - trusted_fingerprints: List of trusted GPG key fingerprints
        """
        self.config = config or {}
        self.verify_signatures = self.config.get('signature_verification', True)
        self.signature_type = self.config.get('signature_type', 'simple')
        
        # Initialize GPG if available and configured
        self.gpg = None
        if self.signature_type == 'gpg' and GPG_AVAILABLE:
            gpg_home = self.config.get('gpg_home')
            if gpg_home:
                self.gpg = gnupg.GPG(gnupghome=gpg_home)
            else:
                self.gpg = gnupg.GPG()
            
            # Set trusted fingerprints
            self.trusted_fingerprints = self.config.get('trusted_fingerprints', [])
        
        # Initialize RSA if available and configured
        self.public_key = None
        if self.signature_type == 'rsa' and CRYPTOGRAPHY_AVAILABLE:
            public_key_path = self.config.get('public_key_path')
            if public_key_path and os.path.exists(public_key_path):
                with open(public_key_path, 'rb') as key_file:
                    self.public_key = serialization.load_pem_public_key(
                        key_file.read()
                    )

    def verify_signature(self, file_path: str, version_info: Dict) -> bool:
        """Verify the digital signature of a file.

        Args:
            file_path: Path to the file to verify
            version_info: Version information dictionary containing signature data

        Returns:
            True if verification succeeded or is disabled, False otherwise
        """
        if not self.verify_signatures:
            logger.warning("Signature verification is disabled")
            return True

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        signature = version_info.get('signature')
        if not signature:
            logger.error("No signature found in version info")
            return False

        if self.signature_type == 'gpg':
            return self._verify_gpg_signature(file_path, signature, version_info)
        elif self.signature_type == 'rsa':
            return self._verify_rsa_signature(file_path, signature, version_info)
        else:  # 'simple' or default
            return self._verify_simple_signature(file_path, signature, version_info)

    def _verify_gpg_signature(self, file_path: str, signature: str, version_info: Dict) -> bool:
        """Verify a GPG signature.

        Args:
            file_path: Path to the file to verify
            signature: Base64-encoded GPG signature
            version_info: Version information dictionary

        Returns:
            True if verification succeeded, False otherwise
        """
        if not GPG_AVAILABLE or not self.gpg:
            logger.error("GPG verification requested but GPG is not available")
            return False

        try:
            # Decode the signature
            signature_data = base64.b64decode(signature)
            
            # Write signature to a temporary file
            sig_file = f"{file_path}.sig"
            with open(sig_file, 'wb') as f:
                f.write(signature_data)
            
            # Verify the signature
            with open(file_path, 'rb') as f:
                verify_result = self.gpg.verify_file(f, sig_file)
            
            # Clean up the signature file
            if os.path.exists(sig_file):
                os.remove(sig_file)
            
            # Check if the signature is valid and from a trusted key
            if verify_result.valid:
                if self.trusted_fingerprints and verify_result.fingerprint not in self.trusted_fingerprints:
                    logger.error(f"Signature from untrusted key: {verify_result.fingerprint}")
                    return False
                logger.info(f"GPG signature verified: {verify_result.fingerprint}")
                return True
            else:
                logger.error(f"Invalid GPG signature: {verify_result.status}")
                return False
                
        except Exception as e:
            logger.exception(f"GPG signature verification failed: {str(e)}")
            return False

    def _verify_rsa_signature(self, file_path: str, signature: str, version_info: Dict) -> bool:
        """Verify an RSA signature.

        Args:
            file_path: Path to the file to verify
            signature: Base64-encoded RSA signature
            version_info: Version information dictionary

        Returns:
            True if verification succeeded, False otherwise
        """
        if not CRYPTOGRAPHY_AVAILABLE or not self.public_key:
            logger.error("RSA verification requested but cryptography is not available or public key not loaded")
            return False

        try:
            # Decode the signature
            signature_data = base64.b64decode(signature)
            
            # Calculate the file hash
            file_hash = self._calculate_file_hash(file_path)
            
            # Verify the signature
            self.public_key.verify(
                signature_data,
                file_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            logger.info("RSA signature verified successfully")
            return True
            
        except InvalidSignature:
            logger.error("Invalid RSA signature")
            return False
        except Exception as e:
            logger.exception(f"RSA signature verification failed: {str(e)}")
            return False

    def _verify_simple_signature(self, file_path: str, signature: str, version_info: Dict) -> bool:
        """Verify a simple hash-based signature.

        Args:
            file_path: Path to the file to verify
            signature: Expected hash value (SHA-256)
            version_info: Version information dictionary

        Returns:
            True if verification succeeded, False otherwise
        """
        try:
            # Calculate the file hash
            file_hash = self._calculate_file_hash_hex(file_path)
            
            # Compare with the expected hash
            if file_hash == signature:
                logger.info("Simple signature (SHA-256) verified successfully")
                return True
            else:
                logger.error(f"Simple signature mismatch. Expected: {signature}, Got: {file_hash}")
                return False
                
        except Exception as e:
            logger.exception(f"Simple signature verification failed: {str(e)}")
            return False

    def _calculate_file_hash(self, file_path: str) -> bytes:
        """Calculate the SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as bytes
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.digest()

    def _calculate_file_hash_hex(self, file_path: str) -> str:
        """Calculate the SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as a hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


# Utility functions for generating keys and signatures
def generate_rsa_key_pair(private_key_path: str, public_key_path: str, key_size: int = 2048) -> bool:
    """Generate an RSA key pair for signing and verification.

    Args:
        private_key_path: Path to save the private key
        public_key_path: Path to save the public key
        key_size: Size of the key in bits (default: 2048)

    Returns:
        True if key generation succeeded, False otherwise
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.error("Cryptography library not available")
        return False

    try:
        # Generate a private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )

        # Get the public key
        public_key = private_key.public_key()

        # Serialize and save the private key
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Serialize and save the public key
        with open(public_key_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

        logger.info(f"RSA key pair generated and saved to {private_key_path} and {public_key_path}")
        return True

    except Exception as e:
        logger.exception(f"RSA key pair generation failed: {str(e)}")
        return False


def sign_file_rsa(file_path: str, private_key_path: str) -> Optional[str]:
    """Sign a file using RSA.

    Args:
        file_path: Path to the file to sign
        private_key_path: Path to the private key file

    Returns:
        Base64-encoded signature or None if signing failed
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.error("Cryptography library not available")
        return None

    try:
        # Load the private key
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )

        # Calculate the file hash
        file_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)

        # Sign the hash
        signature = private_key.sign(
            file_hash.digest(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Encode the signature as base64
        encoded_signature = base64.b64encode(signature).decode('ascii')
        return encoded_signature

    except Exception as e:
        logger.exception(f"RSA signing failed: {str(e)}")
        return None


def sign_file_gpg(file_path: str, gpg_home: Optional[str] = None, key_id: Optional[str] = None) -> Optional[str]:
    """Sign a file using GPG.

    Args:
        file_path: Path to the file to sign
        gpg_home: Optional path to the GPG home directory
        key_id: Optional key ID to use for signing

    Returns:
        Base64-encoded signature or None if signing failed
    """
    if not GPG_AVAILABLE:
        logger.error("GPG library not available")
        return None

    try:
        # Initialize GPG
        if gpg_home:
            gpg = gnupg.GPG(gnupghome=gpg_home)
        else:
            gpg = gnupg.GPG()

        # Sign the file
        with open(file_path, 'rb') as f:
            signature = gpg.sign_file(f, keyid=key_id, detach=True, binary=True)

        if signature:
            # Encode the signature as base64
            encoded_signature = base64.b64encode(signature.data).decode('ascii')
            return encoded_signature
        else:
            logger.error("GPG signing failed")
            return None

    except Exception as e:
        logger.exception(f"GPG signing failed: {str(e)}")
        return None