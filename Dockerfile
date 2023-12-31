FROM python:3-slim
COPY . .
RUN ls -la
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/entrypoint.py"]
