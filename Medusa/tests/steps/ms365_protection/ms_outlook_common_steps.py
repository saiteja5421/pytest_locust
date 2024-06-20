import logging
import time
import requests
import asyncio
from typing import List, Union
from msgraph.generated.models.user import User

from datetime import datetime, timedelta
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
from lib.platform.ms365.ms_outlook_manager import MSOutlookManager

logger = logging.getLogger()


def send_email_message_and_validate(
    ms_context: MSOfficeContext,
    sender_email_id: str,
    receiver_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    subject: str = "MS365 Framework",
    content: str = "Hello, let's create MS outlook automation framework.",
    **kwargs,
):
    """Send an outlook email message and validate

    Args:
        ms_context (MSOfficeContext): MS365 context object
        sender_email_id (str): sender email address
        receiver_email_id (str): receiver email address
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        subject (str, optional): email subject. defaults to "MS365 Framework"
        content (str, optional): email content. Defaults to "Hello, let's create MS outlook automation framework.",
        kwargs: key, value pair(s) of additional arguments for sending an email
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    email_message = ms_outlook_manager.construct_email(
        to_recipients=[receiver_email_id], subject=subject, content=content, **kwargs
    )
    email_response = ms_outlook_manager.send_email(sender_address=sender_email_id, email_message=email_message)
    assert (
        email_response.status_code == requests.codes.accepted
    ), f"Failed to send an email to the user: {receiver_email_id}, Email response: {email_response.json()}"
    logger.info(f"Email sent successfully to the recipient: {receiver_email_id}")


def validate_email_message(
    ms_context: MSOfficeContext,
    sender_email_id: str,
    receiver_email_id: str,
    subject: str,
    date: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Validate email message

    Args:
        ms_context (MSOfficeContext): MS365 context object
        sender_email_id (str): sender email address
        receiver_email_id (str): receiver email address
        subject (str): email subject
        date (str): email sent date
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    filter = f"filter=startswith(from/emailAddress/address, '{sender_email_id}') and subject eq '{subject}' and receivedDateTime ge {date}"
    logger.info(f"Filter: {filter}")
    email_response = ms_outlook_manager.get_emails_by_filter(receiver_email_id, filter)
    assert (
        email_response.status_code == requests.codes.ok
    ), f"Failed to get the specified email/s, response: {email_response.json()}"
    logger.info(f"Successfully get the specified email/s {email_response.json()}")


def get_current_date():
    """Get current date

    Returns:
        Formatted date as YYYY-MM-DD
    """
    # Get the current date
    current_date = datetime.now()

    # Format the date as "YYYY-MM-DD"
    formatted_date = current_date.strftime("%Y-%m-%d")
    logger.info(f"Date: {formatted_date}")
    return formatted_date


def create_event_and_validate(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    event_name: str = "Create MS365 Framework",
    **kwargs,
):
    """Create and validate outlook event

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        event_name (str, optional): Name of the event. Defaults to "Create MS365 Framework".
        kwargs: key, value pairs of additional args needed to create calendar event
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    # Construct event details
    event_details = ms_outlook_manager.construct_event_details(event_name=event_name, **kwargs)

    # Create Event
    event_response = ms_outlook_manager.create_event(user_email_id, event_details)
    assert (
        event_response.status_code == requests.codes.created
    ), f"Failed to create an outlook event for the user: {user_email_id}, Event response: {event_response.json()}"
    logger.info(
        f"Successfully created outlook event for the user: {user_email_id} Event response: {event_response.json()}"
    )


def create_task_list_and_get_id(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    display_name: str = "automation_tasks_list",
) -> str:
    """Create a task list and return the task list id

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        display_name (str, optional): task list name. Defaults to "automation_tasks_list".

    Returns:
        to_do_task_list_id (str): task list id
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify MS365 outlook todo task list with name: {display_name}")
    response = ms_outlook_manager.get_list_of_user_task_lists(user_email_id)
    assert (
        response.status_code == requests.codes.ok
    ), f"Failed to get outlook task info with name {display_name}, response:{response.text}"
    existing_lists = response.json().get("value", [])
    to_do_task_list_id = None
    for folder in existing_lists:
        if folder.get("displayName") == display_name:
            to_do_task_list_id = folder.get("id")
            logger.info(f"To do task list with name: {display_name} does not exist and ID: {to_do_task_list_id}")
            break
    if not to_do_task_list_id:
        logger.info(f"MS365 outlook to do task list with name: {display_name} does not exist, lets create...")
        # Create Task list
        task_response = ms_outlook_manager.create_task_list(user_email_id, display_name)
        assert (
            task_response.status_code == requests.codes.created
        ), f"Failed to create an outlook task list for the user: {user_email_id} and task response: {task_response.json()}"
        logger.info(
            f"Successfully created an outlook task list for the user: {user_email_id} and task list response: {task_response.json()}"
        )
        to_do_task_list_info = task_response.json()
        to_do_task_list_id = to_do_task_list_info.get("id")
        logger.info(
            f"Successfully created outlook task list with name: {display_name} and response: {to_do_task_list_info}"
        )
    return to_do_task_list_id


def create_to_do_task_and_validate(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    task_list_id: str = "",
    title: str = "Complete Automation",
    linked_resources: list = [],
    display_name: str = "automation_tasks_list",
    **kwargs,
):
    """Create to do task in a task list

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        task_list_id (str, optional): task list id, to create the task. Defaults to ''.
        title (str, optional): Name of the task. Defaults to "Complete Automation".
        linked_resources (list, optional): List of dict describing linked resource.
            ex. {application_name="Microsoft", display_name="Microsoft", web_url="http://microsoft.com"}
        display_name (str, optional): task list name. Defaults to "automation_tasks_list".
        **kwargs(optional): Additional optional parameters for creation of task
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    # Create task list if task_list_id is not passed
    if not task_list_id:
        task_list_id = create_task_list_and_get_id(
            ms_context,
            user_email_id,
            ms_outlook_manager=ms_outlook_manager,
            display_name=display_name,
        )
    # Construct task details
    task_details = ms_outlook_manager.construct_task_details(title=title, linked_resources=linked_resources, **kwargs)

    # Create to do task
    task_response = ms_outlook_manager.create_to_do_task(
        user_id=user_email_id, task_list_id=task_list_id, task_details=task_details
    )
    assert (
        task_response.status_code == requests.codes.created
    ), f"Failed to create an outlook task for the user: {user_email_id} and task response: {task_response.json()}"
    logger.info(
        f"Successfully created an outlook to do task for the user: {user_email_id} and task response: {task_response.json()}"
    )


