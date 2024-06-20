import sys
import os
import configparser


def update_config_file(config_file: str) -> None:
    variables_config = configparser.ConfigParser(allow_no_value=True)
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} is not found to update with the secrets!")
    variables_config.read(config_file)
    # keys in INI file are mapped with respective Environment Variables for all the runs
    env_mapping = {
        "VCENTER_SANITY": {
            "password": "SANITY_VCENTER_PASSWORD",
            "ad_password": "VCENTER_AD_PASSWORD",
            "large_vm_password": "LARGE_VM_PASSWORD",
            "esxi_password": "ESXI_PASSWORD",
        },
        "VCENTER1": {
            "password": "REG1_VCENTER1_PASSWORD",
            "ad_password": "VCENTER_AD_PASSWORD",
            "large_vm_password": "LARGE_VM_PASSWORD",
            "esxi_password": "ESXI_PASSWORD",
        },
        "VCENTER2": {
            "password": "REG1_VCENTER2_PASSWORD",
            "ad_password": "VCENTER_AD_PASSWORD",
            "large_vm_password": "LARGE_VM_PASSWORD",
            "esxi_password": "ESXI_PASSWORD",
        },
        "STOREONCE_TEST_DATA": {
            "admin_password": "STOREONCE_ADMIN_PASSWORD",
            "dualauth_password": "STOREONCE_DUALAUTH_PASSWORD",
            "dscc_admin_password": "STOREONCE_DSCC_ADMIN_PASSWORD",
        },
        "SCDEV01-USER-ONE": {
            "api_client_id": "SCDEV01_USER_ONE_API_CLIENT_ID",
            "api_client_secret": "SCDEV01_USER_ONE_API_CLIENT_SECRET",
        },
        "SCDEV01-USER-TWO": {
            "api_client_id": "SCDEV01_USER_TWO_API_CLIENT_ID",
            "api_client_secret": "SCDEV01_USER_TWO_API_CLIENT_SECRET",
        },
        "SCDEV01-USER-THREE": {
            "api_client_id": "SCDEV01_USER_THREE_API_CLIENT_ID",
            "api_client_secret": "SCDEV01_USER_THREE_API_CLIENT_SECRET",
        },
        "SCINT-USER-ONE": {
            "api_client_id": "SCINT_USER_ONE_API_CLIENT_ID",
            "api_client_secret": "SCINT_USER_ONE_API_CLIENT_SECRET",
        },
        "SCINT-USER-TWO": {
            "api_client_id": "SCINT_USER_TWO_API_CLIENT_ID",
            "api_client_secret": "SCINT_USER_TWO_API_CLIENT_SECRET",
        },
        "SCINT-USER-THREE": {
            "api_client_id": "SCINT_USER_THREE_API_CLIENT_ID",
            "api_client_secret": "SCINT_USER_THREE_API_CLIENT_SECRET",
        },
        "PROD-USER-ONE": {
            "api_client_id": "PROD_USER_ONE_API_CLIENT_ID",
            "api_client_secret": "PROD_USER_ONE_API_CLIENT_SECRET",
        },
        "SO-SCDEV01-USER-ONE": {
            "api_client_id": "STOREONCE_SCDEV01_USER_ONE_API_CLIENT_ID",
            "api_client_secret": "STOREONCE_SCDEV01_USER_ONE_API_CLIENT_SECRET",
        },
        "SO-SCINT-USER-ONE": {
            "api_client_id": "STOREONCE_SCINT_USER_ONE_API_CLIENT_ID",
            "api_client_secret": "STOREONCE_SCINT_USER_ONE_API_CLIENT_SECRET",
        },
        "MINIO": {
            "minio_access_key": "MINIO_ACCESS_KEY",
            "minio_secret_key": "MINIO_SECRET_KEY",
        },
    }
    # SCDEV01 Sanity run
    if "sanity_scdev01" in config_file:
        update_section(variables_config, "VCENTER_SANITY", env_mapping["VCENTER_SANITY"])
        update_section(variables_config, "USER-ONE", env_mapping["SCDEV01-USER-ONE"])
        update_section(variables_config, "USER-TWO", env_mapping["SCDEV01-USER-TWO"])
        update_section(variables_config, "USER-THREE", env_mapping["SCDEV01-USER-THREE"])
    # SCINT Sanity run
    elif "sanity_scint" in config_file:
        update_section(variables_config, "VCENTER_SANITY", env_mapping["VCENTER_SANITY"])
        update_section(variables_config, "USER-ONE", env_mapping["SCINT-USER-ONE"])
        update_section(variables_config, "USER-TWO", env_mapping["SCINT-USER-TWO"])
        update_section(variables_config, "USER-THREE", env_mapping["SCINT-USER-THREE"])
    # PROD Sanity run
    elif "sanity_prod" in config_file:
        update_section(variables_config, "VCENTER_SANITY", env_mapping["VCENTER_SANITY"])
        update_section(variables_config, "USER-ONE", env_mapping["PROD-USER-ONE"])
    # SCDEV01 Regression Runs
    elif "reg" in config_file and "scint" not in config_file:
        update_section(variables_config, "VCENTER1", env_mapping["VCENTER1"])
        update_section(variables_config, "VCENTER2", env_mapping["VCENTER2"])
        update_section(variables_config, "USER-ONE", env_mapping["SCDEV01-USER-ONE"])
        update_section(variables_config, "USER-TWO", env_mapping["SCDEV01-USER-TWO"])
        update_section(variables_config, "USER-THREE", env_mapping["SCDEV01-USER-THREE"])
        update_section(variables_config, "MINIO", env_mapping["MINIO"])
    # SCINT Regression Runs
    elif "reg" in config_file and "scint" in config_file:
        update_section(variables_config, "VCENTER1", env_mapping["VCENTER1"])
        update_section(variables_config, "VCENTER2", env_mapping["VCENTER2"])
        update_section(variables_config, "USER-ONE", env_mapping["SCINT-USER-ONE"])
        update_section(variables_config, "USER-TWO", env_mapping["SCINT-USER-TWO"])
        update_section(variables_config, "USER-THREE", env_mapping["SCINT-USER-THREE"])
        update_section(variables_config, "MINIO", env_mapping["MINIO"])
    # SCDEV01 Storeonce
    elif "storeonce" in config_file and "scint" not in config_file:
        update_section(variables_config, "VCENTER1", env_mapping["VCENTER_SANITY"])
        update_section(variables_config, "STOREONCE_TEST_DATA", env_mapping["STOREONCE_TEST_DATA"])
        update_section(variables_config, "USER-ONE", env_mapping["SO-SCDEV01-USER-ONE"])
        update_section(variables_config, "MINIO", env_mapping["MINIO"])
    # SCINT Storeonce
    elif "storeonce" in config_file and "scint" in config_file:
        update_section(variables_config, "VCENTER1", env_mapping["VCENTER_SANITY"])
        update_section(variables_config, "STOREONCE_TEST_DATA", env_mapping["STOREONCE_TEST_DATA"])
        update_section(variables_config, "USER-ONE", env_mapping["SO-SCINT-USER-ONE"])
        update_section(variables_config, "MINIO", env_mapping["MINIO"])

    # Write changes back to the config file
    with open(config_file, "w") as configfile:
        variables_config.write(configfile)


def update_section(variables_config: configparser.ConfigParser, section_name: str, env_map: dict) -> None:
    for section_key, env_var in env_map.items():
        if env_var in os.environ:
            variables_config[section_name][section_key] = os.environ.get(env_var)
        else:
            print(f"Environment variable {env_var} not found.")


if __name__ == "__main__":
    config_file = sys.argv[1]
    update_config_file(config_file)
