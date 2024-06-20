import os
import pytest


for root, dirs, files in os.walk(".", topdown=True):
    if any(root.startswith(folder) for folder in ["./tests", "./utils", "./lib"]):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file).lstrip("./").rstrip(".py").replace("/", ".")
                print(file_path)
                pytest.register_assert_rewrite(file_path)


def pytest_configure():
    var_file = os.getenv("CONFIG_FILE")
    print(f"{var_file=}")
    if var_file:
        pytest.is_filepoc = True if "filepoc" in var_file else False
        pytest.is_scdev01 = True if "scdev01" in var_file else False
        pytest.is_scint = True if "scint" in var_file else False
        pytest.is_prod = True if "prod" in var_file else False
