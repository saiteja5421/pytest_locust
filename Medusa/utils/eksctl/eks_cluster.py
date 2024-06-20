import logging

import subprocess
import threading

logger = logging.getLogger()


def run_eks_cluster_command(command: str, capture_output: bool = True, text: bool = True, timeout: int = 300):
    """Runs provided command and returns the CompletedProcess onbject

    Args:
        command (str): eks cluster command to run
        capture_output (bool, optional): Output of the child process . Defaults to True.
        text (bool, optional): Return the output in the form of string, if set to True. Defaults to True.
        timeout (int, optional): Wait time to run the child process. Defaults to 1800.

    Returns:
        CompletedProcess object, with args, returncode, stdout and stderror if succeeded. Otherwise returns False
    """
    try:
        result = subprocess.run(command, capture_output=capture_output, text=text, timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.error(f"Failed to run the command: {command} with in {timeout} seconds")
        return False
    except subprocess.CalledProcessError:
        logger.error(f"Failed to run the command: {command} exited with non zero status")
        return False
    return result


def run_eks_command_without_waiting(command: str):
    def run_subprocess_non_blocking(command: str):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print("Subprocess started successfully!")
                print("STDOUT:", stdout.decode().strip())
            else:
                print("Subprocess failed to start.")
                print("STDERR:", stderr.decode().strip())
        except Exception as e:
            print("An error occurred:", str(e))

    subprocess_thread = threading.Thread(target=run_subprocess_non_blocking, args=(command,))
    subprocess_thread.start()
