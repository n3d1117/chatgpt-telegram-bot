
#!/bin/bash

# Set the PORT environment variable (important!)
export PORT=10000  # Replace 10000 with your desired/assigned port

# Start your Gunicorn process in the background
gunicorn bot.main:app --bind 0.0.0.0:$PORT & 
