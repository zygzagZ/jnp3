FROM python:3.7-alpine
WORKDIR /app
ENV FLASK_APP movies.py
ENV FLASK_RUN_HOST 0.0.0.0
# RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /wait
RUN chmod +x /wait
COPY . .
CMD ["sh", "-c", "/wait && python movies.py"]