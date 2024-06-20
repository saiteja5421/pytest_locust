from selenium.webdriver.common.by import By
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.base_page import BasePage


class DeviceCodePage(BasePage):
    TXT_CODE = (By.XPATH, "//input[@placeholder='Code']")
    BTN_NEXT = (By.XPATH, "//input[@type='submit'][@value='Next']")

    def __init__(self, driver):
        super().__init__(driver)
        self.wait_for_element_to_be_visible(self.TXT_CODE)

    def enter_device_code(self, device_code: str):
        txt_device_code = self.wait_for_element_to_be_clickable(self.TXT_CODE)
        txt_device_code.clear()
        txt_device_code.send_keys(device_code)

        btn_next = self.wait_for_element_to_be_clickable(self.BTN_NEXT)
        btn_next.click()
