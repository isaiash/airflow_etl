from datetime import timedelta
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.hooks.mongo_hook import MongoHook
from airflow.utils.dates import days_ago
from time import sleep
from collections import defaultdict
import shutil
import csv
import os
from pymongo import MongoClient
from datetime import datetime
from pathlib import Path

# General
HOME_PATH = "/home/isaias/"
RAW_FOLDER = HOME_PATH+"airflow/repository/raw_data/"
PROCESSED_FOLDER = HOME_PATH+"airflow/repository/processed_data/"
DATA_FOLDER = HOME_PATH+"cmpc_data/"
SYSTEMS = ["MIS", "SAP", "sh_macerado", "sh_prensa", "sh_preprensa", "recepcion"]

# Particular
INTEGRATED_FOLDER = HOME_PATH+"airflow/repository/integrated_data/"
#####################################################################
############################### DAG #################################
#####################################################################


# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 6,18,16),
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
    'integrator', #ID del dag
    default_args=default_args,
    description='Integrar archivos',
    schedule_interval='0 */8 * * *' # tiempo del scheduler
)

#####################################################################
############################## UTILS ################################
#####################################################################

def read_csv(filepath, include_names, separator):
    processed_data = []
    with open(filepath, newline='') as f:
        reader = csv.reader(f, delimiter=separator)
        for i, row in enumerate(reader):
            if i == 0:
                cn_names = row
                continue
            processed_data.append(row)
    return processed_data, cn_names
    
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

def MongodbConnection():
        client = MongoClient(port=27017)
        db=client.cmpc
        return db

def get_empty_document():
    pass

def get_processed_files():
    recepcion_data, cn_recepcion = read_csv(PROCESSED_FOLDER+"recepcion/Recepcion_634.csv", include_names=1, separator=',')
    mis_data, cn_mis = read_csv(PROCESSED_FOLDER+"MIS/plywood.csv", include_names=1, separator=',')
    sap_data, cn_sap = read_csv(PROCESSED_FOLDER+"SAP/BD para calculo reposo.csv", include_names=1, separator=',')
    macerado_data, cn_macerado = read_csv(PROCESSED_FOLDER+"sh_macerado/macerado-2020-06-08-18-21-41.csv", include_names=1, separator=',')
    prensa_data, cn_prensa = read_csv(PROCESSED_FOLDER+"sh_prensa/prensa-2020-06-08-18-21-39.csv", include_names=1, separator=',')
    preprensa_data, cn_preprensa = read_csv(PROCESSED_FOLDER+"sh_preprensa/preprensa-2020-06-08-18-21-37.csv", include_names=1, separator=',')

    return ([
        recepcion_data,
        mis_data,
        sap_data,
        macerado_data,
        prensa_data,
        preprensa_data
    ],
    [
        cn_recepcion,
        cn_mis,
        cn_sap,
        cn_macerado,
        cn_prensa,
        cn_preprensa
    ])

def integrate_files(processed_files, column_names):
    document = {}

    document = recepcion_document(document, column_names[0], processed_files[0])
    document = mis_document(document, column_names[1], processed_files[1])
    document = sap_document(document, column_names[2], processed_files[2])
    document = macerado_document(document, column_names[3], processed_files[3])
    document = prensa_document(document, column_names[4], processed_files[4])
    document = preprensa_document(document, column_names[5], processed_files[5])

def lote_exists(collection, id_name ,cod_barra):
    return 0 < collection.count_documents({ id_name: cod_barra }, limit = 1)
        
def fill_secado_output(db):
    # Search for pending files
    for path in Path(PROCESSED_FOLDER+"SAP_SECADO_OUTPUT/").rglob('SAP_SECADO_OUTPUT_*.csv'):
        print(path)
        data, column_names = read_csv(path, include_names=1, separator=',')

        for row in data:
            if not lote_exists(db.LOTE_SECO, 'COD_BARRA_LOTE_SECO', row[7]):
                doc = {
                    "COD_BARRA_LOTE_SECO":row[7],
                    "DATETIME_ENTRADA":row[6],
                    "TURNO": row[5],
                    "CALIDAD": row[9],
                    "ESPESOR": row[10],
                    "ORDEN_FABRICACION": row[3],
                    "MATERIAL": row[1]
                }
                db.LOTE_SECO.insert_one(doc)

        #for i,row in enumerate(data):
        #    if i== 0:
        #        print(row)
            # Check if already exists
            #...
            #else

def fill_debobinado(db):
    for path in Path(PROCESSED_FOLDER+"MIS_DEBOBINADO/").rglob('MIS_DEBOBINADO_*.csv'):
        print(path)
        data, column_names = read_csv(path, include_names=1, separator=',')

        for row in data:
            if not lote_exists(db.LOTE_VERDE, 'COD_BARRA_LOTE_VERDE', row[0]):
                doc = {
                    "COD_BARRA_LOTE_VERDE":row[0],
                    "DATETIME_PRODUCCION":row[5],
                    "DATETIME_CREACION":row[12],
                    "TURNO": row[1],
                    "GRADO": row[2],
                    "ROLLIZO": row[4],
                    "APLICACION": row[3],
                    "ESPESOR": row[6],
                    "ANCHO":row[7],
                    "LARGO":row[8],
                    "NUMERO_PIEZAS":row[9],
                    "ID_MATERIAL": row[10],
                    "ID_HUMEDAD": row[11],
                    "ORDEN_FABRICACION": row[13],
                }
                db.LOTE_VERDE.insert_one(doc)         


def integrate(ds, **kwargs):

    db = MongodbConnection()
    print(db)
    fill_secado_output(db)
    fill_debobinado(db)
    #documents = create_documents(processed_files, column_names)
    
    #Integrate
    #current_timestamp = str(int(datetime.now().timestamp()))
    #save_csv(data, INTEGRATED_FOLDER+"INTEGRATED_"+current_timestamp+".csv")
    return 1

integrator = PythonOperator(
    task_id='integrate_files',
    provide_context=True,
    python_callable=integrate,
    dag=dag,
)

integrator

