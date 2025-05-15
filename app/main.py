from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
	return {"message": "Investec ML Reports API is running!"}