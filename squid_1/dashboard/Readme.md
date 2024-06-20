# Locust dashboard

It uses postgres timescaledb and grafana as dashboard tool

Execute docker-compose file which will set up postgres and grafana. Postgres will have tables required to store test result. This postgres db will be add as datasource to Grafana.
Grafana dashboard will have locust dashboard which can be imported.Once imported this will
use locust_timescale as datasource and display visual results.

```

First create docker volumes

docker volume create grafana_data
docker volume create postgres_data
Note: Volume has to be created only once.

1) To run locust grafana dashboard

docker-compose -f locust-grafana-dockercompose.yml up

Note: This will bring up the locust and grafana

2) if you want to specify the project name yourself instead of taking folder name as default

COMPOSE_PROJECT_NAME=qa_automation docker-compose -f locust-grafana-dockercompose.yml up -d

Note: First time connect to grafana dashboard using admin/admin then create new password


3) To down the grafana dashboard

docker-compose -f locust-grafana-dockercompose.yml down

Note: This will delete the container but not volume where data is stored.
So if we down and up historic data won't be affected

docker-compose -f locust-grafana-dockercompose.yml down -v

Note: Volume also will be down so all the data stored till now will be deleted. If we delete the volume all our history of runs will be gone. So if only truly require use this option.
```

# postgres sql file

The file query.postgres.psql will have query to display the results table.
We have added max,min,median,started_at and completed_at as extra fields.

# Historic data preserved in postgres volume 
Postgres volume will be added to container. So even if we made some changes historic data will remain in volume. If needed to remove the history totally then volume need to be removed.

```
docker-compose -f locust-grafana-dockercompose.yml down -v
```

