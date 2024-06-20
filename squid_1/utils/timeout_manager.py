from common.config.config_manager import ConfigManager


class TimeoutManager:
    first_time_psgw_creation: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("first_time_psgw_creation")) else 0
    )
    create_psgw_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("create_psgw_timeout")) else 0
    )
    create_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("create_backup_timeout")) else 0
    )
    unregister_purge_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("unregister_purge_timeout")) else 0
    )
    delete_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("delete_backup_timeout")) else 0
    )
    create_cloud_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("create_cloud_backup_timeout")) else 0
    )
    standard_task_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("standard_task_timeout")) else 0
    )
    health_status_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("health_status_timeout")) else 0
    )
    v_center_manipulation_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("v_center_manipulation_timeout")) else 0
    )
    resize_psg_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("resize_psg_timeout")) else 0
    )
    resize_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("resize_timeout")) else 0
    )
    psg_shutdown_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("psg_shutdown_timeout")) else 0
    )
    psg_powered_off_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("psg_powered_off_timeout")) else 0
    )
    create_local_store_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("create_psgw_timeout")) else 0
    )
    create_rds_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("rds_create_backup_timeout")) else 0
    )
    restore_rds_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("rds_restore_timeout")) else 0
    )
    task_timeout = 180
    create_snaphots_inbetween_timeout: int = (
        int(timeout)
        if (timeout := ConfigManager.get_config()["timeouts"].get("create_snaphots_inbetween_timeout"))
        else 0
    )
    create_ami_inbetween_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("create_ami_inbetween_timeout")) else 0
    )
    dual_auth_task_inbetween_timeout: int = (
        int(timeout)
        if (timeout := ConfigManager.get_config()["timeouts"].get("dual_auth_task_inbetween_timeout"))
        else 0
    )
    index_backup_timeout: int = (
        int(timeout) if (timeout := ConfigManager.get_config()["timeouts"].get("index_backup_timeout")) else 0
    )
