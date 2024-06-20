"""
Script created for keeping cVSA manager test plan up to date.
After script is run the Test Scenarios on page below are updated accordingly to module doc strings from the top of tests
https://confluence.eng.nimblestorage.com/display/WIQ/cVSA+Manager+Test+Plan
"""

import ast
import glob
from os import getenv

import pandas as pd
from atlassian import Confluence
from bs4 import BeautifulSoup


class GenerateTestPlan:
    tests_path = "../**/test_*.py"
    columns = ["ID", "Name", "Steps", "Environment", "Automation Status"]

    test_plan_page = "https://confluence.eng.nimblestorage.com"
    space = "WIQ"
    title = "cVSA Manager Test Plan"
    test_plan_id = "231245587"
    token = getenv("CONFLUENCE_TOKEN")
    assert token is not None, "Please add environmental variable with CONFLUENCE_TOKEN"

    def __init__(self):
        self.confluence_connector = Confluence(url=self.test_plan_page, token=self.token, cloud=True)

    def get_existing_confluence_page_html(self):
        page = self.confluence_connector.get_page_by_id(self.test_plan_id, expand="body.storage")
        return BeautifulSoup(page["body"]["storage"]["value"], "html.parser")

    def get_html_tab_from_tests_docs(self):
        docs_list = []
        for filename in glob.iglob(self.tests_path):
            with open(filename) as f:
                env = filename.split("/")[-2].upper()
                doc_parser = ast.parse(f.read())
                doc_string_lines = ast.get_docstring(doc_parser).split("\n")
                file_records = self.get_dict_frame_from_docstring(doc_string_lines, env)
                docs_list += file_records
        df = (
            pd.DataFrame(data=docs_list, columns=self.columns)
            .sort_values(by="ID")
            .drop_duplicates(ignore_index=True)
            .dropna(subset=["ID"])
        )
        return df.to_html(index=False, escape=False)

    @staticmethod
    def get_dict_frame_from_docstring(doc_string_lines, env):
        records = []
        record = {"Steps": ""}
        for line in doc_string_lines:
            if line.startswith("TC"):
                record = {"Steps": "", "Environment": env}
                ids, name = line.split(":")
                record["ID"] = ids.replace("-", "")
                record["Name"] = name.strip()
                record["Automation Status"] = "DONE"
            else:
                record["Steps"] += f"{line.strip()} <br/>"
            records.append(record)
        return records

    def update_test_rail(self):
        pass

    def update_existing_table_on_confluence(self):
        soup = self.get_existing_confluence_page_html()
        old_table_html = soup.find("table", attrs={"class": "dataframe"})
        new_table_html = self.get_html_tab_from_tests_docs()
        old_table_html.replace_with(BeautifulSoup(new_table_html))
        self.confluence_connector.update_page(
            page_id=self.test_plan_id, body=soup.prettify(), title=self.title, minor_edit=True
        )


if __name__ == "__main__":
    GenerateTestPlan().update_existing_table_on_confluence()
