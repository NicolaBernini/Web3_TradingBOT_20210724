FROM python:latest

RUN groupadd -r newuser && useradd -r -g newuser newuser
RUN adduser newuser sudo
RUN adduser --disabled-password \
--gecos '' docker
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> \
/etc/sudoers

COPY requirements.txt .
#RUN python3 -m pip install --upgrade pip


RUN mkdir -p /home/newuser
RUN chown -R 999:999 /home/newuser

USER newuser

RUN pip install --upgrade pip
RUN pip3 install -r requirements.txt --user
#RUN pip install pyyaml

WORKDIR /project

#CMD ["sh", "-c", "python3 internal_start.py ${ARGS}"]

