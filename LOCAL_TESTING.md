# Local Testing with Docker

If you want to test this add-on locally before deploying to Home Assistant, you can build and run it using Docker:

## Building the Docker Image

1. Navigate to the wheel-tracker directory:
   ```
   cd wheel-tracker-addon/wheel-tracker
   ```

2. Build the Docker image:
   ```
   docker build -t wheel-tracker .
   ```

## Running the Container

Run the container with the following command:

```bash
docker run -d \
  --name wheel-tracker \
  -p 5000:5000 \
  -e DATABASE_URL="sqlite:///data/database.db" \
  -e SECRET_KEY="your-secret-key" \
  -v "$(pwd)/data:/data" \
  wheel-tracker
```

This will:
- Map port 5000 to your host
- Store the database in a local data directory
- Set an environment variable for the secret key

## Accessing the Application

Open your browser and navigate to:
```
http://localhost:5000
```

## Stopping the Container

```bash
docker stop wheel-tracker
docker rm wheel-tracker
``` 