from datetime import timedelta
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.contrib.sensors.file_sensor import FileSensor
# from airflow.operators.sensors.file_sensor import FileSensor
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.utils.dates import days_ago
from time import sleep
from collections import defaultdict
import shutil
import csv
import os
import pandas as pd
from datetime import datetime

# General
HOME_PATH = "/home/isaias/"
RAW_FOLDER = HOME_PATH+"airflow/repository/raw_data/"
PROCESSED_FOLDER = HOME_PATH+"airflow/repository/processed_data/"
DATA_FOLDER = HOME_PATH+"cmpc_data/"


# Especifico
SPECIFIC_DATA_FOLDER = DATA_FOLDER+"CPPWIN/"
SYSTEM_FOLDER = "CANCHAS/"
SPECIFIC_RAW_FOLDER = RAW_FOLDER+SYSTEM_FOLDER
SPECIFIC_PROCESSED_FOLDER = PROCESSED_FOLDER+SYSTEM_FOLDER
DAG_NAME = "cppwin_v1"
#####################################################################
############################### DAG #################################
#####################################################################

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(2),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}

dag = DAG(
    DAG_NAME, #ID del dag
    default_args=default_args,
    description='Extraccion de Cppwin',
    schedule_interval=None#timedelta(minutes=1), # tiempo del scheduler
)

#####################################################################
############################## UTILS ################################
#####################################################################

def read_csv(filepath, include_names, separator):
    #processed_data = defaultdict(list)
    processed_data = []
    #column_name = []
    with open(filepath, newline='') as f:
        reader = csv.reader(f, delimiter=separator)
        for i, row in enumerate(reader):
            if i == 0 and include_names:
                continue
            processed_data.append(row)
    return processed_data

def read_slk(filepath, start_in, n_columns, separator):
    processed_data = []
    with open(filepath, newline='') as f:
        reader = csv.reader(f, delimiter=separator)
        current_row = ['']*n_columns
        i = 2
        prev_i = i
        for num, row in enumerate(reader):
            if num <= start_in:
                continue
            if row == ["E"] or row == ["E\n"]:
                break
            j = int(row[1][1:])-1
            i = int(row[2][1:])
            if prev_i != i:
                prev_i = i
                processed_data.append(current_row)
                current_row = ['']*n_columns
                current_row[j] = row[3][1:]
            else:
                current_row[j] = row[3][1:]
            
    return processed_data

def read_xlsx(filepath, sheet_name):
    dfs = pd.read_excel(filepath, sheet_name=sheet_name)
    return dfs
    
def copy_raw(from_, to_):
    filename = os.path.basename(from_)
    shutil.copyfile(from_, to_+filename)

def save_csv(data, filepath, column_names=[]):
    with open(filepath , 'w') as f:
        writer = csv.writer(f)
        if len(column_names):
            writer.writerow(column_names)
        for row in data:
            writer.writerow(row)

#####################################################################
############################## TASKS ################################
#####################################################################

def sensor(ds, **kwargs):
    print("Sensoring...")

    while(1):
        data_files = os.listdir(SPECIFIC_DATA_FOLDER)
        raw_files = os.listdir(SPECIFIC_RAW_FOLDER)
        diff = list(set(data_files) - set(raw_files))
        if len(diff) == 0:
            sleep(5)
        else:
            print([SPECIFIC_DATA_FOLDER + f for f in diff])
            return [SPECIFIC_DATA_FOLDER + f for f in diff]
    print("Sucedió algo inesperado")
    return 0

def save_raw(ds, **kwargs):
    print("Saving raw...")

    ti = kwargs['task_instance']
    filepaths = ti.xcom_pull(task_ids='sensor')

    for filepath in filepaths:
        copy_raw(filepath, SPECIFIC_RAW_FOLDER)

    return 'save_raw_file'

def save_processed(ds, **kwargs):
    print("Saving processed...")
    ti = kwargs['task_instance']
    #filepaths = ti.xcom_pull(task_ids='sensor')
    filepaths = ["/home/isaias/cmpc_data/CPPWIN/Mov_Parcelas.slk"]
    for filepath in filepaths:
        data = read_slk(filepath, start_in=21, n_columns=20, separator=';')
        
        column_names = [
            "ID_CENTRO_NEGOCIO",
            "ID_TIPO_PARCELA",
            "DESCRIPCION",
            "NUMERO_PROCESO",
            "ID_PARCELA",
            "TIPO_PARCELA",
            "ID_AGRUP_PRODUCTO",
            "DESCRIPCION",
            "ID_CONDICION",
            "ESTADO_CORTEZA",
            "LARGO",
            "ID_RANGO_DIAMETRO",
            "DIAM_MENOR",
            "DIAM_MAYOR",
            "VOLUMEN_TROZOS",
            "FECHA_INICIO",
            "TURNO_INICIO",
            "FECHA_TERMINO",
            "TURNO_TERMINO",
            "OBSERVACION"
        ]

        df = pd.DataFrame(data, columns=column_names).groupby("ID_TIPO_PARCELA")

        current_timestamp = str(int(datetime.now().timestamp()))
        df.get_group("101").to_csv(PROCESSED_FOLDER+"CANCHA1/CANCHA1_"+current_timestamp+'.csv', index=False)
        df.get_group("201").to_csv(PROCESSED_FOLDER+"CANCHA2/CANCHA2_"+current_timestamp+'.csv', index=False)

    return 'integrate_data'

sensor_loop = PythonOperator(
    task_id='sensor',
    provide_context=True,
    python_callable=sensor,
    dag=dag,
)

save_raw = PythonOperator(
    task_id='save_raw',
    provide_context=True,
    python_callable=save_raw,
    dag=dag,
)


save_processed = PythonOperator(
    task_id='save_processed',
    provide_context=True,
    python_callable=save_processed,
    dag=dag,
)

trigger = TriggerDagRunOperator(
    task_id='trigger_rerun',
    trigger_dag_id=DAG_NAME,
    dag=dag
)

sensor_loop >> save_raw 
sensor_loop >> save_processed 
[save_raw, save_processed] >> trigger

