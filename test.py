import pytest
from main import make_request, get_nested_values, create_applicant_data
from requests import exceptions

TOKEN = "675b8574770b11611351d9d6ad0caa7053bb49c08b364f28d034a94075b97e5e"
ACCOUNT_ID = 30

def test_invalid_url():
    with pytest.raises(exceptions.HTTPError):
        make_request(
            url="testpath/1",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

def test_getting_nested_values():
    dictionary = {
        "fields": {
            "name": {
                "first": "Test",
                "last": "Testov",
                "middle": "Testovich"
            },
            "email": "test@example.com",
            "phones": [
                "+1234567890"
            ],
            "experience": [
                {
                    "position": "Python Backend",
                    "company": "Test Company"
                }
            ]
        },
    }

    assert get_nested_values(dictionary,["fields","name", "first"]) == "Test"
    assert get_nested_values(dictionary,["fields","name", "last"]) == "Testov"
    assert get_nested_values(dictionary,["fields","name", "middle"]) is not None
    assert get_nested_values(dictionary,["fields","email"]) == "test@example.com"
    assert get_nested_values(dictionary,["fields","phones"])[0] == "+123456789"
    assert get_nested_values(dictionary,["fields","experience"],[{}])[0].get("position") == "Python Backend"
    assert get_nested_values(dictionary,["fields","experience"],[{}])[0].get("company") == "Test Company"
    assert get_nested_values(dictionary,["fields","salary"]) is None
    
def test_create_vaild_applicant():
    resume = {
        "id": 1,
        "text": "test text \n additional info",
        "fields": {
            "name": {
                "first": "Тест",
                "last": "Тестов",
                "middle": "Тестович"
            },
            "birthdate": None,
            "phones": [
                "+799999999999"
            ],
            "email": "test@test.com",
            "salary": None,
            "position": None,
            "skype": "@test_skype",
            "telegram": "@test_tg",
            "experience": [
                {
                    "position": "Тестовая позиция (10 лет 10 месяцев)",
                    "company": "ООО 'Тест компания'"
                },
            ]
        }
    }
    applicant = create_applicant_data(resume, {"Ожидания по ЗП":"100000"})
    created_applicant = make_request(
        method="POST", 
        url=f"accounts/{ACCOUNT_ID}/applicants",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=applicant
    )
    assert created_applicant['code'] == 200