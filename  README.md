# huntflow-test-task

```
usage: python3 main.py [-h] [-d DATA_PATH] [-t TOKEN_PATH]

Upload applicants to Huntflow
options:
  -h, --help            show this help message and exit
  -d DATA_PATH, --data_path DATA_PATH
                        Path to XLSX file with applicants (default: test_task/Тестовая база.xlsx)
  -t TOKEN_PATH, --token_path TOKEN_PATH
                        Path to JSON file with access token (default: token.json)
```

##### Для корректной обработки данных, требуется следущая структура файлов в директории, где находится тестовая база:

├── Должность 1
│   ├── резюме1.pdf
│   ├── резюме2.doc
│   ├── ...
├── Должность 2
│   ├── ...
├── Должность ...
└── Тестовая база.xlsx

##### Также, для работы скрипта требуется указать путь к json файлу, где содержится токен. Он должен иметь следующую структуру:
```json
{"access_token":"XXXXXXX", "refresh_token":"XXXXXXX"}
```