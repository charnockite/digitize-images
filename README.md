# Digitize images
Streamlit web app to help with simple digitization projects.

## Features
- Upload a PDF document
- Extract text and numbers from documents, preserving table, column, or row structure as possible
- Allow user to select what parts of preserved structure to retain by checking on or off columns and rows in resulting data
- Export selected data as CSV

## Running locally with Docker (recommended for Windows)

Poppler and Tesseract can be tricky to install on Windows.  The Docker image
bundles all system dependencies so you can run the app on any platform without
any extra setup.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Build the image

```bash
docker build -t digitize-images .
```

### Run the container

```bash
docker run -p 8501:8501 digitize-images
```

Then open your browser and navigate to **http://localhost:8501**.

### Stopping the container

Press `Ctrl+C` in the terminal where `docker run` is executing, or run:

```bash
docker ps                        # find the CONTAINER ID
docker stop <CONTAINER ID>
```
