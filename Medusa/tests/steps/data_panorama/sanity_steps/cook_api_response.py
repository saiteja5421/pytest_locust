


from pathlib import Path
import pandas as pd
import sqlalchemy


class APITable:

    def __init__(self,db_path):
        self.db_path = db_path
        conn = self._connect_db()
        
        self.volume = pd.read_sql_table("volume_last_collection", con=conn)
        self.snapshot = pd.read_sql_table("snapshot_last_collection", con=conn)
        self.clone = pd.read_sql_table("clone_last_collection", con=conn)
        self.application = pd.read_sql_table("app_last_collection", con=conn)
        self.system = pd.read_sql_table("system_last_collection", con=conn)
        self.volperf = pd.read_sql_table("volperf_all_collection", con=conn)
        self.volusage = pd.read_sql_table("volusage_all_collection", con=conn)


    def _connect_db(self):
        db_path = Path(f"{self.db_path}").resolve()
        engine = sqlalchemy.create_engine("sqlite:///%s" % db_path, execution_options={"sqlite_raw_colnames": True})
        conn = engine.connect()
        return conn