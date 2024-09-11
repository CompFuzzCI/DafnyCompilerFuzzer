FROM --platform=linux/x86_64 public.ecr.aws/compfuzzci/compfuzzci-base:latest
ARG AUTHOR
ARG BRANCH

# Install Dafny
RUN git clone https://github.com/dafny-lang/dafny.git
RUN cd dafny && \
    git remote add merge-head https://github.com/${AUTHOR}/dafny.git && \
    git fetch merge-head && \
    git checkout -b ${BRANCH} merge-head/${BRANCH} && \
    make exe && \
    make z3-ubuntu

# Prepare for fuzzing
RUN chmod +x entrypoint.sh
ENV PATH="/compfuzzci/dafny/Scripts:${PATH}"

ENTRYPOINT ["/compfuzzci/entrypoint.sh"]