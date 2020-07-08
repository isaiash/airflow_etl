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
SPECIFIC_DATA_FOLDER = DATA_FOLDER+"SAP/"
SYSTEM_FOLDER = "SAP/"
SPECIFIC_RAW_FOLDER = RAW_FOLDER+SYSTEM_FOLDER
SPECIFIC_PROCESSED_FOLDER = PROCESSED_FOLDER+SYSTEM_FOLDER
DAG_NAME = "sap"
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
    description='Extraccion de SAP',
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
    filepaths = ti.xcom_pull(task_ids='sensor')
    #filepaths = ["/home/isaias/airflow/repository/raw_data/SAP/BD para calculo reposo.xlsx"]

    for filepath in filepaths:
        df_data = read_xlsx(filepath, 'BD')
        ### PROCESS HERE
        df_pto_trabajo = df_data[["Pto. Trabajo", 
                                    "Material", 
                                    "Desc.Material", 
                                    "Orden Fab.", 
                                    "M3", 
                                    "Turno",
                                    "Hora de entrada",
                                    "Nro.Etiqueta",
                                    "Clase de movimiento",
                                    "Rem.Grado",
                                    "Espesor"]].groupby("Pto. Trabajo")
        df_class = df_pto_trabajo.get_group('ZPLY_S27').groupby("Clase de movimiento")
        df_secador_input = df_class.get_group(261)
        df_secador_output = df_class.get_group(101)
        df_prensado1 = df_pto_trabajo.get_group('ZPLY_PR1')
        df_prensado2 = df_pto_trabajo.get_group('ZPLY_PR2')
        df_prensado3 = df_pto_trabajo.get_group('ZPLY_PR3')
        df_prensado4 = df_pto_trabajo.get_group('ZPLY_PR4')

        current_timestamp = str(int(datetime.now().timestamp()))
        df_secador_input.to_csv(PROCESSED_FOLDER+"SAP_SECADO_INPUT/SAP_SECADO_INPUT_"+current_timestamp+'.csv', index=False)
        df_secador_output.to_csv(PROCESSED_FOLDER+"SAP_SECADO_OUTPUT/SAP_SECADO_OUTPUT_"+current_timestamp+'.csv', index=False)
        df_prensado1.to_csv(PROCESSED_FOLDER+"SAP_PRENSA/SAP_PRENSA1_"+current_timestamp+'.csv', index=False)
        df_prensado2.to_csv(PROCESSED_FOLDER+"SAP_PRENSA/SAP_PRENSA2_"+current_timestamp+'.csv', index=False)
        df_prensado3.to_csv(PROCESSED_FOLDER+"SAP_PRENSA/SAP_PRENSA3_"+current_timestamp+'.csv', index=False)
        df_prensado4.to_csv(PROCESSED_FOLDER+"SAP_PRENSA/SAP_PRENSA4_"+current_timestamp+'.csv', index=False)
    return 'save_processed'

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

