import sys
import os
import configparser
import logging

logger = logging.getLogger()


def update_config_file(config_file: str, credentials: list, operator: bool = False) -> None:
    path = "Medusa/configs/atlantia"
    config = configparser.ConfigParser(allow_no_value=True)
    file_path = os.path.join(path, config_file)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} is not found to update with the  secrets!")
    config.read(file_path)
    # Add client and secret ids to the config.
    if operator:
        op_cred = credentials[-1]
        config["OP-USER-ONE"]["api_client_id"], config["OP-USER-ONE"]["api_client_secret"] = op_cred.split(",")
    elif len(credentials) == 3:
        cred_one, cred_two, cred_three = credentials
        config["USER-ONE"]["api_client_id"], config["USER-ONE"]["api_client_secret"] = cred_one.split(",")
        config["USER-TWO"]["api_client_id"], config["USER-TWO"]["api_client_secret"] = cred_two.split(",")
        config["USER-THREE"]["api_client_id"], config["USER-THREE"]["api_client_secret"] = cred_three.split(",")
    elif len(credentials) == 2:
        cred_one, cred_two = credentials
        config["USER-ONE"]["api_client_id"], config["USER-ONE"]["api_client_secret"] = cred_one.split(",")
        config["USER-TWO"]["api_client_id"], config["USER-TWO"]["api_client_secret"] = cred_two.split(",")
    else:
        cred_one = credentials[-1]
        config["USER-ONE"]["api_client_id"], config["USER-ONE"]["api_client_secret"] = cred_one.split(",")

    # Write changes back to the config file
    with open(file_path, "w") as config_file:
        config.write(config_file)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        logger.info("Usage: python3 utils/update_config_file.py config_file.ini credentials_type credentials_ids_list")
        logger.info("Credentials types: admin, operator")
        sys.exit(1)

    config_file = sys.argv[1]
    credentials_type = sys.argv[2]
    credentials = sys.argv[3:]
    if credentials_type.lower() == "operator":
        update_config_file(config_file=config_file, credentials=credentials, operator=True)
    elif credentials_type.lower() == "admin":
        update_config_file(config_file=config_file, credentials=credentials)
    else:
        raise ValueError("credentials type should be admin or operator")
