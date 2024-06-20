import os
import random
import string
import base64
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def list_file_tree_structure(startpath):
    for root, _, files in os.walk(startpath):
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")


def generate_random_string(length=10):
    # string can contain letters, digits and special characters
    characters = string.ascii_letters + string.digits + "!@#$*"
    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string


def decode_base64(encoded_string):
    try:
        # Decode the base64 string
        decoded_bytes = base64.b64decode(encoded_string)
        # Convert bytes to a string
        decoded_string = decoded_bytes.decode("utf-8")
        return decoded_string
    except Exception as e:
        return f"Error decoding base64: {str(e)}"
