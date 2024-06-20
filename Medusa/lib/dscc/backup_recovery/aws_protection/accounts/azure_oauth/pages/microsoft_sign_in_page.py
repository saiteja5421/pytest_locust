from selenium.webdriver.common.by import By
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.base_page import BasePage


class MicrosoftSignInPage(BasePage):

    TXT_EMAIL = (By.XPATH, "//input[@type='email']")
    BTN_NEXT = (By.XPATH, "//input[@type='submit'][@value='Next']")
    TXT_PASSWORD = (By.XPATH, "//input[@type='password']")
    BTN_SIGN_IN = (By.XPATH, "//input[@type='submit'][@value='Sign in']")

    def __init__(self, driver):
        super().__init__(driver)
        self.wait_for_element_to_be_visible(self.TXT_EMAIL)

    def login(self, email_address: str, password: str):
        txt_email = self.wait_for_element_to_be_visible(self.TXT_EMAIL)
        txt_email.clear()
        txt_email.send_keys(email_address)

        btn_next = self.wait_for_element_to_be_clickable(self.BTN_NEXT)
        btn_next.click()

        txt_password = self.wait_for_element_to_be_visible(self.TXT_PASSWORD)
        txt_password.clear()
        txt_password.send_keys(password)

        btn_sign_in = self.wait_for_element_to_be_clickable(self.BTN_SIGN_IN)
        btn_sign_in.click()
