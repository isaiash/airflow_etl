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
SYSTEM_FOLDER = "MIS/"
SPECIFIC_DATA_FOLDER = DATA_FOLDER+SYSTEM_FOLDER
SPECIFIC_RAW_FOLDER = PROCESSED_FOLDER+SYSTEM_FOLDER
DAG_NAME = "mis"
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
    description='Extraccion de MIS',
    schedule_interval=None#timedelta(minutes=1), # tiempo del scheduler
)

#####################################################################
############################## UTILS ################################
#####################################################################

def read_csv(filepath):
    processed_data = defaultdict(list)
    #column_name = []
    with open(filepath, newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                column_names = row
            else:
                [processed_data[column_names[j]].append(k) for j,k in enumerate(row)]
    return processed_data

def read_xlsx(filepath, sheet_name):
    dfs = pd.read_excel(filepath, sheet_name=sheet_name)
    return dfs
    
def copy_raw(from_, to_):
    filename = os.path.basename(from_)
    shutil.copyfile(from_, to_+filename)

def save_csv(filepath, processed_data):
    filename = os.path.basename(filepath)
    attribute_names = processed_data.keys()
    rows = zip(*[i for i in processed_data.values()])
    
    with open(PROCESSED_FOLDER+filename , 'w') as f:                                         
        writer = csv.writer(f)
        writer.writerow(attribute_names)
        for row in rows:                                                                      
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
        copy_raw(filepath,RAW_FOLDER+SYSTEM_FOLDER)

    return 'save_raw_file'

def save_processed(ds, **kwargs):
    print("Saving processed...")
    ti = kwargs['task_instance']
    #filepaths = ti.xcom_pull(task_ids='sensor')
    filepaths = ["/home/isaias/cmpc_data/MIS/plywood.xlsx"]
    
    for filepath in filepaths:
        df_data = read_xlsx(filepath, "PRODUCCION")
        df_area = df_data[["ID_AREA", 
                            "ID_PROCESO", 
                            "ID_TURNO", 
                            "ID_MAQUINA", 
                            "ID_TARJETA", 
                            "ID_CLASE",
                            "ID_GRADO",
                            "ID_USO",
                            "ID_LIJADO",
                            "ID_CANTO",
                            "ID_TEXTURA",
                            "ID_PINTURA",
                            "ID_EMBALAJE",
                            "ID_APLICACION",
                            "ID_BAR",
                            "ID_EMPAQUE",
                            "ID_SECADO",
                            "ID_ROLLIZO",
                            "ID_RETAPE",
                            "FECHA_PRODUCCION",
                            "HORA_PRODUCCION",
                            "ESPESOR",
                            "ANCHO",
                            "LARGO",
                            "NUMERO_PIEZAS",
                            "ESPESOR_NOMINAL",
                            "ANCHO_NOMINAL",
                            "LARGO_NOMINAL",
                            "ID_MATERIAL",
                            "ID_HUMEDAD",
                            "FECHA_CREACION",
                            "ID_PLY",
                            "ID_FORMATO",
                            "ORDERID",
                            "ORDERROW",
                            ]].groupby("ID_AREA")
        df_db = df_area.get_group('DB')[[
                                        "ID_TARJETA",
                                        "ID_TURNO",
                                        "ID_GRADO",
                                        "ID_APLICACION",
                                        "ID_ROLLIZO",
                                        "HORA_PRODUCCION",
                                        "ESPESOR",
                                        "ANCHO",
                                        "LARGO",
                                        "NUMERO_PIEZAS",
                                        "ID_MATERIAL",
                                        "ID_HUMEDAD",
                                        "FECHA_CREACION",
                                        "ORDERID",
                                        ]]
        df_se = df_area.get_group('SE')[[
                                        "ID_TARJETA",
                                        "ID_TURNO",
                                        "ID_GRADO",
                                        "ID_APLICACION",
                                        "ID_ROLLIZO",
                                        "HORA_PRODUCCION",
                                        "ESPESOR",
                                        "ANCHO",
                                        "LARGO",
                                        "NUMERO_PIEZAS",
                                        "ID_MATERIAL",
                                        "ID_HUMEDAD",
                                        "FECHA_CREACION",
                                        "ORDERID",
                                        ]]
        df_pn = df_area.get_group('PN')[[
                                        "ID_TARJETA",
                                        "ID_TURNO",
                                        "ID_CLASE",
                                        "ID_GRADO",
                                        "ID_USO",
                                        "ID_CANTO",
                                        "ID_EMBALAJE",
                                        "ID_RETAPE",
                                        "ID_APLICACION",
                                        "HORA_PRODUCCION",
                                        "ESPESOR",
                                        "ANCHO",
                                        "LARGO",
                                        "NUMERO_PIEZAS",
                                        "ID_MATERIAL",
                                        "ID_PLY",
                                        "FECHA_CREACION",
                                        "ORDERID",
                                        "ORDERROW"
                                        ]]
        ### PROCESS HERE
        current_timestamp = str(int(datetime.now().timestamp()))
        df_db.to_csv(PROCESSED_FOLDER+"MIS_DEBOBINADO/MIS_DEBOBINADO_"+current_timestamp+'.csv', index=False)
        df_se.to_csv(PROCESSED_FOLDER+"MIS_SECADO/MIS_SECADO_"+current_timestamp+'.csv', index=False)
        df_pn.to_csv(PROCESSED_FOLDER+"MIS_PRENSA/MIS_PRENSA_"+current_timestamp+'.csv', index=False)

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


