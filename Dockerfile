FROM cicirello/pyaction:4
WORKDIR /tmp/action
COPY . .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/tmp/action/entrypoint.py"]
