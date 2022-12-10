#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module is a library of cryptographic functions used by TokenAccess
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'


# Built-in
from importlib import import_module
from urllib.parse import unquote_to_bytes, quote_from_bytes
import base64


# Other libs
from cryptography.hazmat.primitives.twofactor import hotp
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import twofactor, hashes, serialization


# Classes
## PSK structure for ECDH
class PreSharedKey:
    PSK=None


    def __init__(self, curve:str='x25519',base:str='b64',algorithm:str='SHA256'):
        """Create a structure for ECDH pre-shared key generation (HOTP seed).

        Args:
            curve (str, optional): An elliptic curve allowed cryptography.hazmat.primitives.asymmetric. Defaults to 'x25519'.
            base (str, optional): An encoding base allowed by base64. Defaults to 'b64'.
            algorithm (str, optional): A hashing function allowed by cryptography.hazmat.primitives.hashes. Defaults to 'SHA256'.
        """

        mod = import_module('cryptography.hazmat.primitives.asymmetric.'+ curve.lower())
        self._ECPrivateKey=getattr(mod, curve.capitalize()+"PrivateKey")
        self._ECPublicKey=getattr(mod, curve.capitalize()+"PublicKey")

        self._pvtKey=self._ECPrivateKey.generate()

        self._baseEncode=getattr(base64, base+'encode')
        self._baseDecode=getattr(base64, base+'decode')
        self._algorithm=getattr(hashes, algorithm)


    def exportPubKey(self) -> str:
        """Export public key for PSK generation (to send to recipient).

        Returns:
            str: The public key generated by the elliptic curve
        """
        bytesPubKey = self._pvtKey.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        encodedPubKey = self._baseEncode(bytesPubKey)
        return quote_from_bytes(encodedPubKey)


    def generate(self, user:str, recipientPubKey:str) -> str:
        """Generation of the pre-shared key for a specified user using the public key recieved

        Args:
            user (str): The user name. MUST BE THE SAME AS RECIPIENT
            recipientPubKey (str): The public key url-encoded.

        Returns:
            str: The PSK generated.
        """
        encodedPubKey = unquote_to_bytes(recipientPubKey)
        bytesPubKey = self._ECPublicKey.from_public_bytes(
                self._baseDecode(encodedPubKey)
            )
            
        sharedKey = self._pvtKey.exchange(bytesPubKey)
        derivedPSK = HKDF(
            algorithm=self._algorithm(),
            length=20,
            salt=None,
            info=bytes(f'{user}', 'UTF-8'),
        ).derive(sharedKey)

        self.PSK = self._baseEncode(derivedPSK).decode()
        return self.PSK
        

class HashText:

    def __init__(self, plaintext:str, base:str='b64', algorithm:str='SHA256'):
        """Creates a hashText object

        Args:
            plaintext (str): The message to hash
            base (str, optional): An encoding base allowed by base64. Defaults to 'b64'.
            algorithm (str, optional): A hashing function allowed by cryptography.hazmat.primitives.hashes. Defaults to 'SHA256'.
        """

        self._baseEncode=getattr(base64, base+'encode')
        self._baseDecode=getattr(base64, base+'decode')

        self._algorithm=getattr(hashes, algorithm)

        self.plaintext=plaintext.encode()

    
    def getHash(self) -> bytes:
        """Get the generated hash

        Returns:
            bytes: The base-encoded hash
        """
        digest = hashes.Hash( algorithm=self._algorithm() )
        digest.update(self.plaintext)
        hashBytes = digest.finalize()
        return self._baseEncode(hashBytes)

    
    def isSame(self, hashStr:str) -> bool:
        """Checks if the given base-encoded hash is the one of the object's one

        Args:
            hashStr (str): The base-encoded string hash value

        Returns:
            bool: Result of hash comparison
        """
        return (self.getHash() == hashStr.encode())
    


# Functions
def getHotp(preSharedKey: str, count: int, base:str='b64', algorithm:str='SHA256', length:int=6) -> str:
    """Compute HOTP with the given arguments

    Args:
        preSharedKey (str): base-encoded pre-shared key
        count (int): Counter
        base (str, optional): An encoding base allowed by base64. Defaults to 'b64'.
        algorithm (str, optional): A hashing function allowed by cryptography.hazmat.primitives.hashes. Defaults to 'SHA256'.
        length (int, optional): The HOTP length. Defaults to 6.

    Returns:
        str: Returns the HOTP computed value
    """
    _baseDecode=getattr(base64, base+'decode')
    _algorithm=getattr(hashes, algorithm)
    bytesPSK = _baseDecode(preSharedKey)
    myHOTP = hotp.HOTP(
        key=bytesPSK,
        length=length,
        algorithm=_algorithm()
    )
    return myHOTP.generate(counter=count)