def create_contact_and_validate(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    given_name: str = "Automation",
    surname: str = "365",
    email_addresses: list = [{"address": "ms365automation@framework.com", "name": "MS365Automation"}],
    business_phones: list = ["+1 732 555 0102"],
):
    """Create outlook contact

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        given_name (str, optional): name of the contact. Defaults to "Automation".
        surname (str, optional): surname of the contact. Defaults to "MS365".
        email_addresses (list): list of email address of the contact.
            Defaults to [{"address": "ms365automation@framework.com", "name": "MS365Automation"}].
        contact_details (str, optional): contact details object
        business_phones (list): list of phone nos. Defaults to ["+1 732 555 0102"]
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    # Construct contact details
    contact_details = ms_outlook_manager.construct_contact_details(
        given_name=given_name, surname=surname, email_addresses=email_addresses, business_phones=business_phones
    )

    # Create contact
    contact_response = ms_outlook_manager.create_contact(user_email_id, contact_details=contact_details)
    assert (
        contact_response.status_code == requests.codes.created
    ), f"Failed to create an outlook contact for the user: {user_email_id} and task response: {contact_response.json()}"
    logger.info(
        f"Successfully created an outlook contact for the user: {user_email_id} and task list response: {contact_response.json()}"
    )


def verify_and_get_mail_folder_id(
    ms_context: MSOfficeContext,
    user_email_id: str,
    folder_name: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Verify if folder exists, if exists return folderID, else create folder and return folderID.

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): outlook user email id
        folder_name (str): Name of the folder to be created
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""

    Returns:
        str: mail folder id
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify folder: {folder_name} existed or not")
    response = ms_outlook_manager.get_mail_folders(user_email_id, filter=f"displayName eq '{folder_name}'")
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    existing_folders = response.json().get("value", [])
    folder_id = None
    for folder in existing_folders:
        if folder.get("displayName") == folder_name:
            folder_id = folder.get("id")
            logger.info(f"Folder: {folder_name} already exists and ID: {folder_id}")
            break

    # If the folder doesn't exist, create a new folder
    if not folder_id:
        logger.info(f"Folder: {folder_name} not existed, lets create...")
        response = ms_outlook_manager.create_mail_folder(user_email_id, folder_name)
        assert (
            response.status_code == requests.codes.created
        ), f"Failed to create email folder, response: {response.json()}"
        created_folder = response.json()
        folder_id = created_folder.get("id")
        logger.info(f"Folder: {folder_name} created successfully and ID: {folder_id}")
    return folder_id


def verify_and_create_inbox_rule(
    ms_context: MSOfficeContext,
    user_email_id: str,
    folder_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    subject: str = "Create mailbox rule",
    inbox_rule_name: str = "inbox_rule",
):
    """Verify inbox rule, if exists skip it, if not create an inbox rule

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): user email address
        folder_id (str): inbox mail folder id
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        subject (str, optional): email subject. defaults to "Send email to a folder"
        inbox_rule_name (str, optional): inbox rule name. Defaults to "inbox_rule"

    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    # Check if the rule with the same name already exists
    get_mailbox_rule_response = ms_outlook_manager.get_inbox_rule(user_email_id)
    assert (
        get_mailbox_rule_response.status_code == requests.codes.ok
    ), f"Failed to get the inbox rule for the user: {user_email_id} and task response: {get_mailbox_rule_response.json()}"
    logger.info(
        f"Successfully got the inbox rule for the user: {user_email_id} and task response: {get_mailbox_rule_response.json()}"
    )
    existing_rules = get_mailbox_rule_response.json().get("value")
    matching_rule = next(
        (
            rule
            for rule in existing_rules
            if rule["displayName"] == inbox_rule_name and rule["actions"]["moveToFolder"] == folder_id
        ),
        None,
    )
    if matching_rule:
        logger.info(f"Inbox rule name: {inbox_rule_name} already exists, hence skipping to create a inbox rule.")
    else:
        # Create a new rule to move emails with a specific subject to the target folder
        logger.info(
            f"Creating an inbox rule with name: {inbox_rule_name} and condition as 'move the mail subject contains: {subject} to a folder ID: {folder_id}'"
        )
        inbox_rule_details = ms_outlook_manager.construct_inbox_rule(inbox_rule_name, subject, folder_id)
        create_mailbox_rule_response = ms_outlook_manager.create_inbox_rule(
            user_email_id,
            subject,
            folder_id,
            inbox_rule_name=inbox_rule_name,
            inbox_rule_details=inbox_rule_details,
        )

        assert (
            create_mailbox_rule_response.status_code == requests.codes.created
        ), f"Failed to Create an inbox rule with name: {inbox_rule_name} and condition as 'move the mail subject contains: {subject} to a folder ID: {folder_id} task response: {create_mailbox_rule_response.json()}'"
        logger.info(
            f"Successfully created an inbox rule with name: {inbox_rule_name} and condition as 'move the mail subject contains: {subject} to a folder ID: {folder_id}'"
        )


def send_multiple_emails_to_specific_folder(
    ms_context: MSOfficeContext,
    sender_email_id: str,
    receiver_email_id: str,
    folder_name: str = "automation_folder",
    ms_outlook_manager: MSOutlookManager = "",
    subject: str = "Move messages",
    content: str = "Hello, let's move messages to a specific folder",
    inbox_rule_name: str = "move_messages",
    total_no_of_emails: int = 100,
    **kwargs,
):
    """Send an outlook email messages to a specific folder

    Args:
        ms_context (MSOfficeContext): MS365 context object
        sender_email_id (str): user email address
        receiver_email_id (str): user email address
        folder_name (str, optional): mail folder name. Default to "Automation_folder"
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        subject (str, optional): email subject. defaults to "Move messages"
        content (str, optional): email content. Defaults to "Hello, let's move messages to a specific folder"
        inbox_rule_name (str, optional): inbox rule name. Defaults to "move messages"
        total_no_of_emails (int. optional): total no of mail to send. Defaults to "100"
        kwargs: key, value pair(s) of additional arguments for sending an email

    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    folder_id = verify_and_get_mail_folder_id(
        ms_context,
        sender_email_id,
        folder_name,
        ms_outlook_manager,
    )
    verify_and_create_inbox_rule(
        ms_context,
        receiver_email_id,
        folder_id,
        ms_outlook_manager=ms_outlook_manager,
        subject=subject,
        inbox_rule_name=inbox_rule_name,
    )
    logger.info("We have already created an inbox rule to move the messages to specific folder, lets send messages")
    failed_emails = 0

    # Send multiple emails to a specified folder
    for i in range(total_no_of_emails):
        if i % 5 == 0:
            email_message = ms_outlook_manager.construct_email(
                to_recipients=[receiver_email_id],
                subject=subject,
                content=content,
                **kwargs,
            )
        else:
            email_message = ms_outlook_manager.construct_email(
                to_recipients=[receiver_email_id],
                subject=subject,
                content=content,
            )
        email_response = ms_outlook_manager.send_email(sender_address=sender_email_id, email_message=email_message)
        if email_response.status_code != requests.codes.accepted:
            logger.warn(
                f"Failed to send an email to the user: {receiver_email_id}, Email response: {email_response.json()}"
            )
            failed_emails += 1
            time.sleep(5)
        logger.info(f"Email sent successfully to the recipient: {receiver_email_id}")
    created_emails = total_no_of_emails - failed_emails
    logger.warn(f"out of '{total_no_of_emails}' emails, {created_emails} emails have been sent successfully")
    logger.info(f"Successfully sent {total_no_of_emails} mails and all of them moved to a folder: {folder_name}")


def get_msgraph_email_id(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    filter: str = "",
    folder_name: str = "",
    fetch_all: bool = False,
) -> str:
    """Get email identifier for email present in mail box of particular user.
    If provided filter will be used.
    If folder_name is mentioned, search will happen inside that particular folder.
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): user email address in which email has to be searched
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        filter (str, optional): filter string to be applied for searching email. Defaults to ""
        folder_name (str, optional): Folder name in which mail will be searched. Default to ""
        fetch_all (boolean, optional): returns all the items if this parameter sets True. Default to False.
    Returns:
        email_identifier(str) if email is found in mailbox of user.
    """
    folder_id = ""
    if not ms_outlook_manager:
        outlook_manager = ms_context.ms_one_outlook_manager
    else:
        outlook_manager = ms_outlook_manager
    if folder_name:
        folder_id = verify_and_get_mail_folder_id(
            ms_context,
            user_email_id,
            folder_name,
            outlook_manager,
        )
    if folder_id:
        email_id = outlook_manager.get_identifier_of_filtered_email(
            receiver_email=user_email_id, filter=filter, folder_id=folder_id, fetch_all=fetch_all
        )
    else:
        email_id = outlook_manager.get_identifier_of_filtered_email(
            receiver_email=user_email_id, filter=filter, fetch_all=fetch_all
        )
    return email_id


def get_current_timestamp():
    """Get current timestamp

    Returns:
        Formatted date as YYYY-MM-DD-HH-MM-SS
    """
    # Get the current date
    current_date = datetime.now()

    # Format the date as "YYYY-MM-DD-HH-MM-SS"
    formatted_date = current_date.strftime("%Y-%m-%d-%H-%M-%S")
    logger.info(f"TimeStamp: {formatted_date}")
    return formatted_date


def create_and_validate_ms365_user_account(
    ms_context: MSOfficeContext,
    account_enabled: bool = True,
    display_name: str = "Test Automation",
    mail_nickname: str = "Sanity",
    user_principal_name: str = "sanity.testautomation@ms365br.onmicrosoft.com",
    force_change_password_next_sign_in: bool = False,
    ms_outlook_manager: MSOutlookManager = "",
) -> User:
    """Create and validates the MS365 user account

    Args:
        ms_context (MSOfficeContext): MS365 context object
        account_enabled (bool, optional): Flag to enable the MS365 account
        display_name (str, optional): MS365 user display name. Defaults to "Test Automation".
        mail_nickname (str, optional): MS365 user nick name. Defaults to "Sanity".
        user_principal_name (str, optional): MS365 user principal name. Defaults to "sanity.testautomation@ms365br.onmicrosoft.com".
        force_change_password_next_sign_in (str, optional): Flag to change the password for next sign in. Defaults to "False".
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""

    Returns:
        User: Success: MS365 user account information
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info("Creating MS365 user account")
    logger.info("Verify MS365 user account, if exists delete it and create")
    user_id = get_ms365_user_id(ms_context, ms_outlook_manager, display_name=display_name)
    if user_id is not None:
        logger.info("MS365 user account exists, lets delete it")
        delete_ms365_user_account(
            ms_context,
            ms_outlook_manager,
            display_name,
            user_id=user_id,
        )
    result = asyncio.get_event_loop().run_until_complete(
        ms_outlook_manager.create_ms365_user_account(
            password=ms_context.ms365_user_password,
            account_enabled=account_enabled,
            display_name=display_name,
            mail_nickname=mail_nickname,
            user_principal_name=user_principal_name,
            force_change_password_next_sign_in=force_change_password_next_sign_in,
        )
    )
    assert result, "Failed to Create the MS365 user account"
    logger.info("Successfully created the MS365 user account")
    logger.debug(f"user account info: {result}")
    return result


