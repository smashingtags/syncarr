FROM python:3.6

# Necessary for build hooks
ARG BUILD_DATE
ARG VCS_REF

LABEL org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.vcs-url="https://github.com/syncarr/syncarr.git" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.schema-version="1.3.0"

ENV IS_IN_DOCKER 1
# default every 5 minutes
ENV SYNC_INTERVAL_SECONDS 300

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt 

CMD ["python", "/app/index.py"]