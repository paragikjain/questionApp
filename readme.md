### This is private repo
# Instructions
* First set MONGO_URI in your env
`$env:MONGO_URI = "mongodb+srv://<username>:<password>@questionform.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"`
* Run below command to start server
`uvicorn main:app --reload --reload-dir`