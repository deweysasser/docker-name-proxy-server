IMAGE=name-based-proxy
DBUILDARGS=

all: image


image:
	docker build  -t $(IMAGE) $(DBUILDARGS) .


test: image
	python -m unittest -v test
