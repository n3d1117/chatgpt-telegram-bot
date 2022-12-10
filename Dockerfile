# Use the official Python image as the base image
FROM python:3.10.8

# Create a user named appuser
RUN useradd -m appuser

# Switch to the appuser user
USER appuser

WORKDIR /home/appuser/

ENV PATH="/home/appuser/.local/bin:$PATH"

# Install pipenv
RUN pip install --user pipenv

# Pull the repository from Github
RUN git clone --depth=1 https://github.com/n3d1117/chatgpt-telegram-bot.git app

# Enter the repository directory
WORKDIR /home/appuser/app

# Install the dependencies specified in the Pipfile in the repository
RUN pipenv install --deploy

ENTRYPOINT ["python", "-m", "pipenv", "run"]
# Run the main.py file
CMD ["python", "main.py"]
