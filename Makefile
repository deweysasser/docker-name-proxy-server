IMAGE=name-based-proxy
DBUILDARGS=

all: image


image:
	docker build  -t $(IMAGE) $(DBUILDARGS) .


test: image
#	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy --route53 --public-ip-service --key $(AWS_ACCESS_KEY_ID) --secret $(AWS_SECRET_ACCESS_KEY)
	./test.sh
