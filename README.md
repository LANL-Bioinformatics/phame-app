### Step by step guide to running PhaME using a web interface on a local machine. 
*Docker and git is required.*

1. clone the repo  

   ```git clone git@github.com:LANL-Bioinformatics/phame-api.git```

2. create a .postegres file within the cloned directory `phame-api/.envs/.local/.postgres`, and add following lines to it.  
   ```
   # PostgreSQL
   # ----------
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   POSTGRES_DB=phame_api01
   POSTGRES_USER=<username>
   POSTGRES_PASSWORD=<password>
   ```
4. cd to the project root directory `phame-api`

   `cd phame-api`

5. Create docker containers.

   `docker-compose build`

6. start docker

   `docker-compose up -d`

7. initialize the database.

   `docker-compose run --rm web /bin/bash -c "python -c  'import database; database.init_db()'"`


If all went well, you can go to localhost to see the phame webpage.
