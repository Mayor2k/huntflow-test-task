import argparse
import json
import requests
import openpyxl
import os
from transliterate import translit
from re import sub
from datetime import datetime
import mimetypes
 
def make_request(url, method="GET", headers={}, **kwargs):        
    response = requests.request(
        method=method,
        url=f"https://dev-100-api.huntflow.dev/v2/{url}",
        headers=headers,
        **kwargs
    )
    response.raise_for_status()
    return {"code": response.status_code, "json":response.json()}

def find_resume(workdir, path, name):
    workdir = os.path.dirname(workdir)
    for root, dirs, files in os.walk(os.path.join(workdir, path)):
        for file in files:
            if name in file:
                return os.path.join(root, file)
    
def get_nested_values(dictionary, keys, default=None):
    value = dictionary
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key] 
        else:
            return default
    return value if value is not None else default

def create_applicant_data(resume, additional_data):
    applicant = {
        "first_name": get_nested_values(resume, ["fields", "name", "first"]),
        "last_name": get_nested_values(resume, ["fields", "name", "last"]),
        "middle_name": get_nested_values(resume, ["fields", "name", "middle"]),
        # берем данные из excel и приводим к единому виду, убирая ненужные символы
        "money": sub("[^\d\.]", "", str(additional_data.get('Ожидания по ЗП'))),
        # берем первый номер из списка, если список не пустой
        "phone": get_nested_values(resume, ["fields", "phones"], [""])[0],
        "email": get_nested_values(resume, ["fields", "email"]),
        "skype": get_nested_values(resume, ["fields", "skype"]),
        # берем последние данные о должности и месте работы, если таковые имеются
        "position": get_nested_values(resume, ["fields","experience"], [{}])[0].get("position", ""),
        "company": get_nested_values(resume, ["fields","experience"], [{}])[0].get("company", ""),
        "photo": get_nested_values(resume, ["photo", "id"]),
        "birthday": datetime(
            year=get_nested_values(resume, ["fields", "birthdate", "year"]),
            month=get_nested_values(resume, ["fields", "birthdate", "month"]),
            day=get_nested_values(resume, ["fields", "birthdate", "day"]),
        ).strftime("%Y-%m-%d") if get_nested_values(resume, ["fields", "birthdate"]) else None,
        "externals": [{
            "data": {
                "body": resume.get("text", "")
            }, 
            "auth_type": "NATIVE",
            "files": [resume.get("id")],
            "account_source": None
        }]
    }
    
    # проверяем, есть ли в резюме ник в tg, при наличии, прикрепляем social с данными
    if get_nested_values(resume, ["fields", "telegram"]) is not None:
        applicant["social"] = [{
            "social_type": "TELEGRAM",
            "value": get_nested_values(resume, ["fields", "telegram"])
        }]
    
    return applicant

def main():
    parser = argparse.ArgumentParser(description='Upload applicants to Huntflow')
    
    parser.add_argument(
        '-d',
        '--data_path', 
        type=str, 
        default='test_task/Тестовая база.xlsx',
        help='Path to XLSX file with applicants (default: test_task/Тестовая база.xlsx)'
    )

    parser.add_argument(
        '-t',
        '--token_path', 
        type=str,
        default='token.json',
        help='Path to JSON file with access token (default: token.json)'
    )

    args = parser.parse_args()
    
    #получение access_token из указанного файла
    if os.path.isfile(args.token_path):
        token_data = json.load(open(args.token_path))
        if token_data.get("access_token"):
            TOKEN = json.load(open(args.token_path))["access_token"]
        else:
            raise KeyError("There is no 'access_token' in provided file!")
    else:
        raise FileNotFoundError("Token file is not exist!")

    ACCOUNT_ID = make_request(
        url="accounts",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )['json']['items'][0]['id']
    # приводим VACANCIES и STATUSES к виду:{"имя статуса/вакансии":int(id)}
    VACANCIES = dict(map(
        lambda x: (x['position'], x['id']), 
        make_request(
            url=f"accounts/{ACCOUNT_ID}/vacancies",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )['json']['items']
    ))
    STATUSES = dict(map(
        lambda x: (x['name'], x['id']), 
        make_request(
            url=f"accounts/{ACCOUNT_ID}/vacancies/statuses",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )['json']['items']
    ))
    # временный файл, в который, при возникновения ошибок или ручной остановки 
    # скрипта, будет записываться номер последней обработанной строки, 
    TEMP_FILE = os.path.join(os.path.dirname(args.data_path), ".huntflow_import.tmp")

    applicants_list = openpyxl.load_workbook(args.data_path)
    sheet = applicants_list.active
    sheet_header = list(header.value for header in sheet[1])

    if os.path.isfile(TEMP_FILE):
        with open(TEMP_FILE) as f:
            min_row = int(f.readline())
            print(f"Обработка кандидатов начнется с {min_row} строки")
    else:
        min_row = 2

    for row_count, row in enumerate(sheet.iter_rows(min_row=min_row, min_col=1)):
        try:
            applicant = dict(zip(sheet_header, list(str(x.value).strip() for x in row))) 
            
            print(f"Начинаем обрабатывать кандидата {applicant['ФИО']} на должность {applicant['Должность']}")
            
            current_resume_path = find_resume(args.data_path,applicant['Должность'],applicant['ФИО'])
            if current_resume_path:
                # заливаем резюме на сервер, получаем спарсенные данные
                current_resume_file = make_request(
                    method="POST", 
                    url=f"accounts/{ACCOUNT_ID}/upload",
                    headers={"Authorization": f"Bearer {TOKEN}","X-File-Parse":"true"},
                    files={"file":(
                        translit(applicant['ФИО'], language_code='ru', reversed=True),
                        open(current_resume_path, 'rb'),
                        mimetypes.guess_type(current_resume_path)[0]
                        )}
                )['json']
                # подготавливаем данные кандидата
                current_applicant_data = create_applicant_data(current_resume_file, applicant)
                # создаем кандидата
                current_applicant = make_request(
                    method="POST", 
                    url=f"accounts/{ACCOUNT_ID}/applicants",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                    json=current_applicant_data
                )['json']
                
                if current_applicant.get("id"):
                    # прикрепляем кандидата к заданным данным
                    make_request(
                        method="POST", 
                        url=f"accounts/{ACCOUNT_ID}/applicants/{current_applicant.get('id')}/vacancy",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                        json={
                            "vacancy": VACANCIES[applicant['Должность']],
                            "status": STATUSES[applicant['Статус']],
                            "comment": applicant['Комментарий'],
                        }
                    )
                    
                    print(f"Кандидат {applicant['ФИО']} на прикреплен на должность {applicant['Должность']}!")
            else:
                print(f"Резюме кандидата {applicant['ФИО']} на должность {applicant['Должность']} не найдено")
                
        # при возникновении ошибки или ручного прерывания скрипта, 
        # во временный файл записывается номер текущей строки        
        except (Exception, KeyboardInterrupt) as e:
            with open(TEMP_FILE, "w") as f:
                f.write(str(row_count+2))
            raise e
        
    if os.path.isfile(TEMP_FILE):
        os.remove(TEMP_FILE)
        
if __name__ == "__main__":
    main()