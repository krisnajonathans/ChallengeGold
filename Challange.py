from flask import Flask, request, jsonify
from flasgger import Swagger, LazyString, LazyJSONEncoder, swag_from
import pandas as pd
import re
import time
from unidecode import unidecode
from database import checkTable_text, checkTable_file, createTable, _insertText, _insertFile

app = Flask(__name__)
app.json_encoder = LazyJSONEncoder

swagger_template = dict(
    info = {
        'title': LazyString(lambda: 'API TESTER'),
        'version': LazyString(lambda: '1'),
        'description': LazyString(lambda: 'API Tester for challenge')
    },
    host = LazyString(lambda: request.host)
)

swagger_config = {
    "headers":[],
    "specs": [
        {
            "endpoint":"docs",
            "route":"/docs.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True
        }
    ],
    "static_url_path":"/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}

swagger = Swagger(app, template=swagger_template,config=swagger_config)

kamus_normalisasi = pd.read_csv('new_kamusalay.csv', names = ['sebelum', 'sesudah'], encoding='ISO-8859-1')

def lowerCase(i):
    return i.lower()

def remove_url(i):
    i = re.sub(r"http\S+", "", i)
    i = re.sub(r"www.\S+", "", i)
    return i

def remove_punct(i):
    i = re.sub(r"[^\w\d\s]+", "", i) 
    return i

def remove_other_body(i):
    i = re.sub(r"rt", "", i) 
    i = re.sub(r"user", "", i) 
    i = re.sub(r"[^\x00-\x7f]", r"", i) 
    return i

def remove_other_file(i): 
    i = re.sub(r"rt", "", i)
    i = re.sub(r"user", "", i)
    return re.sub(r"\\x[A-Za-z0-9./]+", "", unidecode(i))

def remove_hashtag(i):
    # i = re.sub("@[A-Za-z0-9_]+","", i)
    # i = re.sub("#[A-Za-z0-9_]+","", i)
    i = re.sub(r'#([^\s]+)',' ',i)
    i = re.sub(r'@([^\s]+)',' ',i)
    return i

def remove_multipleSpace(i):
    i = re.sub(' +', ' ', i)
    # i = re.sub("\s\s+", " ", i)
    return i

def _normalization(i):
    words = i.split()
    clear_words = ""
    for val in words:
        x = 0
        for idx, data in enumerate(kamus_normalisasi['sebelum']):
            if(val == data):
                clear_words += kamus_normalisasi['sesudah'][idx] + ' '
                print("Transform :",data,"-",kamus_normalisasi['sesudah'][idx])
                x = 1
                break
        if(x == 0):
            clear_words += val + ' '
    return clear_words

def text_processing(s):
    text = s
    s = lowerCase(s)
    s = remove_url(s)
    s = remove_other_body(s)
    s = remove_hashtag(s)
    s = remove_punct(s)
    s = _normalization(s)
    s = remove_multipleSpace(s)
    _insertText(text, s)
    return s

def file_processing(df):
    df['lower'] = df['Tweet'].apply(lowerCase)
    df['link'] = df['lower'].apply(remove_url)
    df['binary'] = df['link'].apply(remove_other_file)
    df['hastag'] = df['binary'].apply(remove_hashtag)
    df['punct'] = df['hastag'].apply(remove_punct)
    df['normalization'] = df['punct'].apply(_normalization)
    df['space'] = df['normalization'].apply(remove_multipleSpace)
    df_clean = pd.DataFrame(df[['Tweet','space']])
    _insertFile(df_clean)

@swag_from("challenge_swagger_text.yml", methods=['POST'])
@app.route("/text_clean/v1", methods=['POST'])
def text_clean():
    check_table = checkTable_text()
    if check_table == 0:
        createTable()
    s = request.get_json()
    clean_text = text_processing(s['text'])
    return jsonify({"result":clean_text})

@swag_from("challenge_swagger_file.yml", methods=['POST'])
@app.route("/file_clean/v1", methods=['POST'])
def file_clean():
    check_table = checkTable_file()
    if check_table == 0:
        createTable()
    count_time = time.time()
    file = request.files['file']
    df = pd.read_csv(file, encoding='ISO-8859-1')
    file_processing(df)
    return jsonify({"result":"file telah berhasil terupload", "time_exc":"%s second" % (time.time() - count_time)})

if __name__ == '__main__':
    app.run(port=1234, debug=True)

