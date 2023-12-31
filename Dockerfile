FROM python:3-slim
COPY requirements.txt /requirements.txt
COPY entrypoint.py /entrypoint.py
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/entrypoint.py"]