def get_ms365_users_account(
    ms_context: MSOfficeContext,
    ms_outlook_manager: MSOutlookManager = "",
) -> List[User]:
    """Get the list of MS365 user/s information

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".

    Returns:
        List[User]: Success: MS365 user account information
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info("Getting MS365 user accounts information")
    users_list = asyncio.get_event_loop().run_until_complete(ms_outlook_manager.fetch_ms365_users_account())
    assert users_list, "Failed to get the MS365 user accounts information"
    logger.info("Successfully got MS365 user accounts information")
    logger.debug(f"user accounts info: {users_list}")
    return users_list


def get_ms365_user_id(
    ms_context: MSOfficeContext,
    ms_outlook_manager: MSOutlookManager = "",
    display_name: str = "Test Automation",
) -> Union[str, None]:
    """Get MS365 user account id, which matches with the display name

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".
        display_name (str, optional): MS365 user display name. Defaults to "Test Automation".

    Returns:
        Union[str, None]: Success: MS365 user account id, Failure: None
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    user_id = None
    users_list = get_ms365_users_account(
        ms_context,
        ms_outlook_manager,
    )
    for user in users_list:
        if user.display_name == display_name:
            user_id = user.id
            logger.info(f"MS365 user id with display name:{display_name} is {user_id}")
            break
    return user_id


def delete_ms365_user_account(
    ms_context: MSOfficeContext,
    ms_outlook_manager: MSOutlookManager = "",
    display_name: str = "Test Automation",
    user_id: str = None,
):
    """Delete the MS365 user account from the org account

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".
        display_name (str, optional): MS365 user display name. Defaults to "Test Automation".
        user_id (str, optional): MS365 account user ID to get the information. Defaults to "None"
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    if user_id is None:
        user_id = get_ms365_user_id(ms_context, ms_outlook_manager, display_name=display_name)
    assert user_id, f"Unable to find the user account with display name: {display_name}"
    logger.info(f"Delete MS365 user account with ID:{user_id}")
    result = asyncio.get_event_loop().run_until_complete(ms_outlook_manager.delete_ms365_user_account(user_id))
    assert result, "Failed to delete the MS365 user account"
    logger.info(f"Successfully deleted MS365 user account with ID:{user_id}")


def get_ms365_org_users_count(ms_context: MSOfficeContext, ms_outlook_manager: MSOutlookManager = "") -> int:
    """Get MS365 organization users count

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".

    Returns:
        int: MS365 org users count
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info("Get the user count of MS365 organization")
    users_list = get_ms365_users_account(
        ms_context,
        ms_outlook_manager,
    )
    users_count = len(users_list)
    assert users_count, f"Failed to get the user count of MS365 organization account"
    logger.info(f"Successfully got the user count of MS365 organization account, count: {users_count}")
    return users_count


