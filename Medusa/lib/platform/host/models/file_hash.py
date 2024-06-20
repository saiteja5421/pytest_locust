from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config
import json
import logging

logger = logging.getLogger()


# NOTE: This class is added to convert the response from 'Get-FileHash' Powershell command to read checksum
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class FileHash:
    algorithm: str = field(metadata=config(field_name="Algorithm"))
    hash: str = field(metadata=config(field_name="Hash"))
    path: str = field(metadata=config(field_name="Path"))


@dataclass
class FileHashList:
    file_hashes: list[FileHash]

    def parse_sha256_unix(self, output: list[str]):
        # This function is called from: "gfrs_aws_steps.get_checksum_ec2()", and gets its
        # stdout from: "output = io_manager.client.execute_command()", where "output" is a "list[str]"
        assert isinstance(output, list), "provided input is not a list[]"
        parsed_list = [hash.split("  ") for hash in output if hash]
        self.file_hashes = [
            FileHash(algorithm="SHA256", hash=filehash[0], path=filehash[1]) for filehash in parsed_list
        ]

    def parse_sha256_unix_subprocess(self, output: str):
        # This function is called from: "gfrs_aws_steps.get_checksum_local()", and gets its
        # stdout from: "output = subprocess.run()", where "output" is a "CompletedProcess" object
        # The "output.stdout" is provided to this function as a "str"

        # stdout Format from subprocess.run():
        # "HASH  FILENAME\nHASH  FILENAME\n...""

        # break up hash/filename lines
        lines = output.split("\n")
        self.parse_sha256_unix(lines)

    def parse_sha256_windows(self, response):
        # this function is currently is use, called from "ssm_manager":
        # "response = self.ssm_client.send_command()"
        # The "response["StandardOutputContent"]" is provided to this function
        result = response.replace("\n", "")
        parsed_list = json.loads(result)
        # if there is only 1 entry, then the 'parsed_list' will not be a 'list'
        if not isinstance(parsed_list, list):
            parsed_list = [parsed_list]

        # now build an actual list[FileHash] from the 'json_loads' data
        self.file_hashes = [
            FileHash(algorithm="SHA256", hash=filehash["Hash"], path=filehash["Path"]) for filehash in parsed_list
        ]
