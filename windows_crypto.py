"""Windows DPAPI protection for SAD private application data.

This module delegates cryptography and key custody to Windows CryptProtectData /
CryptUnprotectData. It intentionally does not implement a custom cipher and does not
persist an application master key.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import platform


CRYPTPROTECT_UI_FORBIDDEN = 0x00000001
MAX_DPAPI_BYTES = 512_000_000
MAX_PURPOSE_CHARS = 160
_CONTEXT_PREFIX = "SAD-Core|dpapi-v1|"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _validate_purpose(purpose):
    if not isinstance(purpose, str) or not purpose or len(purpose) > MAX_PURPOSE_CHARS:
        raise ValueError("DPAPI purpose must be 1-160 characters.")
    if any(ord(character) < 32 for character in purpose):
        raise ValueError("DPAPI purpose contains control characters.")
    return purpose


def _require_windows():
    if platform.system() != "Windows":
        raise OSError("Windows DPAPI is available only on Windows hosts.")


def _blob_from_bytes(data):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("DPAPI input must be bytes-like.")
    raw = bytes(data)
    if len(raw) > MAX_DPAPI_BYTES:
        raise ValueError("DPAPI input exceeds the configured size limit.")
    if not raw:
        buffer = (ctypes.c_ubyte * 1)()
        return DATA_BLOB(0, ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    return DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _load_windows_apis():
    _require_windows()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    protect = crypt32.CryptProtectData
    protect.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    protect.restype = wintypes.BOOL

    unprotect = crypt32.CryptUnprotectData
    unprotect.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    unprotect.restype = wintypes.BOOL

    local_free = kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p
    return protect, unprotect, local_free


def _entropy_blob(purpose):
    purpose = _validate_purpose(purpose)
    return _blob_from_bytes((_CONTEXT_PREFIX + purpose).encode("utf-8"))


def protect_data(data, *, purpose):
    """Protect bytes for the current Windows user, bound to a SAD purpose string."""
    protect, _unprotect, local_free = _load_windows_apis()
    input_blob, input_buffer = _blob_from_bytes(data)
    entropy_blob, entropy_buffer = _entropy_blob(purpose)
    output_blob = DATA_BLOB()
    # Keep backing buffers alive until the Windows call returns.
    _ = (input_buffer, entropy_buffer)
    ok = protect(
        ctypes.byref(input_blob),
        "SAD Core protected data",
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        error = ctypes.get_last_error()
        raise OSError(error, "Windows CryptProtectData failed.")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if output_blob.pbData:
            local_free(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


def unprotect_data(data, *, purpose):
    """Unprotect current-user DPAPI bytes using the exact purpose used at protection."""
    _protect, unprotect, local_free = _load_windows_apis()
    input_blob, input_buffer = _blob_from_bytes(data)
    entropy_blob, entropy_buffer = _entropy_blob(purpose)
    output_blob = DATA_BLOB()
    description = wintypes.LPWSTR()
    _ = (input_buffer, entropy_buffer)
    ok = unprotect(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        error = ctypes.get_last_error()
        raise OSError(error, "Windows CryptUnprotectData failed or protected data is invalid for this context.")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if output_blob.pbData:
            local_free(ctypes.cast(output_blob.pbData, ctypes.c_void_p))
        if description:
            local_free(ctypes.cast(description, ctypes.c_void_p))


def dpapi_available():
    """Return whether this process is running on Windows where DPAPI should exist."""
    return platform.system() == "Windows"
