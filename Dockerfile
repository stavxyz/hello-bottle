FROM alpine

# install pip and hello-world server requirements
RUN mkdir -p /var/hellobottle
WORKDIR /var/hellobottle
RUN apk --update add python3 python3-dev libevent-dev libffi-dev build-base
ADD hello.py /home/bottle/server.py
COPY requirements.txt /
RUN pip3 install -U pip
RUN pip3 install -U -r /requirements.txt
COPY . /var/hellobottle
# Install the hellobottle app
RUN ["pip3", "install", "/var/hellobottle"]

# in case you'd prefer to use links, expose the port
EXPOSE 8080
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["/usr/bin/python3", \
            "/var/hellobottle/hello.py", \
            "--debug", "--verbose", \
            "--mongo-host", "mongo"]
