FROM python:3.7-alpine as builder
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /wait
RUN chmod +x /wait
COPY . .

FROM builder as app
CMD ["sh", "-c", "/wait && python -u movies.py"]

FROM builder as worker
CMD ["sh", "-c", "/wait && rq worker -u redis://redis:6379"]