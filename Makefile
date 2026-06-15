.PHONY: install sample run docker-build docker-run clean

install:        ## Cai dependency
	pip install -r requirements.txt

sample:         ## Sinh du lieu gia lap
	python -m src.generate_sample_data

run:            ## Chay pipeline (data that o data/input)
	python run.py

demo:           ## Sinh data gia lap + chay
	python run.py --sample

docker-build:   ## Build image Docker
	docker build -t zion-recon:latest .

docker-run:     ## Chay container tren data that, lay ket qua ra ./data/output
	docker run --rm -v $(PWD)/data/output:/app/data/output zion-recon:latest

clean:          ## Xoa output & cache
	rm -rf data/output/* __pycache__ src/__pycache__
