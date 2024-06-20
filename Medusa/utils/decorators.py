from functools import wraps
import time


# def try_except(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         try:
#             value = func(*args, **kwargs)
#         except AssertionError as ae:
#             print(f"Assertion Error: {ae}")
#             raise
#         except requests.exceptions.Timeout as e:
#             print(f"Timeout: {e}")
#             raise
#         except requests.exceptions.RequestException as e:
#             print(f"Requests Exception: {e}")
#             raise SystemExit(e)
#         except Exception as e:
#             print(f"Exception: {e}")
#             raise
#         return value
#     return wrapper


def timeit(func):
    @wraps(func)
    def wrapper_timer(*args, **kwargs):
        start = time.perf_counter()
        value = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_time = end - start
        print(f"Time taken for Test Execution: {elapsed_time:0.4f} seconds")
        return value

    return wrapper_timer
