#!/bin/sh

docker-compose -f unittest.yml up -d
docker-compose -f unittest.yml run --rm web bash -c "FLASK_ENV=testing flask test"
docker-compose -f unittest.yml down
