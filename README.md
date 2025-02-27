# Folklore Archive

The **Folklore Archive** is a digital repository designed to store, manage, and retrieve folklore documents with metadata. This system consists of a **FastAPI backend** with a **MongoDB database** and an **AWS S3 integration** for file storage, along with a **Vue 3 frontend** for user interaction.

## Features
- REST API for querying folklore records by language, genre, or ID.
- Full-text metadata search for folklore collections.
- File storage using AWS S3 for PDF retrieval.
- Shibboleth authentication (planned) for access control.
- Dockerized for deployment on Reclaim Cloud.

---

## Backend Setup (FastAPI + MongoDB + AWS S3)

### Prerequisites
- Python 3.9+
- MongoDB Atlas (or local MongoDB instance)
- AWS CLI configured with credentials
- Docker (for containerized deployment)

### Environment Variables
Create a `.env` file in the root directory:

```ini
ATLAS_URI=mongodb+srv://<username>:<password>@archive-testing.jvyng.mongodb.net
DB_NAME=Archive
```

Ensure AWS credentials are available at `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
```
And set the AWS region in `~/.aws/config`:
```ini
[default]
region=us-west-1
```

### Install Dependencies
```sh
python -m pip install -r requirements.txt
```

### Run the Server
```sh
python -m uvicorn app.main:app --reload
```
Visit `http://localhost:8000/docs` for the interactive API documentation.

---

## Deployment with Docker

### Backend
```sh
docker build -t py-archive . --platform linux/amd64
```
Push the image to a registry and deploy on Reclaim Cloud.

### Frontend
```sh
docker build -t archive-frontend . --platform linux/amd64
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/folklore/` | List all folklore entries |
| `GET` | `/folklore/languages` | Get distinct languages |
| `GET` | `/folklore/genres` | Get distinct genres |
| `GET` | `/folklore/{id}` | Fetch a folklore entry by ID |
| `GET` | `/folklore/{id}/download` | Download a PDF from S3 |

---

## Future Features
- Shibboleth authentication for access control.
- Vector-based semantic search for folklore discovery.
- Folder-based navigation to mimic physical archive browsing.
- Metadata auto-extraction using AWS Lambda & OCR processing.
- Enhanced mobile UI for better user experience.

---

## Contributing
If you'd like to contribute, please submit an issue or pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/license/mit).

---

For any questions or support, please contact the repository maintainer.