def create_outlook_contacts_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    display_name: str = "automation_contacts",
) -> str:
    """Creates and validates outlook contacts folder

    Args:
        ms_context (MSOfficeContext): ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): MS365 outlook account user id
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".
        display_name (str, optional): Name of the folder to be created. Defaults to "automation_contacts".

    Returns:
        contacts_folder_id (str): contacts folder id
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify MS365 outlook contacts folder with name: {display_name}")
    response = ms_outlook_manager.get_contacts_folders(user_email_id)
    assert response.status_code == requests.codes.ok, f"Failed to get contact folders info, response:{response.text}"
    existing_folders = response.json().get("value", [])
    contacts_folder_id = None
    for folder in existing_folders:
        if folder.get("displayName") == display_name:
            contacts_folder_id = folder.get("id")
            logger.info(f"Contacts folder: {display_name} already exists and ID: {contacts_folder_id}")
            break
    if not contacts_folder_id:
        logger.info(f"MS365 outlook contacts folder with name: {display_name} does not exist, lets create...")
        response = ms_outlook_manager.create_contacts_folder(
            user_email_id,
            display_name=display_name,
        )
        assert (
            response.status_code == requests.codes.created
        ), f"Failed to create outlook contacts folder, response: {response.text}"
        contacts_folder_info = response.json()
        contacts_folder_id = contacts_folder_info.get("id")
        logger.info(
            f"Successfully created outlook contacts folder with name: {display_name} and response: {contacts_folder_info}"
        )
    return contacts_folder_id


def create_multiple_contacts_in_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    given_name: str = "automation",
    surname: str = "MS365",
    email_addresses: list = [{"address": "ms365automation@framework.com", "name": "MS365_automation"}],
    business_phones: list = ["+1 732 555 0102"],
    display_name: str = "automation_contacts",
    total_no_of_contacts: int = 100,
    return_response: bool = False,
) -> Union[list, None]:
    """Creates and validates outlook contacts in a specified folder

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        given_name (str, optional): name of the contact. Defaults to "automation".
        surname (str, optional): surname of the contact. Defaults to "MS365".
        email_addresses (list): list of email address of the contact.
            Defaults to [{"address": "ms365automation@framework.com", "name": "MS365_automation"}].
        business_phones (list): list of phone nos. Defaults to ["+1 732 555 0102"]
        display_name (str, optional): Name of the folder to be created. Defaults to "automation_contacts".
        total_no_of_contacts (int, optional): total no of contacts to be created. Defaults to 100.
        return_response (boolean, optional): returns identifiers as response if this parameter set to True. Default to False.

    Returns:
        contacts_list (list): list of contacts identifiers if return_response set to True.
    """
    contacts_list = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    failed_contacts = 0
    # Get the contacts folder id
    contacts_folder_id = create_outlook_contacts_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager,
        display_name,
    )

    # Create multiple contacts in a specified folder
    for i in range(total_no_of_contacts):
        # Construct contact details
        modified_given_name = "{}{}".format(given_name, i + 1)
        modified_surname = "{}{}".format(surname, i + 1)
        for email_address in email_addresses:
            address = email_address["address"]
            email_address["address"] = "{}{}".format(i + 1, address)
            name = email_address["name"]
            email_address["name"] = "{}{}".format(name, i + 1)
        contact_details = ms_outlook_manager.construct_contact_details(
            given_name=modified_given_name,
            surname=modified_surname,
            email_addresses=email_addresses,
            business_phones=business_phones,
        )

        # Create contact
        contact_response = ms_outlook_manager.create_contact(
            user_email_id,
            contact_details=contact_details,
            contacts_folder_id=contacts_folder_id,
        )
        if contact_response.status_code != requests.codes.created:
            logger.warn(
                f"Failed to create an outlook contact for the user: {user_email_id} and task response: {contact_response.json()}"
            )
            failed_contacts += 1
            time.sleep(5)
        logger.info(
            f"Successfully created an outlook contact for the user: {user_email_id} and task list response: {contact_response.json()}"
        )
        if return_response:
            contact_response = contact_response.json()
            contacts_list.append(contact_response.get("id", ""))
    created_contacts = total_no_of_contacts - failed_contacts
    logger.warn(f"out of '{total_no_of_contacts}' contacts, {created_contacts} contacts have been created successfully")
    if return_response:
        return contacts_list, contacts_folder_id


def create_outlook_calendar_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    display_name: str = "automation_calendar",
) -> str:
    """Creates and validates outlook calendar folder

    Args:
        ms_context (MSOfficeContext): ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): MS365 outlook account user id
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "". Defaults to "".
        display_name (str, optional): Name of the folder to be created. Defaults to "automation_calendar".

    Returns:
        calendar_folder_id (str): calendar folder id
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify MS365 outlook calendar folder with name: {display_name}")
    response = ms_outlook_manager.get_calendar_folders(user_email_id)
    assert response.status_code == requests.codes.ok, f"Failed to get calendar folders info, response:{response.text}"
    existing_folders = response.json().get("value", [])
    calendar_folder_id = None
    for folder in existing_folders:
        if folder.get("name") == display_name:
            calendar_folder_id = folder.get("id")
            logger.info(f"calendar folder: {display_name} already exists and ID: {calendar_folder_id}")
            break
    if not calendar_folder_id:
        logger.info(f"MS365 outlook calendar folder with name: {display_name} does not exist, lets create...")
        response = ms_outlook_manager.create_calendar_folder(
            user_email_id,
            display_name=display_name,
        )
        assert (
            response.status_code == requests.codes.created
        ), f"Failed to create outlook calendar folder, response: {response.text}"
        calendar_folder_info = response.json()
        calendar_folder_id = calendar_folder_info.get("id")
        logger.info(
            f"Successfully created outlook calendar folder with name: {display_name} and response: {calendar_folder_info}"
        )
    return calendar_folder_id


