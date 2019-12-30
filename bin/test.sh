#!/bin/sh

docker-compose -f unittest.yml up -d
docker-compose -f unittest.yml run --rm web bash -c "flask test $1"
docker-compose -f unittest.yml down
