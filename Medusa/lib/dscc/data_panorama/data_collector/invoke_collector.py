import os
from threading import Thread
import logging

# from concurrent.futures import ThreadPoolExecutor
import lib.dscc.data_panorama.data_collector.hauler.dt1_collector as dt1
import lib.dscc.data_panorama.data_collector.hauler.dt2_collector as dt2
import lib.dscc.data_panorama.data_collector.db_writer.dataporter as db_writer
import lib.dscc.data_panorama.data_collector.db_writer.cost_calculation as costdata

logging.basicConfig(
    filename="py_svc3.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"
)
logger = logging.getLogger()


def dt1_getArrayData(mock_dir):
    dt1.dt1_collect_array_data(mock_dir)


def dt2_getArrayData(mock_dir):
    dt2.dt2_collect_array_data(mock_dir)


if __name__ == "__main__":
    file_dir = os.path.dirname(__file__)
    mock_dir = f"{file_dir}/out"
    if not os.path.exists(mock_dir):
        os.makedirs(mock_dir)

    threads = []
    dt1_thread = Thread(target=dt1_getArrayData, args=(mock_dir,))
    threads.append(dt1_thread)

    dt2_thread = Thread(target=dt2_getArrayData, args=(mock_dir,))
    threads.append(dt2_thread)

    [t.start() for t in threads]
    ## wait for the threads to finish
    [t.join() for t in threads]

    dt1_getArrayData(mock_dir=mock_dir)
    dt2_getArrayData(mock_dir=mock_dir)

    db_path = f"{mock_dir}/aggregateddb.sqlite"
    db_writer.create_tables_from_collection(mock_dir=mock_dir, db_file=db_path)
    costdata.getCISCostCalculationdata()
