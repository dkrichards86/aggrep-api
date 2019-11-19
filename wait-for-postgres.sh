#!/bin/sh
cmd="$@"
until psql -h postgres -U aggrep -c '\q'; do
   >&2 echo "Postgres is unavailable - sleeping"
   sleep 1
done

>&2 echo "Postgres is ready - executing command"
exec $cmd

