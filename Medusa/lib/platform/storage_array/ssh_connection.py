import sys
import paramiko
import socket
import logging
import time
from stat import S_ISDIR
import os

logger = logging.getLogger()


class SshConnection(object):
    """
    A class to represent a SshConnection.

    Usage:
    ------
        client = SshConnection()
        obj.exec_cmd()


    Methods:
    --------
        exec_cmd()
            :- Used to execute commands on remote host

    Return:
    -------
        :- return SshConnection object
    """

    def __init__(self, hostname: str, username: str, password: str, sftp=False) -> object:
        """
        __init__: Constructs all the necessary attributes for the SshConnection object.
        ---------

        Parameters:
        -----------
            hostname* :- Remote host name/IP
                type:- str
            username :- Remote host username
                type:- str
            password :- Remote host password
                type:- str

        Global Variables:
        -----------------
            self.port :- contains port jumber, default using port 22 for ssh connection
            self.hostname :- storing user passed hostname
            self.username :- storing user passed user name
            self.password :- storing user passed password
            self.client :- Contain remotoe hsot ssh object

        """
        UseGSSAPI = paramiko.GSS_AUTH_AVAILABLE
        DoGSSAPIKeyExchange = paramiko.GSS_AUTH_AVAILABLE
        self.port = 22
        self.hostname = hostname
        self.username = username
        self.password = password
        self.sftp = ""
        self.sock = ""
        self.t = ""
        """
        - Try to connect to user provided host
        - connection successfull self.client will get initialize 
        - connection fails raise an exception

        """
        if sftp:
            self.sftp_init(hostname = self.hostname,username=self.username,key_file=None,password=self.password)
        else:
            try:
                self.client = paramiko.SSHClient()

                self.client.load_system_host_keys()
                self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
                if not UseGSSAPI and not DoGSSAPIKeyExchange:

                    logger.info(f"Connecting to {hostname} remote host...")
                    self.client.connect(self.hostname, self.port, self.username, self.password)
                    logger.info(f"Remote connection successful for {hostname}")
                else:
                    try:
                        logger.info(f"Connecting to {hostname} remote host...")
                        self.client.connect(
                            self.hostname,
                            self.port,
                            self.username,
                            gss_auth=UseGSSAPI,
                            gss_kex=DoGSSAPIKeyExchange,
                        )
                        logger.info(f"Remote connection successful for {hostname}")
                    except Exception:
                        raise Exception(f"Error: {format(sys.exc_info()[0])}")
            except Exception as e:
                self.client.close()
                raise Exception(f"Error: {format(sys.exc_info()[0])}")


    def sftp_init(self,hostname,username='root',key_file=None,password=None):
        #
        #  Accepts a file-like object (anything with a readlines() function)  
        #  in either dss_key or rsa_key with a private key.  Since I don't 
        #  ever intend to leave a server open to a password auth.
        #
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((hostname,22))
        self.t = paramiko.Transport(self.sock)
        self.t.start_client()
        keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        key = self.t.get_remote_server_key()
        # supposed to check for key in keys, but I don't much care right now to find the right notation
        if key_file is not None:
            if isinstance(key_file,str):
                key_file=open(key_file,'r')
            key_head=key_file.readline()
            key_file.seek(0)
            if 'DSA' in key_head:
                keytype=paramiko.DSSKey
            elif 'RSA' in key_head:
                keytype=paramiko.RSAKey
            else:
                raise Exception("Can't identify key type")
            pkey=keytype.from_private_key(key_file)
            self.t.auth_publickey(username, pkey)
        else:
            if password is not None:
                self.t.auth_password(username,password,fallback=False)
            else: raise Exception('Must supply either key_file or password')
        self.sftp=paramiko.SFTPClient.from_transport(self.t)


    def exec_cmd(self, cmd: str, retry=False, err_exception: bool = False):
        """
        exec_cmd: Method will execute user passed command, it is successfull return stdout else raise a exception with error code
                    - if user pass retry than will perform retry operation untill command successful
        ---------

        Parameters:
            cmd* :- command to execute on remote host
                type:- str
                default value:-  -> means, mandatory parameter
            retry :- if command execution fails, will retry
                type:- bool
                default value:- False -> menas, will not retry if command execution fails

        Return:
        -------
            Command Success:
                - std_out
            Command Fails:
                - if retry specified:
                    std_err
                - else:
                    excepion with std_err
        """
        std_in, std_out, std_err = self.client.exec_command(cmd)

        std_ouput = std_out.read().decode().strip()
        error = std_err.read().decode().strip()
        # Failed to create volume snapshot. Unknown error
        if retry and "ERROR" in error:
            while 1:
                print("User specified retry as True, command failed retrying...")
                print(f"retrying command: {cmd} ...")
                logger.info(f"User specified retry as True, command failed retrying...")
                logger.info(f"retrying command: {cmd} ...")
                self.client.close()
                self.client.connect(self.hostname, self.port, self.username, self.password)
                std_in, std_out, std_err = self.client.exec_command(cmd)
                error = std_err.read().decode().strip()
                if "ERROR" not in error:
                    return std_out.read().decode().strip()

        if "ERROR:" in error or "Error" in error:
            logger.debug(f"Failed to execute command {cmd}")
            logger.debug(f"{error}")
            # return error
            if err_exception:
                return error
            self.client.close()
            raise Exception(f"Failed to execute command {cmd}, Error: {error}")
        else:
            return std_ouput

    def close_connection(self) -> None:
        """
        close_connection: Method will use to close ssh connection
        ---------

        Parameters:
            Not required

        Return:
        -------
            None
        """
        logger.info(f"Closing remote connection...")
        self.client.close()
        logger.info(f"Remote connection closed successfully...")

    def put(self,localfile,remotefile):
        #  Copy localfile to remotefile, overwriting or creating as needed.
        self.sftp.put(localfile,remotefile)

    def put_all(self,localpath,remotepath):
        os.chdir(os.path.split(localpath)[0])
        parent=os.path.split(localpath)[1]
        for path,_,files in os.walk(parent):
            try:
                self.sftp.mkdir(self.remotepath_join(remotepath,path))
            except:
                pass
            for filename in files:
                self.put(os.path.join(path,filename),self.remotepath_join(remotepath,path,filename))

    def remotepath_join(self,*args):
        #  Bug fix for Windows clients, we always use / for remote paths
        return '/'.join(args)

    def get(self,remotefile,localfile):
        #  Copy remotefile to localfile, overwriting or creating as needed.
        self.sftp.get(remotefile,localfile)
        
    def sftp_walk(self,remotepath):
        # Kindof a stripped down  version of os.walk, implemented for 
        # sftp.  Tried running it flat without the yields, but it really
        # chokes on big directories.
        path=remotepath
        files=[]
        folders=[]
        for f in self.sftp.listdir_attr(remotepath):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)
        yield path,folders,files
        for folder in folders:
            new_path=self.remotepath_join(remotepath,folder)
            for x in self.sftp_walk(new_path):
                yield x

    def get_all(self,remotepath,localpath):
        #  recursively download a full directory
        #  Harder than it sounded at first, since paramiko won't walk
        #
        # For the record, something like this would gennerally be faster:
        # ssh user@host 'tar -cz /source/folder' | tar -xz
        self.sftp.chdir(os.path.split(remotepath)[0])
        parent=os.path.split(remotepath)[1]
        try:
            os.mkdir(localpath)
        except FileExistsError:
            pass
        for path,_,files in self.sftp_walk(parent):
            try:
                os.mkdir(self.remotepath_join(localpath,path))
            except FileExistsError:
                pass
            for filename in files:
                #print(self.remotepath_join(path,filename),os.path.join(localpath,path,filename))
                self.get(self.remotepath_join(path,filename),os.path.join(localpath,path,filename))

    def sftp_close(self):
        self.sftp.close()
        self.t.close()
        self.sock.close()
    