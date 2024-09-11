FROM --platform=linux/x86_64 ubuntu:22.04
RUN mkdir /compfuzzci
COPY entrypoint.sh /compfuzzci/entrypoint.sh
WORKDIR /compfuzzci

RUN apt-get update
RUN apt-get -y upgrade
RUN apt install -y unzip wget curl

#install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

#Install Dotnet
RUN apt-get install -y dotnet-sdk-6.0

#Install Java
RUN apt install -y openjdk-17-jdk

#Install NodeJS
RUN apt install -y nodejs npm
RUN npm install bignumber.js

#Install Python
RUN apt install -y python3.11 python3-pip -y
RUN pip install boto3 requests chardet

#Install Go
RUN wget https://go.dev/dl/go1.23.1.linux-amd64.tar.gz
RUN tar -C /root -xzf go1.23.1.linux-amd64.tar.gz
ENV PATH="/root/go/bin:${PATH}"
RUN go install golang.org/x/tools/cmd/goimports@latest

#Install Rust
RUN curl --proto '=https' --tlsv1.3 https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"