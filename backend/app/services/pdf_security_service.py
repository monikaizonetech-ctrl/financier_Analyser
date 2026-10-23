import os
import shutil
import tempfile
import pikepdf
import pymupdf


def detect_pdf_encryption(file_path: str) -> dict:
    """
    Detects if a PDF file is encrypted and whether it requires a user password.
    Returns:
        {
            "is_encrypted": bool,
            "password_required": bool,   # True if user password is required
            "owner_restricted": bool,    # True if owner-only encrypted (opens with empty password)
        }
    """
    if not os.path.exists(file_path):
        return {"is_encrypted": False, "password_required": False, "owner_restricted": False}

    # First attempt: pikepdf
    try:
        with pikepdf.open(file_path, password="") as pdf:
            if pdf.is_encrypted:
                # PDF is encrypted with owner permissions, but user password is empty
                return {
                    "is_encrypted": True,
                    "password_required": False,
                    "owner_restricted": True,
                }
            return {
                "is_encrypted": False,
                "password_required": False,
                "owner_restricted": False,
            }
    except pikepdf.PasswordError:
        # Requires a user password to open
        return {
            "is_encrypted": True,
            "password_required": True,
            "owner_restricted": False,
        }
    except Exception:
        # Fallback to PyMuPDF
        try:
            doc = pymupdf.open(file_path)
            is_enc = doc.is_encrypted
            needs_pass = bool(doc.needs_pass)
            doc.close()
            return {
                "is_encrypted": is_enc,
                "password_required": needs_pass,
                "owner_restricted": is_enc and not needs_pass,
            }
        except Exception:
            return {"is_encrypted": False, "password_required": False, "owner_restricted": False}


def unlock_pdf_file(file_path: str, password: str, target_path: str | None = None) -> str:
    """
    Decrypts an encrypted PDF with the provided user password.
    Saves the decrypted PDF to target_path (or replaces file_path if target_path is None).
    Never logs or persists the password.
    Returns the path to the decrypted PDF.
    Raises ValueError on incorrect password.
    """
    dest_path = target_path or file_path
    temp_fd, temp_dest = tempfile.mkstemp(suffix=".pdf")
    os.close(temp_fd)

    try:
        with pikepdf.open(file_path, password=password) as pdf:
            pdf.save(temp_dest)
        
        # Replace target with decrypted copy
        shutil.move(temp_dest, dest_path)
        return dest_path
    except pikepdf.PasswordError:
        if os.path.exists(temp_dest):
            os.remove(temp_dest)
        raise ValueError("Incorrect password, try again")
    except Exception as e:
        if os.path.exists(temp_dest):
            os.remove(temp_dest)
        raise ValueError(f"Could not unlock PDF: {str(e)}")
