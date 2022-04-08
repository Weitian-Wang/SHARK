# 1. deploy fn to nginx
    build docker image in directory /SHARK/fn, then run image
# 2. deploy bn (flask app + mysql) with docker compose
    docker-compose up under /SHARK/bn, build and run flask_app image and mysql image
### 2.1 change dockerfile of flask app to production
### 2.2 log into mysql, initialize dbms by change password, create db
    mysql -u root -p
    ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword'
    CREATE DATABASE SHARK

   
