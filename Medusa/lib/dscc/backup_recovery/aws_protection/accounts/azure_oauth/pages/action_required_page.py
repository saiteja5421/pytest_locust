from selenium.webdriver.common.by import By
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.base_page import BasePage


class ActionRequiredPage(BasePage):
    """Page that shows up when a user does not have MFA setup

    Args:
        BasePage (BasePage): BasePage
    """

    BTN_ASK_LATER = (By.ID, "btnAskLater")
    BTN_NEXT = (By.ID, "idSubmit_ProofUp_Redirect")

    def __init__(self, driver):
        super().__init__(driver)
        self.wait_for_element_to_be_visible(self.BTN_ASK_LATER)

    def skip_setting_authentication(self):
        btn_ask_later = self.wait_for_element_to_be_visible(self.BTN_ASK_LATER)
        btn_ask_later.click()