def create_multiple_calendar_events_in_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    event_name: str = "Create MS365 Framework",
    display_name: str = "automation_calendar",
    total_no_of_events: int = 100,
    return_response: bool = False,
) -> Union[list, None]:
    """Create and validates multiple calendar events created in a outlook calendar folder

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        event_name (str, optional): Name of the event. Defaults to "Create MS365 Framework".
        display_name (str, optional): Outlook calendar folder name. Defaults to automation_calendar.
        total_no_of_events (int, optional): total no of events to be created. Defaults to 100.
        return_response (boolean, optional): returns identifiers as response if this parameter set to True. Default to False.

    Returns:
        calender_event_list (list): list of calender event identifiers if return_response set to True.
    """
    calender_event_list = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    failed_events = 0
    # Get calendar folder id
    calendar_folder_id = create_outlook_calendar_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager,
        display_name,
    )

    # Create multiple calendar events in a specified folder
    for i in range(total_no_of_events):
        start_time = datetime.utcnow() + timedelta(days=i)
        end_time = start_time + timedelta(hours=2)  # Events last for 2 hours
        modified_event_name = "{}{}".format(event_name, i + 1)
        start = {"dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), "timeZone": "UTC"}
        end = {"dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), "timeZone": "UTC"}

        # Construct event details
        event_details = ms_outlook_manager.construct_event_details(event_name=modified_event_name, start=start, end=end)

        # Create Event
        event_response = ms_outlook_manager.create_event(
            user_email_id, event_details, calendar_folder_id=calendar_folder_id
        )
        if event_response.status_code != requests.codes.created:
            logger.warn(
                f"Failed to create an outlook event for the user: {user_email_id}, Event response: {event_response.json()}"
            )
            failed_events += 1
            time.sleep(5)
        logger.info(
            f"Successfully created outlook event for the user: {user_email_id} Event response: {event_response.json()}"
        )
        if return_response:
            res = event_response.json()
            calender_event_list.append(res.get("id", ""))
    created_events = total_no_of_events - failed_events
    logger.warn(f"out of '{total_no_of_events}' events, {created_events} events have been created successfully")
    if return_response:
        return calender_event_list, calendar_folder_id


def create_multiple_tasks_in_to_do_list(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    title: str = "automation_task",
    linked_resources: list = [],
    display_name: str = "automation_tasks_list",
    total_no_of_tasks: int = 100,
    return_response: bool = False,
) -> Union[list, None]:
    """Create to do task in a task list

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        title (str, optional): Name of the task. Defaults to "automation_task".
        linked_resources (list, optional): List of dict describing linked resource.
            ex. {application_name="Microsoft", display_name="Microsoft", web_url="http://microsoft.com"}
        display_name (str, optional): To do task list name
        total_no_of_tasks (int, optional): total no of tasks to be created. Defaults to 100.
        return_response (boolean, optional): returns identifiers as response if this parameter set to True. Default to False.

    Returns:
        tasks_list (list): list of tasks identifiers if return_response set to True.
    """
    tasks_list = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    failed_tasks = 0
    # Get the task list id
    task_list_id = create_task_list_and_get_id(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        display_name=display_name,
    )
    # Create multiple tasks in a specified task list
    for i in range(total_no_of_tasks):
        modified_title = "{}{}".format(title, i + 1)
        # Construct task details
        task_details = ms_outlook_manager.construct_task_details(
            title=modified_title,
            linked_resources=linked_resources,
        )

        # Create to do task
        task_response = ms_outlook_manager.create_to_do_task(
            user_id=user_email_id, task_list_id=task_list_id, task_details=task_details
        )
        if task_response.status_code != requests.codes.created:
            logger.warn(
                f"Failed to create an outlook task for the user: {user_email_id} and task response: {task_response.json()}"
            )
            failed_tasks += 1
            time.sleep(5)
        logger.info(
            f"Successfully created an outlook to do task for the user: {user_email_id} and task response: {task_response.json()}"
        )
        if return_response:
            task_response = task_response.json()
            tasks_list.append(task_response.get("id", ""))
    created_tasks = total_no_of_tasks - failed_tasks
    logger.warn(f"out of '{total_no_of_tasks}' tasks, {created_tasks} tasks have been created successfully")
    if return_response:
        return tasks_list, task_list_id


def setup_outlook_account_with_test_data(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    email_folder_name: str = "automation_folder",
    subject: str = "Move messages",
    content: str = "Hello, let's move messages to a specific folder",
    inbox_rule_name: str = "move_messages",
    total_no_of_emails: int = 100,
    given_name: str = "automation",
    surname: str = "MS365",
    email_addresses: list = [{"address": "ms365automation@framework.com", "name": "MS365_automation"}],
    business_phones: list = ["+1 732 555 0102"],
    contacts_display_name: str = "automation_contacts",
    total_no_of_contacts: int = 100,
    event_name: str = "Create MS365 Framework",
    calendar_display_name: str = "automation_calendar",
    total_no_of_events: int = 100,
    title: str = "automation_task",
    linked_resources: list = [],
    task_list_display_name: str = "automation_tasks_list",
    total_no_of_tasks: int = 100,
    **kwargs,
):
    """setup MS365 outlook account with the test data, which includes contacts, calendar events and tasks

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        email_folder_name (str, optional): MS365 outlook email folder name. Defaults to "automation_folder"
        subject (str, optional): email subject. defaults to "Move messages"
        content (str, optional): email content. Defaults to "Hello, let's move messages to a specific folder"
        inbox_rule_name (str, optional): inbox rule name. Defaults to "move messages"
        total_no_of_emails (int. optional): total no of mail to send. Defaults to "100"
        given_name (str, optional): name of the contact. Defaults to "automation".
        surname (str, optional): surname of the contact. Defaults to "MS365".
        email_addresses (list): list of email address of the contact.
            Defaults to [{"address": "ms365automation@framework.com", "name": "MS365_automation"}].
        business_phones (list): list of phone nos. Defaults to ["+1 732 555 0102"]
        contacts_display_name (str, optional): Name of the folder to be created. Defaults to "automation_contacts".
        total_no_of_contacts (int, optional): total no of contacts to be created. Defaults to 100.
        event_name: str = "Create MS365 Framework",
        calendar_display_name: str = "automation_calendar",
        total_no_of_events: int = 100,
        title (str, optional): Name of the task. Defaults to "automation_task".
        linked_resources (list, optional): List of dict describing linked resource.
            ex. {application_name="Microsoft", display_name="Microsoft", web_url="http://microsoft.com"}
        task_list_display_name (str, optional): To do task list name
        total_no_of_tasks (int, optional): total no of tasks to be created. Defaults to 100.
        kwargs: key, value pair(s) of additional arguments for sending an email
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    # Send emails
    send_multiple_emails_to_specific_folder(
        ms_context,
        user_email_id,
        user_email_id,
        folder_name=email_folder_name,
        ms_outlook_manager=ms_outlook_manager,
        subject=subject,
        content=content,
        inbox_rule_name=inbox_rule_name,
        total_no_of_emails=total_no_of_emails,
        **kwargs,
    )
    # create contacts
    create_multiple_contacts_in_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        given_name=given_name,
        surname=surname,
        email_addresses=email_addresses,
        business_phones=business_phones,
        display_name=contacts_display_name,
        total_no_of_contacts=total_no_of_contacts,
    )

    # create calendar events
    create_multiple_calendar_events_in_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        event_name=event_name,
        display_name=calendar_display_name,
        total_no_of_events=total_no_of_events,
    )

    # create to do tasks
    create_multiple_tasks_in_to_do_list(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        title=title,
        linked_resources=linked_resources,
        display_name=task_list_display_name,
        total_no_of_tasks=total_no_of_tasks,
    )


def delete_messages_from_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    mail_folder_name,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Delete all the email messages from the specified folder
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        mail_folder_name (str): MS365 outlook email folder name
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Delete all the messages from the folder:{mail_folder_name}")
    logger.info(f"Get the messages from the folder:{mail_folder_name}")
    response = ms_outlook_manager.get_email_messages_from_folder(user_email_id, mail_folder_name)
    assert response.status_code == requests.codes.ok, f"Failed to get the messages from the folder:{mail_folder_name}"
    messages = response.json().get("value", [])
    total_messages = len(messages)
    if total_messages == 0:
        logger.info(f"There are no messages available in the folder: {mail_folder_name}")
        return
    logger.debug(f"List of messages from the folder: {mail_folder_name}\nMessages: {messages}")
    logger.info(f"Successfully got the messages from the folder: {mail_folder_name}")

    # Iterate through each message and delete it
    failed_to_delete = 0
    for message in messages:
        message_id = message["id"]
        logger.debug(f"Deleting the message with id: {message_id}")
        response = ms_outlook_manager.delete_email_message_from_folder(
            user_email_id,
            message_id,
            mail_folder_name,
        )
        if response.status_code != requests.codes.no_content:
            logger.warn(
                f"Failed to delete the message with id: {message_id} from the folder: {mail_folder_name}\nResponse: {response.json()}"
            )
            failed_to_delete += 1
        else:
            logger.info(f"Successfully deleted the message with id: {message_id}")
    logger.info(
        f"Out of {total_messages} messages {total_messages - failed_to_delete} has been deleted successfully from the folder:{mail_folder_name}"
    )
    assert True


def cleanup_outlook_inbox(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Clean up MS365 outlook inbox
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    logger.info(f"Cleaning up MS365 outlook inbox and its folders")
    default_folders = ["Junk Email", "Inbox", "Outbox", "Drafts", "Sent Items", "Conversation History", "Archive"]
    logger.info(f"Get all the mail folders from the outlook")
    response = ms_outlook_manager.get_mail_folders(user_email_id)
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    mail_folders = response.json().get("value", [])
    logger.debug(f"Existing mail folders from the outlook: {mail_folders}")
    logger.info(f"Successfully got MS365 mail folders, lets delete it")
    for mail_folder in mail_folders:
        mail_folder_name = mail_folder["displayName"]
        if mail_folder_name == "Deleted Items":
            continue
        if mail_folder_name in default_folders:
            folder_name_without_spaces = mail_folder_name.replace(" ", "")
            delete_messages_from_folder(ms_context, user_email_id, folder_name_without_spaces, ms_outlook_manager)
        else:
            response = ms_outlook_manager.delete_mail_folder(user_email_id, mail_folder["id"])
            assert (
                response.status_code == requests.codes.no_content
            ), f"Failed to delete the folder: {mail_folder_name}\nResponse: {response.json()}"
            logger.info(f"Successfully deleted the folder: {mail_folder_name}")
    logger.info(f"Successfully cleaned up MS365 outlook inbox and email folders")
    assert True


def get_folders_with_prefix(
    ms_context: MSOfficeContext, user_email_id: str, folder_name: str, ms_outlook_manager: MSOutlookManager = ""
):
    """This step method gets all the folders lists using the filter starts with the given folder name.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        folder_name (str): Folder name which will be used in the filter to fetch the list
        ms_outlook_manager (MSOutlookManager, optional):microsoft user context.. Defaults to "".

    Returns:
        dict: returns dictionary of { folder_name: folder_id } pairs matching given foldername prefix.
    """
    folders_dict = {}
    folder_id = None
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify folder: {folder_name} existed or not")
    response = ms_outlook_manager.get_mail_folders(
        user_email_id, filter=f"startswith(displayName,'{folder_name}')&$top=1000"
    )
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    existing_folders = response.json().get("value", [])
    for folder in existing_folders:
        folder_id = folder.get("id")
        folder_name = folder.get("displayName")
        folders_dict[folder_name] = folder_id
    logger.info(f"all folders dict details {folders_dict}")
    return folders_dict


def get_folder_with_prefix_for_specific_item_type(
    ms_context: MSOfficeContext,
    user_email_id: str,
    folder_name: str,
    item_type: str,
    ms_outlook_manager: MSOutlookManager = "",
) -> dict:
    """This step method gets all the folders lists using the filter starts with the given folder name.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        folder_name (str): Folder name which will be used in the filter to fetch the list
        item_type (str): User can provide outlook items such as Contacts, Calendars, Tasks.
        ms_outlook_manager (MSOutlookManager, optional):microsoft user context.. Defaults to "".

    Returns:
        dict: returns dictionary of {restored_folder_name: folder_id} pairs matching given foldername prefix.
    """
    folders_dict = {}
    folder_id = None
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    logger.info(f"Verify folder: {folder_name} existed or not in {item_type}...")
    if item_type == "contacts":
        response = ms_outlook_manager.get_contacts_folders(
            user_email_id, filter=f"startswith(displayName,'{folder_name}')"
        )
        assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
        existing_folders = response.json().get("value", [])

    elif item_type == "calendars":
        response = ms_outlook_manager.get_calendar_folders(user_email_id, filter=f"startswith(name,'{folder_name}')")
        assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
        existing_folders = response.json().get("value", [])

    elif item_type == "tasks":
        response = ms_outlook_manager.get_list_of_user_task_lists(
            user_email_id, filter=f"startswith(displayName,'{folder_name}')"
        )
        assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
        existing_folders = response.json().get("value", [])
    else:
        logger.warning("item_type is not provided. please provide for fetching information")
    for folder in existing_folders:
        folder_id = folder.get("id")
        folders_dict[folder_name] = folder_id
    logger.info(f"all folders dict details {folders_dict}")
    return folders_dict


def get_child_folder_id_for_specific_item_type(
    ms_context: MSOfficeContext,
    user_email_id: str,
    parent_folder_id: str,
    item_type: str,
    ms_outlook_manager: MSOutlookManager = "",
    child_folder_name: str = "",
) -> str:
    """This step method gets all the child folders information using the filter equals to given folder name.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        parent_folder_id (str): Parent Folder Identifier from where child folder deta7ils need to fetch
        item_type (str): User can provide outlook items such as contacts, calendars, tasks.
            for now only contacts need this method hence it supports contacts in futuer we can add other items too.
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context.. Defaults to "".
        child_folder_name (str, optional): Child folder name which use want to fetch. Defaults to "".

    Returns:
        str: returns child folder identifier
    """
    child_folder_id = None
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    if item_type == "contacts":
        response = ms_outlook_manager.get_contacts_child_folder(
            user_email_id, parent_folder_id=parent_folder_id, filter=f"displayName eq '{child_folder_name}'"
        )
        assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
        child_folder = response.json().get("value")
        child_folder_id = child_folder[0].get("id")
    else:
        logger.warning("item_type is not provided please provide item type to fetch details")
    return child_folder_id


def get_contacts_identifiers_in_restored_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    folder_id: str,
    filter: str,
    ms_outlook_manager: MSOutlookManager = "",
) -> list:
    """This step method fetches all the contacts identifiers from the given contactsFolder identifier.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        folder_id (str): contactsFolder identifier from where contacts need to fetch
        filter (str): filer to fetch the contacts information
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context.. Defaults to "".

    Returns:
        list: list of restored contacts identfiers
    """
    contacts_ids = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    response = ms_outlook_manager.get_contacts_from_contacts_folder(
        user_email_id=user_email_id, folder_id=folder_id, filter=filter
    )
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    all_contacts = response.json().get("value", [])
    for contact in all_contacts:
        contact_id = contact.get("id")
        contacts_ids.append(contact_id)
    return contacts_ids


def get_calendar_identifiers_in_restored_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    calendar_id: str,
    filter: str = "",
    ms_outlook_manager: MSOutlookManager = "",
) -> list:
    """This step method fetch list of events identifiers from provided calender identifier.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        calendar_id (str): calendar identifier from where events need to fetch
        filter (str, optional): filer to fetch the calendar events information.Defaults to "".
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context.. Defaults to ""

    Returns:
        list: list of events identfiers
    """
    events_ids = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    response = ms_outlook_manager.get_calendar_events(
        user_email_id=user_email_id, calendar_id=calendar_id, filter=filter
    )
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    all_contacts = response.json().get("value", [])
    for event in all_contacts:
        event_id = event.get("id")
        events_ids.append(event_id)
    return events_ids


def get_tasks_identifiers_in_restored_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    todo_list_id: str,
    filter: str = "",
    ms_outlook_manager: MSOutlookManager = "",
) -> list:
    """This step method fetch list of tasks identifiers from the provide folder id

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        user_email_id (str): user email address in which email has to be searched
        todo_list_id (str): todo list identifier from where tasks need to fetch
        filter (str, optional): filer to fetch the tasks information.Defaults to "".
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context.. Defaults to ""

    Returns:
        list: list of tasks identifiers
    """
    events_ids = []
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    response = ms_outlook_manager.get_tasks_in_todo_list(
        user_email_id=user_email_id, todo_list_id=todo_list_id, filter=filter
    )
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    all_contacts = response.json().get("value", [])
    for event in all_contacts:
        event_id = event.get("id")
        events_ids.append(event_id)
    return events_ids


def retrieve_new_folder_via_folder_comparison(folders_before_restore: dict, folders_after_restore: dict):
    """This method compares dictionaries folders_before_restore and folders_after_restore and
    returns (folder_name, folder_id) which is present in folders_after_restore and not in folders_before_restore.

    Args:
        folders_before_restore (dict): folders dict before performing restore operation
        folders_after_restore (dict): folders dict after performing restore operation

    Returns:
        str, str: returns new folder name and folder ID
    """
    new_folder_name = [
        folder_name for folder_name in folders_after_restore if folder_name not in folders_before_restore
    ]
    assert len(new_folder_name) == 1, "There are no new folders created after restore..."
    return new_folder_name[0], folders_after_restore[new_folder_name[0]]


def get_child_folder_details(
    ms_context: MSOfficeContext,
    user_email_id: str,
    parent_folder_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    child_folder_name: str = "",
):
    """This step method to get the child folder details under a parent folder

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): user email address in which email has to be searched
        parent_folder_id (str): Folder ID in which child folder will be searched.
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context.. Defaults to "".
        child_folder_name (str, optional): If provided, particular child folder ID returns if not all child folders will be returned. Defaults to "".

    Returns:
        str/dict: If the exact child_folder_name is provided, the method will return the corresponding child folder ID.
        Otherwise, it will return all child folders details in dict.
    """
    child_folders_dict = {}
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    response = ms_outlook_manager.get_child_folders(user_email_id, parent_folder=parent_folder_id)
    assert response.status_code == requests.codes.ok, f"Failed to get email folder, response: {response.json()}"
    child_folders = response.json().get("value", [])
    for folder in child_folders:
        folder_id = folder.get("id")
        folder_name = folder.get("displayName")
        child_folders_dict[folder_name] = folder_id
    return child_folders_dict[child_folder_name] if child_folder_name else child_folders_dict


def validate_email_in_restored_child_folder(
    ms_context: MSOfficeContext,
    user_email_id: str,
    folder_id: str,
    filter: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """This step method validate an email is available on the given child folder with a filter applied and returns email identifier.

    Args:
        ms_context (MSOfficeContext): MS365 context object.
        user_email_id (str): user email address in which email has to be searched.
        folder_id (str): Folder ID from where email has to validate.
        filter (str): Provide exact filter with which email can be fetched.
        ms_outlook_manager (MSOutlookManager, optional): microsoft user context. Defaults to "".

    Returns:
        str: returns email identifier
    """
    if not ms_outlook_manager:
        outlook_manager = ms_context.ms_one_outlook_manager
    else:
        outlook_manager = ms_outlook_manager
    message_id = outlook_manager.get_identifier_of_filtered_email(
        receiver_email=user_email_id,
        filter=filter,
        folder_id=folder_id,
    )
    assert message_id, f"Failed to get message with filter: {filter} in folder with ID: {folder_id}"
    logger.info("Successfully validated that we are able to fetch email from restored folder...")
    return message_id


def delete_outlook_contacts(
    ms_context: MSOfficeContext,
    user_email_id: str,
    contacts_list: list = [],
    contacts_folder_ids: list = [],
    ms_outlook_manager: MSOutlookManager = "",
):
    """Delete MS365 outlook contacts and its folders
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        contacts_list (list, optional): list of contacts to be deleted. Defaults to []
        contacts_folder_ids (list, optional): list of contacts folder ids. Defaults to "".
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    contacts_failed_to_delete = 0
    total_contacts = len(contacts_list)
    if total_contacts:
        for contact in contacts_list:
            logger.info(f"Deleting contact with ID: {contact}")
            response = ms_outlook_manager.delete_contact(user_email_id, contact)
            if response.status_code != requests.codes.no_content:
                logger.warn(f"Failed to delete the contact with ID: {contact}\nResponse: {response.json()}")
                contacts_failed_to_delete += 1
                continue
            logger.info(f"Successfully deleted the contact with ID: {contact}")
        logger.info(
            f"Out of {total_contacts} contacts {total_contacts - contacts_failed_to_delete} contacts have been deleted Successfully."
        )
        assert True
    elif contacts_folder_ids:
        for contacts_folder_id in contacts_folder_ids:
            logger.info(f"Deleting contacts folder with ID: {contacts_folder_id}")
            response = ms_outlook_manager.delete_contacts_folder(user_email_id, contacts_folder_id)
            assert (
                response.status_code == requests.codes.no_content
            ), f"Failed to delete the contact folder with ID: {contacts_folder_id}\nResponse: {response.json()}"
            logger.info(f"Successfully deleted the contact folder with ID: {contacts_folder_id}")
    else:
        logger.info("There are no contacts available to delete")
        assert True


def cleanup_outlook_contacts(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Clean up MS365 outlook contacts
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    logger.info(f"Cleaning up MS365 outlook contacts and its folders")
    logger.info(f"Get all the contact folders from the outlook")
    response = ms_outlook_manager.get_contacts_folders(user_email_id)
    assert response.status_code == requests.codes.ok, f"Failed to get contact folder, response: {response.json()}"
    contact_folders = response.json().get("value", [])
    logger.debug(f"Existing contact folders from the outlook: {contact_folders}")
    logger.info(f"Successfully got MS365 contact folders, lets delete it")
    contacts_folder_ids = []
    for contact_folder in contact_folders:
        contact_folder_id = contact_folder["id"]
        contacts_folder_ids.append(contact_folder_id)
    delete_outlook_contacts(
        ms_context,
        user_email_id,
        contacts_folder_ids=contacts_folder_ids,
        ms_outlook_manager=ms_outlook_manager,
    )
    logger.info(f"Get all the contacts from the outlook")
    response = ms_outlook_manager.list_contacts(user_email_id)
    assert (
        response.status_code == requests.codes.ok
    ), f"Failed to get contacts from the outlook, response: {response.json()}"
    contact_list = response.json().get("value", [])
    logger.debug(f"Existing contacts from the outlook: {contact_list}")
    logger.info(f"Successfully got MS365 contacts list, lets delete it")
    contact_ids = []
    for contact in contact_list:
        contact_id = contact["id"]
        contact_ids.append(contact_id)
    delete_outlook_contacts(
        ms_context,
        user_email_id,
        contacts_list=contact_ids,
        ms_outlook_manager=ms_outlook_manager,
    )


def cleanup_outlook_tasks(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Clean up MS365 outlook tasks
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    logger.info(f"Cleaning up MS365 outlook tasks")
    logger.info(f"Get all the tasks from the outlook")
    response = ms_outlook_manager.get_list_of_user_task_lists(user_email_id)
    assert (
        response.status_code == requests.codes.ok
    ), f"Failed to get task lists for the user: {user_email_id}, response: {response.json()}"
    task_lists = response.json().get("value", [])
    logger.debug(f"Existing task lists from the outlook: {task_lists}")
    logger.info(f"Successfully got MS365 task lists, lets delete it")
    task_list_ids = []
    tasks_failed_to_delete = 0
    for task_list in task_lists:
        task_list_id = task_list["id"]
        task_list_ids.append(task_list_id)
    total_task_lists = len(task_list_ids)
    if total_task_lists:
        for task_id in task_list_ids:
            response = ms_outlook_manager.delete_task_list(user_email_id, task_id)
            if response.status_code != requests.codes.no_content:
                logger.warn(f"Failed to delete the task list with ID: {task_id}\nResponse: {response.json()}")
                tasks_failed_to_delete += 1
                continue
            logger.info(f"Successfully deleted the task list with ID: {task_id}")
        logger.info(
            f"Out of {total_task_lists} task lists {total_task_lists - tasks_failed_to_delete} task lists have been deleted Successfully."
        )
    else:
        logger.info("There are no task lists to delete")


def delete_outlook_events(
    ms_context: MSOfficeContext,
    user_email_id: str,
    events_list: list = [],
    calendar_folder_ids: list = [],
    ms_outlook_manager: MSOutlookManager = "",
):
    """Delete MS365 outlook events and its folders
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        events_list (list, optional): list of events to be deleted. Defaults to []
        calendar_folder_ids (list, optional): list of events folder ids. Defaults to "".
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    events_failed_to_delete = 0
    total_events = len(events_list)
    if total_events:
        for event in events_list:
            logger.info(f"Deleting event with ID: {event}")
            response = ms_outlook_manager.delete_event(user_email_id, event)
            if response.status_code != requests.codes.no_content:
                logger.warn(f"Failed to delete the event with ID: {event}\nResponse: {response.json()}")
                events_failed_to_delete += 1
                continue
            logger.info(f"Successfully deleted the event with ID: {event}")
        logger.info(
            f"Out of {total_events} events {total_events - events_failed_to_delete} events have been deleted Successfully."
        )
    elif calendar_folder_ids:
        for calendar_folder_id in calendar_folder_ids:
            logger.info(f"Deleting calendar folder with ID: {calendar_folder_id}")
            response = ms_outlook_manager.delete_calendar_folder(user_email_id, calendar_folder_id)
            assert (
                response.status_code == requests.codes.no_content
            ), f"Failed to delete the calendar folder with ID: {calendar_folder_id}\nResponse: {response.json()}"
            logger.info(f"Successfully deleted the calendar folder with ID: {calendar_folder_id}")
    else:
        logger.info("There are no calendar events to delete")


def cleanup_outlook_events(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Clean up MS365 outlook events
    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    logger.info(f"Cleaning up MS365 outlook events and its folders")
    logger.info(f"Get all the event folders from the outlook")
    default_folders = ["Birthdays", "United States holidays", "Calendar"]
    response = ms_outlook_manager.get_calendar_folders(user_email_id)
    assert response.status_code == requests.codes.ok, f"Failed to get calendar folder, response: {response.json()}"
    calendar_folders = response.json().get("value", [])
    logger.debug(f"Existing calendar folders from the outlook: {calendar_folders}")
    logger.info(f"Successfully got MS365 calendar folders, lets delete it")
    calendar_folders_ids = []
    for calendar_folder in calendar_folders:
        if calendar_folder["name"] in default_folders:
            continue
        calendar_folder_id = calendar_folder["id"]
        calendar_folders_ids.append(calendar_folder_id)
    delete_outlook_events(
        ms_context,
        user_email_id,
        calendar_folder_ids=calendar_folders_ids,
        ms_outlook_manager=ms_outlook_manager,
    )
    logger.info(f"Get all the events from the outlook")
    response = ms_outlook_manager.list_events(user_email_id)
    assert (
        response.status_code == requests.codes.ok
    ), f"Failed to get events from the outlook, response: {response.json()}"
    events_list = response.json().get("value", [])
    logger.debug(f"Existing events from the outlook: {events_list}")
    logger.info(f"Successfully got MS365 events list, lets delete it")
    event_ids = []
    for event in events_list:
        event_id = event["id"]
        event_ids.append(event_id)
    delete_outlook_events(
        ms_context,
        user_email_id,
        events_list=event_ids,
        ms_outlook_manager=ms_outlook_manager,
    )


def cleanup_outlook_account(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
):
    """Clean up MS365 outlook account
    Args:
        c (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    # Clean up outlook inbox
    cleanup_outlook_inbox(ms_context, user_email_id, ms_outlook_manager)

    # Clean up outlook contacts
    cleanup_outlook_contacts(ms_context, user_email_id, ms_outlook_manager)

    # Clean up outlook tasks
    cleanup_outlook_tasks(ms_context, user_email_id, ms_outlook_manager)

    # Clean up outlook calendar events
    cleanup_outlook_events(ms_context, user_email_id, ms_outlook_manager)


def cleanup_checksum_tool_workers(ms_context: MSOfficeContext = "", ms_outlook_manager: MSOutlookManager = ""):
    """This method will cleanup checksum tool workers, created as part of MSOutlookManager().
    If we don't kill checksum workers then pytest will not finish the run and will be in running state forever.
    In context, we are creating 2 MSOutlookManager() objects so we need to kill workers in those two objects.
    If user has an object for MSOutlookManager() created outside of context then he should ensure to kill workers in that object as well.
    Args:
        ms_context (MSOfficeContext, optional): MS365 Context object, If provided, will cleanup workers created as part of context object. Defaults to "".
        ms_outlook_manager (MSOutlookManager, optional): If provided, will cleanup workers created as part of that particular MSOutlookManager() . Defaults to "".
    """
    if ms_context:
        ms_context.ms_one_outlook_manager.kill_checksum_tool_workers()
        ms_context.ms_two_outlook_manager.kill_checksum_tool_workers()
    if ms_outlook_manager:
        ms_outlook_manager.kill_checksum_tool_workers()
    logger.info("Successfully killed checksum tool workers")


def generate_multiple_items_and_get_their_identifiers(
    ms_context: MSOfficeContext,
    user_email_id: str,
    ms_outlook_manager: MSOutlookManager = "",
    email_folder_name: str = "automation_folder",
    subject: str = "Move messages",
    content: str = "Hello, let's move messages to a specific folder",
    inbox_rule_name: str = "move_messages",
    total_no_of_emails: int = 100,
    given_name: str = "automation",
    surname: str = "MS365",
    email_addresses: list = [{"address": "ms365automation@framework.com", "name": "MS365_automation"}],
    business_phones: list = ["+1 732 555 0102"],
    contacts_display_name: str = "automation_contacts",
    total_no_of_contacts: int = 100,
    event_name: str = "Create MS365 Framework",
    calendar_display_name: str = "automation_calendar",
    total_no_of_events: int = 100,
    title: str = "automation_task",
    linked_resources: list = [],
    task_list_display_name: str = "automation_tasks_list",
    total_no_of_tasks: int = 100,
    **kwargs,
):
    """setup MS365 outlook account with the test data, which includes contacts, calendar events and tasks

    Args:
        ms_context (MSOfficeContext): MS365 context object
        user_email_id (str): email id of the user
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""
        email_folder_name (str, optional): MS365 outlook email folder name. Defaults to "automation_folder"
        subject (str, optional): email subject. defaults to "Move messages"
        content (str, optional): email content. Defaults to "Hello, let's move messages to a specific folder"
        inbox_rule_name (str, optional): inbox rule name. Defaults to "move messages"
        total_no_of_emails (int. optional): total no of mail to send. Defaults to "100"
        given_name (str, optional): name of the contact. Defaults to "automation".
        surname (str, optional): surname of the contact. Defaults to "MS365".
        email_addresses (list): list of email address of the contact.
            Defaults to [{"address": "ms365automation@framework.com", "name": "MS365_automation"}].
        business_phones (list): list of phone nos. Defaults to ["+1 732 555 0102"]
        contacts_display_name (str, optional): Name of the folder to be created. Defaults to "automation_contacts".
        total_no_of_contacts (int, optional): total no of contacts to be created. Defaults to 100.
        event_name: str = "Create MS365 Framework",
        calendar_display_name: str = "automation_calendar",
        total_no_of_events: int = 100,
        title (str, optional): Name of the task. Defaults to "automation_task".
        linked_resources (list, optional): List of dict describing linked resource.
            ex. {application_name="Microsoft", display_name="Microsoft", web_url="http://microsoft.com"}
        task_list_display_name (str, optional): To do task list name
        total_no_of_tasks (int, optional): total no of tasks to be created. Defaults to 100.
        kwargs: key, value pair(s) of additional arguments for sending an email
    Returns:
        dict: returns a items created in a dictionary.
    """
    identifier_dict = {}
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager

    send_multiple_emails_to_specific_folder(
        ms_context,
        user_email_id,
        user_email_id,
        folder_name=email_folder_name,
        ms_outlook_manager=ms_outlook_manager,
        subject=subject,
        content=content,
        inbox_rule_name=inbox_rule_name,
        total_no_of_emails=total_no_of_emails,
        **kwargs,
    )
    # waiting for mails to replacate on the email folder
    time.sleep(10)
    email_identifiers = get_msgraph_email_id(
        ms_context=ms_context,
        user_email_id=user_email_id,
        filter=ms_context.filter,
        folder_name=email_folder_name,
        fetch_all=True,
    )
    identifier_dict["mail_identifiers"] = email_identifiers

    # create contacts
    contacts_ids, contacts_folder_id = create_multiple_contacts_in_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        given_name=given_name,
        surname=surname,
        email_addresses=email_addresses,
        business_phones=business_phones,
        display_name=contacts_display_name,
        total_no_of_contacts=total_no_of_contacts,
        return_response=True,
    )
    identifier_dict["contacts_folder_id"] = contacts_folder_id
    identifier_dict["contacts_identifiers"] = contacts_ids

    # create calendar events
    events_ids, calender_folder_id = create_multiple_calendar_events_in_folder(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        event_name=event_name,
        display_name=calendar_display_name,
        total_no_of_events=total_no_of_events,
        return_response=True,
    )
    identifier_dict["calender_folder_id"] = calender_folder_id
    identifier_dict["events_identifiers"] = events_ids

    # create to do tasks
    tasks_ids, tasks_list_id = create_multiple_tasks_in_to_do_list(
        ms_context,
        user_email_id,
        ms_outlook_manager=ms_outlook_manager,
        title=title,
        linked_resources=linked_resources,
        display_name=task_list_display_name,
        total_no_of_tasks=total_no_of_tasks,
        return_response=True,
    )
    identifier_dict["tasks_list_id"] = tasks_list_id
    identifier_dict["tasks_identifiers"] = tasks_ids
    logger.info(f"Created identifiers information: {identifier_dict}")
    return identifier_dict
