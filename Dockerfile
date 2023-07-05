# this was recommended by https://towardsdatascience.com/deploy-containerized-plotly-dash-app-to-heroku-with-ci-cd-f82ca833375c

FROM python:3.9-slim-buster

WORKDIR /container_app

# RUN pwd
# RUN ls

COPY ./requirements.txt /container_app/requirements.txt

# RUN ls

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /container_app

RUN useradd -m containerUser
USER containerUser

# filling in and hard-coding port number from example below + adding timeout
CMD gunicorn --bind 0.0.0.0:7860 --timeout 1000 dash-example-app-rebuild:server



# this was the default created by VSCode (should I keep any of this?):

# # For more information, please refer to https://aka.ms/vscode-docker-python
# FROM python:3.9-slim

# EXPOSE 7860

# # Keeps Python from generating .pyc files in the container
# ENV PYTHONDONTWRITEBYTECODE=1

# # Turns off buffering for easier container logging
# ENV PYTHONUNBUFFERED=1

# # Install pip requirements
# COPY requirements.txt .
# RUN python -m pip install -r requirements.txt

# WORKDIR /app
# COPY . /app

# # Creates a non-root user with an explicit UID and adds permission to access the /app folder
# # For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# # During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# CMD ["gunicorn", "--bind", "0.0.0.0:7860", "dash-example-app:app"]





# this is recommended by https://towardsdatascience.com/how-to-deploy-a-panel-app-to-hugging-face-using-docker-6189e3789718

# FROM python:3.9

# WORKDIR /code

# COPY ./requirements.txt /code/requirements.txt

# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# RUN pwd

# COPY . .

# RUN dir -s

# CMD ["python", "dash-example-app.py"] 

#  (does the rest of this apply for dash app?) , "--address", "0.0.0.0", "--port", "7860", "--allow-websocket-origin", "sophiamyang-panel-example.hf.space"]

