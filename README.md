![main workflow](https://github.com/mongodb-developer/pymongo-fastapi-crud/actions/workflows/main.yml/badge.svg)

# Folklore Archive API

This is a read api for accessing folklore documents stored in mongo

## Running the server

Set your [Atlas URI connection string](https://docs.atlas.mongodb.com/getting-started/) as a parameter in `.env`.
Make sure you replace the username and password placeholders with your credentials.

```
ATLAS_URI=mongodb+srv://<username>:<password>@archive-testing.jvyng.mongodb.net
DB_NAME=Archive
```

Install the required dependencies:

```
python -m pip install -r requirements.txt
```

Start the server:
```
python -m uvicorn main:app --reload
```

When the application starts, navigate to the '/docs' to see all available endpoints.

The '/folklore/{id}/download' endpoint gives a pdf, so must use from a browser or other tool where a PDF is a valid response 

## Accessing AWS resources
In order to access S3 downloads, make sure creds are available on the server this is running from in `~/.aws/credentials`
```
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
```

and the default region is set to us-west-1 in `~/.aws/config`
```
[default]
region=us-east-1
```
