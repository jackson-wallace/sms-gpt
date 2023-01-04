FROM python:3
ENV PYTHONUNBUFFERED 1
ENV PORT 5000
ENV HOST 0.0.0.0
EXPOSE 5000
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/