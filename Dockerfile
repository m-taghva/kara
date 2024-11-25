FROM ubuntu:20.04

ENV COSBENCH_VERSION="0.4.2.c4" COSBENCH_DIR="/tmp/cosbench"
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN echo "=================== apt update ===================" && \
    sed -i 's/# deb/deb/g' /etc/apt/sources.list && \
    apt update 

RUN echo "=================== Install basic packages ===================" && \
    apt install -y git sudo ntp dnsutils procps bmon openjdk-8-jre apt-utils curl unzip netcat-openbsd nano python3 python3-distutils pip iputils-ping

#RUN echo "=================== install pip ===================" && \
#    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
#    python3 get-pip.py && \
#    rm get-pip.py

RUN echo "=================== Installing python packages ===================" && \
    pip install jdatetime pytz pyyaml statsd requests dominate datetime matplotlib pandas alive-progress BeautifulSoup4 wikitextparser


RUN echo "=================== Curl Cosbench ===================" && \
    . /etc/profile && curl --retry 5 -Ls "https://github.com/intel-cloud/cosbench/releases/download/v0.4.2.c4/0.4.2.c4.zip" > /tmp/cosbench.zip && \
    cd /tmp ; unzip -q /tmp/cosbench.zip && \
    mv "/tmp/${COSBENCH_VERSION}" ${COSBENCH_DIR} && \
    rm /tmp/cosbench.zip && apt-get autoremove -y && \
    chmod +x ${COSBENCH_DIR}/cli.sh && \
    ln -s ${COSBENCH_DIR}/cli.sh /usr/bin/cosbench

RUN echo "=================== Installing Cosbench ===================" && \
    sed -i -e 's/TOOL_PARAMS=""/TOOL_PARAMS="-N"/g' ${COSBENCH_DIR}/cosbench-start.sh && \
    sed -i -e 's/cat $BOOT_LOG/if [ "$SERVICE_NAME" = "controller" ]; then tail -f $BOOT_LOG; else cat $BOOT_LOG; fi/g' ${COSBENCH_DIR}/cosbench-start.sh && \
    sed -i -e 's/java/java /g' ${COSBENCH_DIR}/cosbench-start.sh

RUN mkdir -p /home/kara
COPY . /home/kara/

RUN echo "=================== Clone kara ===================" && \
    cd /home/kara && \
    rm -rf kara_chart.gif kara_tools.gif LICENSE docker/kara-docker-compose.yaml Dockerfile sequential_diagram && \
    cp -r status_reporter/jsons manager/sample_configs/jsons && \
    cp -r status_reporter/metrics manager/sample_configs/metrics && \
    cp -r manager/scenario_dir manager/sample_configs/scenario_dir && \
    cp -r config_gen/workloads-configs manager/sample_configs/workloads-configs

RUN echo "=================== Installing kara ===================" &&\
    cd /home/kara && \
    chmod +x manager/configure.sh docker/init.sh docker/healthcheck.sh  && \
    cd manager/ && \
    ./configure.sh 
#    chown -Rv kara:kara /home/kara

RUN echo "=================== Setting timezone ===================" && \
    ln -sf /usr/share/zoneinfo/Asia/Tehran /etc/localtime && \
    echo "Asia/Tehran" > /etc/timezone

EXPOSE 18088 18089 19088 19089
CMD cd $COSBENCH_DIR; sudo sh ./start-all.sh  
WORKDIR /home/kara
