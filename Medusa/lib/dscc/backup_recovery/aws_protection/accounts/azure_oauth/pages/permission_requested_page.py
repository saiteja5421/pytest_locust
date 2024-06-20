from selenium.webdriver.common.by import By
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.base_page import BasePage


class PermissionRequestedPage(BasePage):
    BTN_ACCEPT = (By.XPATH, "//input[@type='submit'][@value='Accept']")
    BTN_CANCEL = (By.XPATH, "//input[@type='submit'][@value='Cancel']")

    def __init__(self, driver):
        super().__init__(driver)
        self.wait_for_element_to_be_visible(self.BTN_ACCEPT)

    def accept_permissions(self):
        btn_accept = self.wait_for_element_to_be_clickable(self.BTN_ACCEPT)
        btn_accept.click()
