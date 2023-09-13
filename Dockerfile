FROM python:3.10

COPY . /almaviva
WORKDIR /almaviva
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENV admin_id='ваш телеграм ID'
ENV key='любой ключ для шифрования'
ENV salt='любая соль для шифрования'
ENV token='токен бота'

CMD [ "python", "main.py" ]