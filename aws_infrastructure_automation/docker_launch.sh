#!/bin/bash

# Define SSH key file path
KEY_FILE="secret_place"

# Define NAT host server IP
SERVER_IP_NAT="13.42.197.76"

# Define DB server IP
SERVER_IP_DB="10.2.2.41"

# Define web pubserver IP
SERVER_IP_WP="13.41.71.167"


if [ "$1" != "skip_keygen" ]; then
    ssh-keygen -R $SERVER_IP_DB
    ssh-keygen -R $SERVER_IP_NAT
    ssh-keygen -R $SERVER_IP_WP
fi


scp -i "nat_db.pem" nat_db.pem ec2-user@$SERVER_IP_NAT:~/

ssh -tt -i "nat_db.pem" ec2-user@$SERVER_IP_NAT "ssh -i \"$KEY_FILE\" ec2-user@$SERVER_IP_DB 'sudo docker stop db1 || true && sudo docker rm db1 || true && sudo docker run --name db1 -p 3306:3306 -d benpiper/aws-db1'"

ssh -i "web_key.pem" ec2-user@"$SERVER_IP_WP" 'sudo docker stop www1 || true && sudo docker rm www1 || true && sudo docker run --name www1 -p 80:80 -d benpiper/aws-www1'


