from pymongo import MongoClient
# pretty print
from pprint import pprint

client = MongoClient(port=27017)
db=client.cmpc

row = {
    "FECHA":"20-Apr",
    "FUNDO": 531,
    "RODAL": 199406,
    "PRODUCTO": "Clear A",
    "LARGO_REAL": 5.3,
    "LARGO_NOMINAL": 5.23,
    "POSICION_FUSTAL": 1,
    "N_TROZO": 1,
    "SED": 28,
    "VELOCIDAD": 3.3
}

result=db.bosque.insert_one(row)
print('Created {0}, {1}'.format(x,result.inserted_id))
