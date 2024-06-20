import asyncio
import requests
import msal
import logging
from typing import List, Union
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.user import User
from msgraph.generated.models.password_profile import PasswordProfile
from msgraph.generated.models.phone_authentication_method import PhoneAuthenticationMethod
from msgraph.generated.models.authentication_phone_type import AuthenticationPhoneType
from msgraph.generated.models.unified_role_assignment import UnifiedRoleAssignment
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.generated.models.service_principal_collection_response import ServicePrincipalCollectionResponse

from datetime import datetime, timedelta
from lib.common.config.config_manager import ConfigManager
from lib.dscc.backup_recovery.ms365_protection.common.enums.importance import MS365Importance
from lib.dscc.backup_recovery.ms365_protection.common.enums.categories import TaskCategories

from requests import Response
import os
import base64

logger = logging.getLogger()


class MSOutlookManager:
    """This class will contain all the base methods related to MS Outlook"""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        config = ConfigManager.get_config()
        self.ms365 = config["MS365"]
        self.graph_api_endpoint = self.ms365["graph_api_endpoint"]
        self.login_url = self.ms365["login_url"]
        self.default_scope = self.ms365["default_scope"]
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        if self.tenant_id:
            self.authority = self.login_url + self.tenant_id

        self.access_token = None
        self.token_expiry_time = 0
        self.ms_graph_client = None
        from MS365_Asset_Checksum_Tool import api as checksumTool

        # hashing algorithm can also be checksumTool.sha256(), but mmh3 is faster/preferred
        self.hashing_algorithm = checksumTool.mmh3()
        # hashing log level, can be 'DEBUG', 'INFO', 'ERROR', 'FATAL' suggested is FATAL as logging is slow
        self.hashing_log_level = "FATAL"
        self.chksum_tool = checksumTool.V1(
            self.hashing_log_level, self.hashing_algorithm, self.tenant_id, self.client_id, self.client_secret
        )
        self.attachment_filter = ["name", "contentType", "contentBytes"]
        self.item_filter = ["subject", "receivedDateTime", "body"]
        self.folder_filter = ["displayName", "totalItemCount", "sizeInBytes"]

    def get_access_token(self):
        """get application access token
        Returns:
            string: access token of an application
        """
        if not self.access_token:
            app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
            )
            response = app.acquire_token_for_client(scopes=[self.default_scope])

            # Set the expiry time
            current_time = datetime.now()
            self.token_expiry_time = current_time + timedelta(minutes=55)
            self.access_token = response["access_token"]
        else:
            # Check token expiry time
            if datetime.now() >= self.token_expiry_time:
                self.access_token = None
                self.get_access_token()
        return self.access_token

    def create_ms_graph_client(self):
        """Create MS graph client, which will be created based on the provided credentials"""
        logger.info("Creating MS graph client object")
        try:
            credentials = ClientSecretCredential(
                self.tenant_id,
                self.client_id,
                self.client_secret,
            )
            self.ms_graph_client = GraphServiceClient(credentials=credentials, scopes=[self.default_scope])
            logger.info("Successfully created MS graph client object")
        except Exception as e:
            logger.error(f"Failed to create the MS graph client, error: {e}")
            self.ms_graph_client = None

    def get_ms_graph_client(self):
        """Get MS graph client, which will be created based on the provided credentials

        Returns:
            obj: ms graph client object
        """
        if self.ms_graph_client is None:
            self.create_ms_graph_client()
        else:
            logger.info("MS graph client object exists, lets use it...")
        return self.ms_graph_client

    def get_headers(self):
        """construct headers based on the provided access token

        Returns:
            json: headers in json format
        """
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "ContentType": "application/json",
        }
        return headers

    def construct_attachment_object(self, file_path):
        """This function constructs attachment object after doing basic validation on the file_path passed as the argument.

        Args:
            file_path (str): Path of file which has to be attached to email.

        Returns:
            Attachment object: Attachment object.
            ex:
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "contentBytes": attachment_content.decode("utf-8"),
                "name": "file_path",
            }
        """
        if not os.path.exists(file_path):
            # Generating a .log file
            log_content = "This is a sample log content."
            with open(file_path, "w") as log_file:
                log_file.write(log_content)
        with open(file_path, "rb") as attach:
            attachment_content = base64.b64encode(attach.read())

        attachment_obj = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "contentBytes": attachment_content.decode("utf-8"),
            "name": os.path.basename(file_path),
        }
        return attachment_obj

    def construct_email(
        self,
        to_recipients: list = ["ms365automation@framework.com"],
        subject: str = "test email",
        content: str = ": We are all set",
        importance: MS365Importance = MS365Importance.NORMAL.value,
        attachments: list = [],
        cc_recipients: list = [],
        **kwargs,
    ):
        """Constructs email message

        Args:
            to_recipients (list): list of Receiver's email addresses. Defaults to ["ms365automation@framework.com"]
            subject (str, optional): email subject. Defaults to "test email".
            content (str, optional): content of the email. Defaults to ": We are all set".
            importance (MS365Importance, optional): Importance set for email. Defaults to MS365Importance.NORMAL
                Possible values are MS365Importance.NORMAL.value, MS365Importance.HIGH.value, MS365Importance.LOW.value
            attachments (list, optional): List of file to be sent as attachments, its list of filepaths
            ex:
            attachments = [
                            "attachment.txt",
                            "doc1.doc",
                            "pdf_file.pdf"
                            ],
            cc_recipients (list, optional): list of email addresses of CC recipients. Defaults to [],
            **kwargs: A set of keyword arguments for constructing an email.
        Returns:
            json: email message in json format
        """
        email_message = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": content},
                "toRecipients": [],
                "importance": importance,
            }
        }
        to_recipients_arr = []
        for email in to_recipients:
            to_recipients_arr.append({"emailAddress": {"address": email}})
        email_message["message"]["toRecipients"] = to_recipients_arr
        if to_recipients_arr:
            email_message["message"]["toRecipients"] = to_recipients_arr

        cc_recipients_arr = []
        for email in cc_recipients:
            cc_recipients_arr.append({"emailAddress": {"address": email}})
        if cc_recipients_arr:
            email_message["message"]["ccRecipients"] = cc_recipients_arr

        attachment_obj_arr = []
        for file_path in attachments:
            obj = self.construct_attachment_object(file_path=file_path)
            attachment_obj_arr.append(obj)
        if attachment_obj_arr:
            email_message["message"]["attachments"] = attachment_obj_arr

        for key, val in kwargs.items():
            email_message[key] = val
        return email_message

    def send_email(
        self,
        sender_address: str = "",
        to_recipients: list = [],
        subject: str = "",
        content: str = "",
        importance: MS365Importance = MS365Importance.NORMAL.value,
        attachments: list = [],
        cc_recipients: list = [],
        email_message: dict = {},
        **kwargs,
    ) -> Response:
        """Sends an email to a provided receipent

        Args:
            sender_address (str): email address of the sender,
            to_recipients (list): list of Receiver's email addresses. Defaults to ["ms365automation@framework.com"]
            subject (str, optional): email subject. Defaults to "test email".
            content (str, optional): content of the email. Defaults to ": We are all set".
            importance (MS365Importance, optional): Importance set for email. Defaults to MS365Importance.NORMAL
                Possible values are MS365Importance.NORMAL.value, MS365Importance.HIGH.value, MS365Importance.LOW.value
            attachments (list, optional): List of attachments, its list of filepaths
            ex:
            attachments = [
                            "attachment.txt",
                            "doc1.doc",
                            "pdf_file.pdf"
                            ],
            cc_recipients (list, optional): list of email addresses of CC recipients. Defaults to [],
            email_message (dict, optional): Email message object returned by construct_email() function.
                If this parameter is passed all other params except sender_address are ignored.
                Default is {}.
            **kwargs: A set of keyword arguments for constructing an email.

        Returns:
            response: email response object
        """
        if not email_message:
            email_message = self.construct_email(
                to_recipients=to_recipients,
                subject=subject,
                content=content,
                importance=importance,
                attachments=attachments,
                cc_recipients=cc_recipients,
                **kwargs,
            )
        url = f"{self.graph_api_endpoint}/{sender_address}/sendMail"
        logger.debug(f"URL: {url}")
        response: Response = requests.post(url=url, headers=self.get_headers(), json=email_message)
        return response

    def get_emails_by_filter(self, receiver_email: str, filter: str = "") -> Response:
        """get a specific email/s using the filter

        Args:
            receiver_email (str): receiver email id
            filter (str): query filter. Defaults to ''

        Returns:
            response: API response object
        """
        # API URI
        url = f"{self.graph_api_endpoint}/{receiver_email}/messages?${filter}"
        logger.debug(f"Get email by filter URL: {url}")
        # Make get API call
        response = requests.get(url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def construct_event_details(self, event_name: str = "", **kwargs):
        """constructs details of an event

        Args:
            event_name (str, optional): name of the event. Defaults to "".
            **kwargs: A set of keyword arguments that control the behavior of the function.

        Returns:
            request_body: json request body
        """
        request_body = {"subject": event_name}
        for key, val in kwargs.items():
            request_body[key] = val
        logger.debug(f"Event details: {request_body}")
        return request_body

    def create_event(
        self,
        user_id: str = "",
        event_details: dict = {},
        body={},
        attendees: list = [],
        recurrence: dict = {},
        location: dict = {},
        calendar_folder_id: str = "",
    ):
        """creates an outlook event

        Args:
            user_id (str): Outlook email id for which event has to be created.
            event_details (dict, optional): Details of an event. Defaults to ''.
                If event_details object is passed, all other parameters except user_id are ignored.
            body (dict, optional): dictionary containing the details of body of event.
                ex: "body":{
                    "contentType":"html",
                    "content":"<html>\r\n<head>\r\n<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">\r\n<meta content=\"text/html; charset=us-ascii\">\r\n</head>\r\n<body>\r\nDoes late morning work for you?\r\n</body>\r\n</html>\r\n"
                    },
            attendees(list, optional): List of event atttendees (dict) of the event.
                ex: "attendees":[
                        {
                            "type": AttendeeType.REQUIRED.value,
                            "status":{
                                "response":EventStatusResponse.NONE.value,
                                "time":"0001-01-01T00:00:00Z"
                            },
                            "emailAddress":{
                                "name":"Adele Vance",
                                "address":"AdeleV@contoso.onmicrosoft.com"
                            }
                        }
                    ],
            recurrence(dict, optional): Recurrence dictionary having details of recurrence of the event.
                 ex: "recurrence":{
                        "pattern":{
                            "type": PatternType.WEEKLY.value,
                            "interval":1,
                            "month":0,
                            "dayOfMonth":0,
                            "daysOfWeek":[
                                DaysOfWeek.TUESDAY.value
                            ],
                            "firstDayOfWeek":DaysOfWeek.SUNDAY.value,
                            "index":PatternIndex.FIRST.value
                        },
                        "range":{
                            "type":RecurrenceRangeType.ENDDATE.value,
                            "startDate":"2017-09-04",
                            "endDate":"2017-12-31",
                            "recurrenceTimeZone":"Pacific Standard Time",
                            "numberOfOccurrences":0
                            }
                    },
            location(dict): Dictionary describing location of the event. default = {}
                ex: Location = {"displayName": "Alex' home"}
            calendar_folder_id (str, optional): MS365 outlook calendar folder
        Returns:
            response: API response
        """
        if not event_details:
            event_details = self.construct_event_details(
                event_name="Calender event",
                body=body,
                recurrence=recurrence,
                attendees=attendees,
                location=location,
            )
        url = f"{self.graph_api_endpoint}/{user_id}/events"
        if calendar_folder_id:
            url = f"{self.graph_api_endpoint}/{user_id}/calendars/{calendar_folder_id}/events"
        logger.debug(f"Create event URL: {url}")
        response = requests.post(url=url, headers=self.get_headers(), json=event_details)
        logger.debug(f"Response: {response.json()}")
        return response

    def list_events(self, user_id: str):
        """List outlook events

        Args:
            user_id (str): email of the outlook account

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/events?$top=100000"
        logger.debug(f"url: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def delete_event(self, user_id: str, event_id: str):
        """Delete outlook event

        Args:
            user_id (str): email of the outlook account
            event_id (str): event id to be deleted

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/events/{event_id}"
        logger.debug(f"url: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def filter_events(self, user_id: str, filter: str = ""):
        """filters outlook events

        Args:
            user_id (str): user id of the outlook account
            filter (str, optional): filter to fetch the specific events. Defaults to "".

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/events?${filter}"
        logger.debug(f"Events filter URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def construct_task_details(
        self,
        title: str = "Complete Automation Task",
        categories: list[TaskCategories] = [],
        linked_resources: list = [],
        **task_details,
    ):
        """construct outlook task details

        Args:
            title (str, optional): title of the task. Defaults to "Complete Automation Task".
            categories (list, optional): List of categories applicable to the task being created.
                ex. categories = [ TaskCategories.NORMAL.value, ],
                Default = []
            linked_resources (list, optional): list of dictionary of linked_resource objects
                ex. [
                        {
                            "webUrl":"http://microsoft.com",
                            "applicationName":"Microsoft",
                            "displayName":"Microsoft"
                        },
                    ]
                Default = []
        Returns:
            response: json response body
        """
        request_body = {"title": title, "categories": categories, "linked_resources": linked_resources}
        for key, val in task_details.items():
            request_body[key] = val
        logger.debug(f"Task details: {request_body}")
        return request_body

    def get_list_of_user_task_lists(self, user_id: str, filter: str = "") -> Response:
        """lists outlook task lists

        Args:
            user_id (str): outlook user id
            filter (str): if filter is provided, api will use filter and fetch result. by default set to ""

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_id}/todo/lists?$filter={filter}&$top=100000"
        else:
            url = f"{self.graph_api_endpoint}/{user_id}/todo/lists?$top=100000"
        logger.debug(f"List tasks URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def delete_task_list(self, user_id: str, task_list_id: str):
        """Delete outlook task list

        Args:
            user_id (str): outlook user id
            task_list_id (str): Outlook task list id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/todo/lists/{task_list_id}"
        logger.debug(f"Delete task list URL: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def create_task_list(self, user_id: str = "", display_name: str = "Automation Task List"):
        """creates an outlook task list

        Args:
            user_id (str): outlook user id
            display_name (str, optional): task list name. Defaults to 'Automation Task List'.

        Returns:
            response: api response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/todo/lists"
        logger.debug(f"Create task list URL: {url}")
        request_body = {"displayName": display_name}
        response = requests.post(url=url, headers=self.get_headers(), json=request_body)
        logger.debug(f"Response: {response.json()}")
        return response

    def create_to_do_task(
        self,
        title: str = "",
        user_id: str = "",
        task_list_id: str = "",
        categories: list[TaskCategories] = [],
        linked_resources: list = [],
        task_details: dict = {},
        **kwargs,
    ):
        """creates an outlook to do task

        Args:

            title (str): Title of the task being created
            user_id (str): outlook user id
            task_list_id  (str): task list id to create the task
            categories (list, optional): List of categories applicable to the task being created.
                ex. categories = [ TaskCategories.NORMAL, ],
                Default = []
            linked_resources (list, optional): list of dictionary of linked_resource objects
                ex. [
                        {
                            "webUrl":"http://microsoft.com",
                            "applicationName":"Microsoft",
                            "displayName":"Microsoft"
                        },
                    ]
                Default = []
            task_details (dict, optional): Task details object returned by construct_task_details().
                If task_details is passed, all other parameters except user_id and task_list_id are ignored.
                Defaults to ''.

        Returns:
            response: api response
        """
        if not task_details:
            task_details = self.construct_task_details(
                title=title, categories=categories, linked_resources=linked_resources, **kwargs
            )
        url = f"{self.graph_api_endpoint}/{user_id}/todo/lists/{task_list_id}/tasks"
        logger.debug(f"Create to do task URL: {url}")
        response = requests.post(url=url, headers=self.get_headers(), json=task_details)
        logger.debug(f"Response: {response.json()}")
        return response

    def filter_tasks_from_list(self, user_id: str, task_list_id: str = "", filter: str = ""):
        """filter tasks from outlook

        Args:
            user_id (str): outlook user id
            task_list_id (str, optional): outlook task id. Defaults to "".
            filter (str, optional): filter to fetch the specific tasks from the task list. Defaults to "".

        Returns:
            response: API response"""
        url = f"{self.graph_api_endpoint}/{user_id}/todo/lists/{task_list_id}/tasks?${filter}"
        logger.debug(f"filter tasks from list URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def construct_contact_details(
        self,
        given_name: str = "Automation",
        surname: str = "365",
        business_phones: list = ["+1 732 555 0102"],
        email_addresses: list = [],
        **kwargs,
    ):
        """construct outlook contact details
        Args:
            given_name (str, optional): first name of the outlook contact. Defaults to "Automation".
            middle_name (str, optional): middle name of the outlook contact. Defaults to "".
            surname (str, optional): surname of the outlook contact. Defaults to "MS".
            business_phones (list): list of business phone nos.
                Defaults to ["+1 732 555 0102"]
            email_addresses (list, optional): list of email addresses dict of the outlook contact.
                Defaults to [{"address": "ms365automation@framework.com", "name": "MS365Automation"}].
            **kwargs: key, value pairs of additional parameters if needed for forming contact
        Returns:
            request_body: json request body
        """
        logger.info(email_addresses)
        request_body = {
            "givenName": given_name,
            "surname": surname,
            "emailAddresses": email_addresses,
            "businessPhones": business_phones,
        }
        for key, val in kwargs.items():
            request_body[key] = val
        logger.debug(f"Contact details: {request_body}")
        return request_body

    def create_contact(
        self,
        user_id: str = "",
        given_name: str = "",
        surname: str = "",
        email_addresses: list = [],
        contact_details: dict = {},
        contacts_folder_id: str = "",
        **kwargs,
    ):
        """creates outlook contact

        Args:
            user_id (str): outlook user id
            given_name (str, optional): first name of the outlook contact. Defaults to "Automation".
            middle_name (str, optional): middle name of the outlook contact. Defaults to "365".
            surname (str, optional): surname of the outlook contact. Defaults to "MS".
            email_addresses (list, optional): list of email addresses dict of the outlook contact.
                Defaults to [{"address": "ms365automation@framework.com", "name": "MS365Automation"}].
            contact_details (dict, optional): Outlook contact object. Defaults to {}.
                If this parameter is passed, all other parameters except user_id are ignored.
            contacts_folder_id (str, optional): contacts folder id, to create the contacts. Defaults to "".
            **kwargs: A set of keyword arguments are needed to create new contact.

        Returns:
            response: API response
        """
        if not contact_details:
            contact_details = self.construct_contact_details(
                given_name=given_name,
                surname=surname,
                email_addresses=email_addresses,
                **kwargs,
            )
        url = f"{self.graph_api_endpoint}/{user_id}/contacts"
        if contacts_folder_id:
            url = f"{self.graph_api_endpoint}/{user_id}/contactFolders/{contacts_folder_id}/contacts"
        logger.debug(f"Contact URL: {url}")
        response = requests.post(url=url, headers=self.get_headers(), json=contact_details)
        logger.debug(f"Response: {response.json()}")
        return response

    def list_contacts(self, user_id: str):
        """lists outlook contacts

        Args:
            user_id (str): outlook user id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/contacts?$top=100000"
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def delete_contact(self, user_id: str, contact_id: str):
        """Delete outlook contact

        Args:
            user_id (str): outlook user id
            contact_id (str): outlook contact id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/contacts/{contact_id}"
        logger.debug(f"URL: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def filter_contacts_from_list(self, user_id: str, filter: str = ""):
        """filter outlook contacts

        Args:
            user_id (str): outlook user id
            filter (str, optional): filter to fetch the specific contacts. Defaults to "".

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_id}/contacts?${filter})"
        response = requests.get(url=url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def get_mail_folders(self, user_email_id: str, filter: str = ""):
        """Get mail folders information

        Args:
            user_email_id (str): outlook user email id
            filter (str, Optional): query to filter folders
            eg: displayName eq 'folder name'
                startswith(displayName,'folder name')

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders?$filter= {filter}"
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def get_child_folders(self, user_email_id: str, parent_folder: str = ""):
        """Get child folders information

        Args:
            user_email_id (str): outlook user email id
            parent_folder (str, Optional): Parent folder from where child folders need to fetch

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/{parent_folder}/childFolders"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def create_mail_folder(self, user_email_id: str, new_folder_name: str):
        """Create mail folder

        Args:
            user_email_id (str): outlook user email id
            new_folder_name (str): Name of the folder to be created

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders"
        folder_data = {"displayName": new_folder_name}
        logger.debug(f"URL: {url}")
        response = requests.post(url=url, headers=self.get_headers(), json=folder_data)
        return response

    def delete_mail_folder(self, user_email_id: str, mail_folder_id: str):
        """Delete MS365 outlook email folder
        Args:
            user_email_id (str): outlook user email id
            mail_folder_id (str): MS365 outlook email folder id
        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/{mail_folder_id}"
        logger.debug(f"URL: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def get_inbox_rule(self, user_email_id: str):
        """Get outlook inbox rules

        Args:
            user_email_id (str): outlook user email id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/inbox/messagerules"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def construct_inbox_rule(
        self,
        displayName: str,
        subject: str,
        folder_id: str,
        isEnabled: bool = True,
        **kwargs,
    ):
        """Create an inbox rule

        Args:
            displayName (str): inbox rule name
            subject (str): subject name
            folder_id (str): mail folder id
            isEnabled (bool, optional): inbox rule to be enable? . Defaults to "True".
            **kwargs: A set of keyword arguments are needed to construct an inbox rule.

        Returns:
            response: API response
        """
        request_body = {
            "displayName": displayName,
            "sequence": 2,
            "isEnabled": isEnabled,
            "conditions": {"subjectContains": [subject]},
            "actions": {
                "moveToFolder": folder_id,
                "stopProcessingRules": True,
            },
        }
        for key, val in kwargs.items():
            request_body[key] = val
        logger.debug(f"inbox rule details: {request_body}")
        return request_body

    def create_inbox_rule(
        self,
        user_email_id: str,
        subject: str,
        folder_id: str,
        inbox_rule_name: str = "inbox_rule",
        inbox_rule_details: str = "",
        **kwargs,
    ):
        """Create an inbox rule

        Args:
            user_email_id (str): outlook user email id
            subject (str): subject name
            folder_id (str): mail folder id
            inbox_rule_name (str, optional): inbox rule name. Defaults to "inbox_rule"
            inbox_rule_details (str, optional): outlook inbox rule details object . Defaults to "".
            **kwargs: A set of keyword arguments are needed to construct an inbox rule.

        Returns:
            response: API response
        """
        if not inbox_rule_details:
            inbox_rule_details = self.construct_inbox_rule(
                inbox_rule_name,
                subject,
                folder_id,
                **kwargs,
            )
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/inbox/messageRules"
        logger.debug(f"URL: {url}")
        response = requests.post(url=url, headers=self.get_headers(), json=inbox_rule_details)
        return response

    def get_identifier_of_filtered_email(
        self, receiver_email: str, filter: str = "", folder_id: str = "", fetch_all: bool = False
    ) -> Union[list, str, None]:
        """get a specific email/s using the filter

        Args:
            receiver_email (str): receiver email id
            filter (str): query filter. Defaults to ''
            folder_id (str): folder_id in which email has to be searched.
            fetch_all (boolean, optional): returns all the items if this parameter sets True. Default to False.

        Returns:
            response: returns list if fetch_all set to True.
                      returns first matched item in the response if fetch_all set to False.
                      returns None if you didn't get any response.
        """
        # API URI
        # TODO : Need to check both APIs below for expected functionality
        all_identifiers = []
        if not folder_id:
            url = f"{self.graph_api_endpoint}/{receiver_email}/messages?$filter={filter}"
        else:
            url = f"{self.graph_api_endpoint}/{receiver_email}/mailFolders/{folder_id}/messages?$filter={filter}"
        logger.debug(f"Get email by filter URL: {url}")
        # Make get API call
        response = requests.get(url, headers=self.get_headers())
        found_email = response.json()
        email_id = None
        # Extract id of the found email
        if fetch_all:
            for each_item in found_email["value"]:
                all_identifiers.append(each_item["id"])
            return all_identifiers
        elif found_email["value"]:
            email_id = found_email["value"][0]["id"]
            logger.info(f"Found email with ID: {email_id}")
            return email_id
        else:
            return

    async def create_ms365_user_account(
        self,
        password,
        account_enabled: bool = True,
        display_name: str = "Test Automation",
        mail_nickname: str = "Sanity",
        user_principal_name: str = "sanity.testautomation@ms365br.onmicrosoft.com",
        force_change_password_next_sign_in: bool = False,
    ) -> Union[User, None]:
        """Creates MS365 user account in the specified domain

        Args:
            password (str): MS365 user password
            account_enabled (bool, optional): Flag to enable the MS365 account
            display_name (str, optional): MS365 user display name. Defaults to "Test Automation".
            mail_nickname (str, optional): MS365 user nick name. Defaults to "Sanity".
            user_principal_name (str, optional): MS365 user principal name. Defaults to "sanity.testautomation@ms365br.onmicrosoft.com".
            force_change_password_next_sign_in (str, optional): Flag to change the password for next sign in. Defaults to False.

        Returns:
            Union[User, None]: Success: MS365 user account information, Failure: None
        """
        graph_client = self.get_ms_graph_client()
        if graph_client is None:
            return None

        request_body = User(
            account_enabled=account_enabled,
            display_name=display_name,
            mail_nickname=mail_nickname,
            user_principal_name=user_principal_name,
            password_profile=PasswordProfile(
                force_change_password_next_sign_in=force_change_password_next_sign_in,
                password=password,
            ),
        )
        logger.debug(f"Request body: {request_body}")
        try:
            result = await graph_client.users.post(request_body)
            return result
        except Exception as e:
            logger.error(f"Failed to get the MS365 user accounts, error: {e}")
            return None

    async def fetch_ms365_users_account(self) -> Union[List[User], None]:
        """Get the list of MS365 user accounts information

        Returns:
            Union[List[User], None]: Success: list of MS365 user account information, Failure: None
        """
        graph_client = self.get_ms_graph_client()
        if graph_client is None:
            return None
        try:
            user_accounts_list = await graph_client.users.get()
            return user_accounts_list.value
        except Exception as e:
            logger.error(f"Failed to get the MS365 user accounts, error: {e}")
            return None

    async def delete_ms365_user_account(self, user_id: str) -> Union[None, bool]:
        """Delete the MS365 user account from the organization

        Args:
            user_id (str): User ID to be deleted from the organization account

        Returns:
            Union[User, None]: Success: bool, Failure: None
        """
        graph_client = self.get_ms_graph_client()
        if graph_client is None:
            return None
        try:
            await graph_client.users.by_user_id(user_id).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete the MS365 user account, error: {e}")
            return None

    async def get_ms365_user_account_information(self, user_id: str) -> Union[User, None]:
        """Get the MS365 user account information

        Args:
            user_id (str): MS365 account user ID to get the information

        Returns:
            Union[User, None]: Success: MS365 user account information, Failure: None
        """
        graph_client = self.get_ms_graph_client()
        if graph_client is None:
            return None
        try:
            result = await graph_client.users.by_user_id(user_id).get()
            return result
        except Exception as e:
            logger.error(f"Failed to delete the MS365 user account, error: {e}")
            return None

    def get_hash_of_message(
        self,
        user_id: str,
        item_id: str,
        use_graph_filter=False,
        attachment_filter=["name", "contentType", "contentBytes"],
        item_filter=["subject", "receivedDateTime", "body"],
    ) -> str:
        """
        This function returns hash of email message.

        Args:
            user_id (str): UserID of concerned user whose mailbox contains email
            item_id (str): Identifier of email message
            use_graph_filter (bool, optional): Flag if filter has to be used to get email. Defaults to False.
            attachment_filter (list, optional): Attachment specific filter. Defaults to ["name", "contentType", "contentBytes"].
            item_filter (list, optional): Filter to be used for getting email message. Defaults to ["subject", "receivedDateTime", "body"].

        Raises:
            Exception: Exception will be raised if email message not found or checksum returned is empty string.

        Returns:
            str: Checksum of email message pointed by user_id and item_id.
        """
        ck_sum = ""
        try:
            ck_sum = self.chksum_tool.HashMessage(
                attachment_filter, item_filter, user_id, item_id, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for message_id:{item_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_message encountered exception {e} while getting chksum for message_id:{item_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of message is: {ck_sum}")
        return ck_sum

    def get_hash_of_messages(
        self,
        user_id: str,
        item_ids: list,
        use_graph_filter=False,
        attachment_filter=["name", "contentType", "contentBytes"],
        item_filter=["subject", "receivedDateTime", "body"],
    ) -> list:
        """
        This function returns list of hashes of emails pointed by email_ids.

        Args:

            user_id (str): UserID of concerned user whose mailbox contains email
            item_ids (list): List of identifiers of email message
            use_graph_filter (bool, optional): Flag if filter has to be used to get email. Defaults to False.
            attachment_filter (list, optional): Attachment specific filter. Defaults to ["name", "contentType", "contentBytes"].
            item_filter (list, optional): Filter to be used for getting email message. Defaults to ["subject", "receivedDateTime", "body"]

        Raises:
            Exception: Exception will be raised if email message not found or checksum returned is empty string.

        Returns:
            List of checksum of email message pointed by user_id and item_ids.
        """
        ck_sum_list = []
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        for item_id in item_ids:
            ck_sum = self.get_hash_of_message(user_id, item_id, use_graph_filter, attachment_filter, item_filter)
            ck_sum_list.append(ck_sum)
        return ck_sum_list

    def get_hash_of_messages_folder(
        self,
        user_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=["name", "contentType", "contentBytes"],
        item_filter=["subject", "receivedDateTime", "body"],
        folder_filter=["displayName", "totalItemCount", "sizeInBytes"],
    ) -> str:
        """
        Returns combined hash of folder pointed by user_id and folder_id combination.

        Args:
            user_id (str): UserID of concerned user whose mailbox contains email
            folder_id (str): Identifier of email message folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get email. Defaults to False.
            attachment_filter (list, optional): Attachment specific filter. Defaults to ["name", "contentType", "contentBytes"].
            item_filter (list, optional): Filter to be used for getting email message. Defaults to ["subject", "receivedDateTime", "body"]
            "folder_filter (list, optional): Filter to be used for getting folder details. Defaults to ["displayName", "totalItemCount", "sizeInBytes"]
        Raises:
            Exception: Exception will be raised if email message folder is not found or checksum returned is empty string.

        Returns:
            str: Checksum of email message folder pointed by user_id and folder_id.
        """
        ck_sum = ""
        try:
            ck_sum = self.chksum_tool.HashMessageFolder(user_id, folder_id).ContentAsSingleDigest(
                attachment_filter, item_filter, folder_filter, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for folder_id:{folder_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_message_folder encountered exception {e} while getting chksum for folder_id:{folder_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of folder is: {ck_sum}")
        return ck_sum

    def get_hash_of_contact(
        self,
        user_id: str,
        item_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> str:
        """
        Returns hash of contact passed as input via item_id

        Args:
            user_id (str): UserID of concerned user whose mailbox contains contact
            item_id (str): Identifier of the contact
            folder_id (str): Identifier of contact folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get contact. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if contact is not found or checksum returned is empty string.

        Returns:
            Checksum of contact pointed by user_id and item_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashContactFolder(user_id, folder_id).Item(
                attachment_filter, item_filter, item_id, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for contact_id:{item_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_contact encountered exception {e} while getting chksum for contact_id:{item_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of contact is: {ck_sum}")
        return ck_sum

    def get_hash_of_contacts(
        self,
        user_id: str,
        item_ids: list,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> list:
        """
        Returns list of hashes of contacts passed as input via items_ids

        Args:
            user_id (str): UserID of concerned user whose mailbox contains contact
            item_ids (list): List of identifiers of the contacts
            folder_id (str): Identifier of contact folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get contact. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Returns:
            List of checksum of contacts pointed by user_id and item_ids.
        """
        ck_sum_list = []
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        for item_id in item_ids:
            ck_sum = self.get_hash_of_contact(
                user_id, item_id, folder_id, use_graph_filter, attachment_filter, item_filter
            )
            ck_sum_list.append(ck_sum)
        return ck_sum_list

    def get_hash_of_contacts_folder(
        self,
        user_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
        folder_filter=[],
    ) -> str:
        """
        Returns hash of contacts folder pointed by folder_id

        Args:
            user_id (str): UserID of concerned user whose mailbox contains contacts folder
            folder_id (str): Identifier of contact folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get contact. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if folder is not found or checksum returned is empty string.

        Returns:
            Checksum of contact folder pointed by user_id and folder_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        if not folder_filter:
            folder_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashContactFolder(user_id, folder_id).ContentAsSingleDigest(
                attachment_filter, item_filter, folder_filter, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for folder_id:{folder_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_contact_folder encountered exception {e} while getting chksum for folder_id:{folder_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of folder is: {ck_sum}")
        return ck_sum

    def get_hash_of_task(
        self,
        user_id: str,
        item_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> str:
        """
        Returns hash of task pointed by item_id

        Args:
            user_id (str): UserID of concerned user whose mailbox contains task
            item_id (str): Identifier of the task
            folder_id (str): Identifier of task folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get task. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if task is not found or checksum returned is empty string.

        Returns:
            Checksum of task pointed by user_id and item_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashTodoFolder(user_id, folder_id).Item(
                attachment_filter, item_filter, item_id, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for task_id:{item_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_task encountered exception {e} while getting chksum for task_id:{item_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of task is: {ck_sum}")
        return ck_sum

    def get_hash_of_tasks(
        self,
        user_id: str,
        item_ids: list,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> list:
        """
        Returns list of hashes of tasks which were passed as input via items_ids
        Args:
            user_id (str): UserID of concerned user whose mailbox contains task
            item_ids (list): List of identifier of the task
            folder_id (str): Identifier of task folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get task. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Returns:
            List of checksum of tasks pointed by user_id and item_ids.
        """
        ck_sum_list = []
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        for item_id in item_ids:
            ck_sum = self.get_hash_of_task(
                user_id, item_id, folder_id, use_graph_filter, attachment_filter, item_filter
            )
            ck_sum_list.append(ck_sum)
        return ck_sum_list

    def get_hash_of_tasks_folder(
        self,
        user_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
        folder_filter=[],
    ) -> str:
        """
        Returns hash of task folder passed as input via folder_id

        Args:
            user_id (str): UserID of concerned user whose mailbox contains tasks folder
            folder_id (str): Identifier of task folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get task. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if folder is not found or checksum returned is empty string.

        Returns:
            Checksum of task folder pointed by user_id and folder_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        if not folder_filter:
            folder_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashTodoFolder(user_id, folder_id).ContentAsSingleDigest(
                attachment_filter, item_filter, folder_filter, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for folder_id:{folder_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_task_folder encountered exception {e} while getting chksum for folder_id:{folder_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of folder is: {ck_sum}")
        return ck_sum

    def get_hash_of_event(
        self,
        user_id: str,
        item_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> str:
        """
        Returns hash of event which is passed as input, pointed by item_id

        Args:
            user_id (str): UserID of concerned user whose mailbox contains event
            item_id (str): Identifier of the event
            folder_id (str): Identifier of event folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get event. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if event is not found or checksum returned is empty string.

        Returns:
            Checksum of event pointed by user_id and item_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashEventFolder(user_id, folder_id).Item(
                attachment_filter, item_filter, item_id, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for event_id:{item_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_event encountered exception {e} while getting chksum for event_id:{item_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of event is: {ck_sum}")
        return ck_sum

    def get_hash_of_events(
        self,
        user_id: str,
        item_ids: list,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
    ) -> list:
        """
        Returns hash of events list which is passed as input.

        Args:
            user_id (str): UserID of concerned user whose mailbox contains event
            item_ids (list): List of identifier of the event
            folder_id (str): Identifier of event folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get event. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Returns:
            List of checksum of events pointed by user_id and item_ids.
        """
        ck_sum_list = []
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        for item_id in item_ids:
            ck_sum = self.get_hash_of_event(
                user_id, item_id, folder_id, use_graph_filter, attachment_filter, item_filter
            )
            ck_sum_list.append(ck_sum)
        return ck_sum_list

    def get_hash_of_events_folder(
        self,
        user_id: str,
        folder_id: str,
        use_graph_filter=False,
        attachment_filter=[],
        item_filter=[],
        folder_filter=[],
    ) -> str:
        """
        Returns hash of events folder pass which ias passed as input (folder_id)

        Args:
            user_id (str): UserID of concerned user whose mailbox contains events folder
            folder_id (str): Identifier of events folder
            use_graph_filter (bool, optional): Flag if filter has to be used to get event. Defaults to False.
            attachment_filter (list, optional): Defaults to [].
            item_filter (list, optional): Defaults to [].

        Raises:
            Exception: Exception will be raised if folder is not found or checksum returned is empty string.

        Returns:
            Checksum of event folder pointed by user_id and folder_id.
        """
        ck_sum = ""
        if not attachment_filter:
            attachment_filter = self.attachment_filter
        if not item_filter:
            item_filter = self.item_filter
        if not folder_filter:
            folder_filter = self.item_filter
        try:
            ck_sum = self.chksum_tool.HashEventFolder(user_id, folder_id).ContentAsSingleDigest(
                attachment_filter, item_filter, folder_filter, useGraphFilter=use_graph_filter
            )
            if not ck_sum:
                msg = f"Unable to get Hash for folder_id:{folder_id} for user_id:{user_id}"
                logger.error(msg)
                raise Exception(msg)
        except Exception as e:
            err = f"Function get_hash_of_events_folder encountered exception {e} while getting chksum for folder_id:{folder_id} for user_id:{user_id}"
            logger.error(err)
            raise Exception(e)
        logger.info(f"ck_sum of folder is: {ck_sum}")
        return ck_sum

    def get_contacts_folders(self, user_email_id: str, filter: str = "") -> Response:
        """Get contacts folders information

        Args:
            user_email_id (str): outlook user email id
            filter (str): if filter is provided, api will use filter and fetch result. by default set to ""

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders?$filter={filter}&$top=100000"
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def get_contacts_child_folder(self, user_email_id: str, parent_folder_id: str, filter: str = "") -> Response:
        """Get Child Folders information from a particular parent contactFolder

        Args:
            user_email_id (str): outlook user email id
            parent_folder_id (str): Parent Folder identifier from where child folder need to fetch.
            filter (str): if filter is provided, api will use filter and fetch result. by default set to ""

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders/{parent_folder_id}/childFolders?$filter={filter}&$top=100000"
        else:
            url = (
                f"{self.graph_api_endpoint}/{user_email_id}/contactFolders/{parent_folder_id}/childFolders?$top=100000"
            )
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def get_contacts_from_contacts_folder(self, user_email_id: str, folder_id: str, filter: str = "") -> Response:
        """Get all the contacts information from the contactFolders.

        Args:
            user_email_id (str): outlook user email id
            folder_id (str): Folder Identifier from where all the contacts need to fetch
            filter (str, optional): if filter is provided, api will use filter and fetch result. by default set to ""

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders/{folder_id}/contacts?$filter={filter}&$top=100000"
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders/{folder_id}/contacts?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def get_calendar_events(self, user_email_id: str, calendar_id: str, filter: str = "") -> Response:
        """Get all the calender events information from the calenders.

        Args:
            user_email_id (str): outlook user email id
            calendar_id (str): calender identifier from where events need to fetch
            filter (str, optional): if filter is provided, api will use filter and fetch result. by default set to ""

        Returns:
            response: API response
        """
        if filter:
            url = (
                f"{self.graph_api_endpoint}/{user_email_id}/calendars/{calendar_id}/events?$filter={filter}&$top=100000"
            )
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/calendars/{calendar_id}/events?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def get_tasks_in_todo_list(self, user_email_id: str, todo_list_id: str, filter: str = "") -> Response:
        """Get all the tasks information from the todo list.

        Args:
            user_email_id (str): outlook user email id
            todo_list_id (str): todo list identifier from where tasks need to fetch
            filter (str, optional): if filter is provided, api will use filter and fetch result. Defaults to "".

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/todo/lists/{todo_list_id}/tasks?$filter={filter}&$top=100000"
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/todo/lists/{todo_list_id}/tasks?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def delete_contacts_folder(self, user_email_id: str, contacts_folder_id: str):
        """Delete contacts folder

        Args:
            user_email_id (str): outlook user email id
            contacts_folder_id (str): outlook contact folder id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders/{contacts_folder_id}"
        logger.debug(f"URL: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def create_contacts_folder(self, user_email_id: str, display_name: str = "automation_contacts"):
        """Create contacts folder

        Args:
            user_email_id (str): outlook user email id
            display_name (str): Name of the folder to be created. Defaults to "automation_contacts".

        Returns:
            response: API response
        """
        # Microsoft Graph API endpoint for creating contacts
        url = f"{self.graph_api_endpoint}/{user_email_id}/contactFolders"
        logger.debug(f"URL: {url}")

        # Create a contact folder
        folder_payload = {"displayName": display_name}
        response = requests.post(url=url, headers=self.get_headers(), json=folder_payload)
        return response

    def get_calendar_folders(self, user_email_id: str, filter: str = ""):
        """Get calendar folders information

        Args:
            user_email_id (str): outlook user email id

        Returns:
            response: API response
        """
        if filter:
            url = f"{self.graph_api_endpoint}/{user_email_id}/calendars?$filter={filter}&top=100000"
        else:
            url = f"{self.graph_api_endpoint}/{user_email_id}/calendars?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url=url, headers=self.get_headers())
        return response

    def delete_calendar_folder(self, user_email_id: str, calendar_folder_id: str):
        """Delete calendar folder

        Args:
            user_email_id (str): outlook user email id
            calendar_folder_id (str): calendar folder id

        Returns:
            response: API response
        """
        url = f"{self.graph_api_endpoint}/{user_email_id}/calendars/{calendar_folder_id}"
        logger.debug(f"URL: {url}")
        response = requests.delete(url=url, headers=self.get_headers())
        return response

    def create_calendar_folder(self, user_email_id: str, display_name: str = "automation_calendar"):
        """Create calendar folder

        Args:
            user_email_id (str): outlook user email id
            display_name (str): Name of the folder to be created. Defaults to "automation_calendar".

        Returns:
            response: API response
        """
        # Microsoft Graph API endpoint for creating contacts
        url = f"{self.graph_api_endpoint}/{user_email_id}/calendars"
        logger.debug(f"URL: {url}")

        # Create a contact folder
        folder_payload = {"name": display_name}
        response = requests.post(url=url, headers=self.get_headers(), json=folder_payload)
        return response

    def get_email_messages_from_folder(self, user_email_id: str, folder_name: str = "Inbox") -> Response:
        """get email messages from a specific folder
        Args:
            user_email_id (str): MS365 outlook user email id
            folder_name (str): MS365 outlook mail folder name. Defaults to "Inbox"
        Returns:
            response: API response object
        """
        # API URI
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/{folder_name}/messages?$top=100000"
        logger.debug(f"URL: {url}")
        response = requests.get(url, headers=self.get_headers())
        logger.debug(f"Response: {response.json()}")
        return response

    def delete_email_message_from_folder(
        self, user_email_id: str, message_id: str, folder_name: str = "Inbox"
    ) -> Response:
        """Delete email message from the folder
        Args:
            user_email_id (str): MS365 outlook user email id
            message_id (str): MS365 outlook message id
            folder_name (str): MS365 outlook mail folder name. Defaults to "Inbox"
        Returns:
            response: API response object
        """
        # API URI
        url = f"{self.graph_api_endpoint}/{user_email_id}/mailFolders/{folder_name}/messages/{message_id}"
        logger.debug(f"URL: {url}")
        response = requests.delete(url, headers=self.get_headers())
        return response

    def kill_checksum_tool_workers(self):
        """
        This method will kill the workers created as part of checksumTool() object.
        """
        self.chksum_tool.KillWorkers()

    async def get_users_list(self) -> list[User]:
        """Returns a list of all the available users

        Returns:
            list[User]: List of users
        """
        graph_client = self.get_ms_graph_client()
        result = await graph_client.users.get()
        logger.info(f"Users list fetched {result.value}")
        return result.value

    async def get_user_by_user_principal_name(self, user_principal_name: str) -> User:
        """Returns a user object by its User Principal Name i.e. email address

        Args:
            user_principal_name (str): User Principal Name i.e email address of the user

        Returns:
            User: User object
        """
        users_list = asyncio.get_event_loop().run_until_complete(self.get_users_list())
        users = [user for user in users_list if user.user_principal_name == user_principal_name]
        logger.info(f"User with {user_principal_name}: {users}")
        return users[0] if len(users) == 1 else None

    async def remove_phone_authentication_mfa_for_user(self, user_principal_name: str):
        """Removes Phone Authentication / MFA for the given user

        Args:
            user_principal_name (str): User Principal Name i.e email address of the user
        """
        graph_client = self.get_ms_graph_client()
        result = await graph_client.users.get()
        users_list: list[User] = result.value
        users = [user for user in users_list if user.user_principal_name == user_principal_name]
        user = users[0] if len(users) == 1 else None

        if user:
            result = await graph_client.users.by_user_id(user_id=user.id).authentication.phone_methods.get()

            if result.value:
                logger.info(f"Removing phone number MFA for user {user_principal_name}")
                await graph_client.users.by_user_id(
                    user_id=user.id
                ).authentication.phone_methods.by_phone_authentication_method_id(result.value[0].id).delete()

    async def add_phone_authentication_mfa_for_user(self, user_principal_name: str, phone_number: str):
        """Adds Phone Authentication / MFA for the given user

        Args:
            user_principal_name (str): User Principal Name i.e email address of the user
            phone_number (str): Phone number to be added. Should be in format +1 1234567890
        """
        graph_client = self.get_ms_graph_client()
        result = await graph_client.users.get()
        users_list: list[User] = result.value
        users = [user for user in users_list if user.user_principal_name == user_principal_name]
        user = users[0] if len(users) == 1 else None

        if user:
            logger.info(f"Adding phone number {phone_number} MFA for user {user_principal_name}")
            request_body = PhoneAuthenticationMethod(
                phone_number=phone_number,
                phone_type=AuthenticationPhoneType.Mobile,
            )
            result = await graph_client.users.by_user_id(user_id=user.id).authentication.phone_methods.post(
                request_body,
            )
            logger.info(f"Phone Authentication added {result}")

    async def assign_role_to_user(self, user_id: str, role_name: str = "Global Administrator") -> UnifiedRoleAssignment:
        """Assigns a role to the specified user

        Args:
            user_id (str): ID of the user
            role_name (str, optional): Name of the Role which needs to be assigned to the specified user
            Defaults to "Global Administrator".

        Returns:
            UnifiedRoleAssignment: UnifiedRoleAssignment object
        """
        graph_client = self.get_ms_graph_client()
        role_assignment = await graph_client.directory_roles.get()
        application_role = [role for role in role_assignment.value if role.display_name == role_name][0]

        logger.info(f"Adding role: {role_name}, {application_role.role_template_id} to user: {user_id}")
        request_body = UnifiedRoleAssignment(
            odata_type="#microsoft.graph.unifiedRoleAssignment",
            role_definition_id=application_role.role_template_id,
            principal_id=user_id,
            directory_scope_id="/",
        )

        role_assignment = await graph_client.role_management.directory.role_assignments.post(request_body)
        logger.info(f"Role {role_name} assigned to user: {user_id}")
        return role_assignment

    async def remove_user_assigned_role(self, role_assignment_id: str) -> bool:
        """Removes an assigned role

        Args:
            role_assignment_id (str): Role Assignment ID

        Returns:
            bool: 'True' if the action is successful, else 'False'
        """
        graph_client = self.get_ms_graph_client()
        try:
            await graph_client.role_management.directory.role_assignments.by_unified_role_assignment_id(
                role_assignment_id
            ).delete()
            logger.info(f"Successfully removed role assignment {role_assignment_id}")
            return True
        except Exception as e:
            logger.info(f"Error removing role assignment {role_assignment_id}: {e}")
            return False

    def create_user_and_assign_role(
        self,
        user_principal_name: str,
        display_name: str,
        mail_nickname: str,
        password: str,
        role_name: str = "Global Administrator",
        force_change_password_next_sign_in: bool = False,
    ) -> Union[User, UnifiedRoleAssignment]:
        """A wrapper function to create a user account and assign a role to the created user

        Args:
            user_principal_name (str): Email Address to be associated to the user
            display_name (str): User's display name
            mail_nickname (str): User's nickname
            password (str): Password for the user's account
            role_name (str, optional): Name of the role to be assigned to the user. Defaults to "Global Administrator".
            force_change_password_next_sign_in (bool, optional): Defaults to False.

        Returns:
            Union[User, UnifiedRoleAssignment]: Created user and the assigned role
        """
        user = asyncio.get_event_loop().run_until_complete(
            self.create_ms365_user_account(
                password=password,
                account_enabled=True,
                display_name=display_name,
                mail_nickname=mail_nickname,
                user_principal_name=user_principal_name,
                force_change_password_next_sign_in=force_change_password_next_sign_in,
            )
        )

        logger.info(f"Created user {display_name}: {user}")

        role_assignment = asyncio.get_event_loop().run_until_complete(
            self.assign_role_to_user(
                user_id=user.id,
                role_name=role_name,
            )
        )
        logger.info(f"Assigned role: {role_name} to user: {display_name}")

        return user, role_assignment

    def remove_role_assignment_and_delete_user_account(self, role_assignment_id: str, user_id: str):
        """Removes the specified role from the user account and deletes the user

        Args:
            role_assignment_id (str): ID of the role to be removed from the user
            user_id (str): ID of the user to be deleted
        """
        asyncio.get_event_loop().run_until_complete(
            self.remove_user_assigned_role(role_assignment_id=role_assignment_id)
        )

        asyncio.get_event_loop().run_until_complete(self.delete_ms365_user_account(user_id=user_id))

    async def list_service_principals(self) -> ServicePrincipalCollectionResponse:
        """Lists all Service Principals in the account

        Returns:
            ServicePrincipalCollectionResponse: Coroutine of all Service Principals
        """
        graph_client = self.get_ms_graph_client()
        service_principals = await graph_client.service_principals.get()
        return service_principals

    async def get_service_principal_by_id(self, service_principal_id: str) -> ServicePrincipal:
        """Retrieves a Service Principal by its ID

        Returns:
            ServicePrincipal: Coroutine of Service Principal by its ID
        """
        graph_client = self.get_ms_graph_client()
        service_principal = await graph_client.service_principals.by_service_principal_id(service_principal_id).get()
        return service_principal

    async def delete_service_principal_by_id(self, service_principal_id: str):
        """Deletes a Service Principal by its ID"""
        graph_client = self.get_ms_graph_client()
        await graph_client.service_principals.by_service_principal_id(service_principal_id).delete()
