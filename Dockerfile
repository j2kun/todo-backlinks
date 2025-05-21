FROM cicirello/pyaction:4.33.0

# GH automatically puts the context repo's source here
WORKDIR /github/workspace
RUN git config --system --add safe.directory *

# ensure our action's source code doesn't conflict
COPY entrypoint.py /entrypoint.py
COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

ENTRYPOINT ["python3"]
CMD ["/entrypoint.py"]
