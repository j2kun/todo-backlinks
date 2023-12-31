FROM python:3-slim
WORKDIR /tmp/action
COPY . .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/entrypoint.py"]
