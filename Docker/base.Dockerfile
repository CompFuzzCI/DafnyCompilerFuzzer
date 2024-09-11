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
RUN apt install -y golang-go
RUN go install golang.org/x/tools/cmd/goimports@latest

#Install Rust
RUN curl --proto '=https' --tlsv1.3 https://sh.rustup.rs -sSf | sh -s -- -y

# Prepare for fuzzing
RUN mkdir data
RUN chmod +x entrypoint.sh
ENV PATH="/compfuzzci/dafny/Scripts:${PATH}"
ENV PATH="/root/go/bin:${PATH}"
ENV PATH="/root/.cargo/bin:${PATH}"

ENTRYPOINT ["/compfuzzci/entrypoint.sh"]