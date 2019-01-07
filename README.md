### Step by step guide to running PhaME using a web interface on a local machine. 
*Docker and git are required.*

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
3. cd to the project root directory `phame-api`

   `cd phame-api`

4. Create docker containers.

   `docker-compose -f docker-compose-local.yml build`

5. start docker

   `docker-compose -f docker-compose-local.yml up -d`

6. initialize the database.

   `docker-compose -f docker-compose-local.yml run --rm web /bin/bash -c "python -c  'import database; database.init_db()'"`


If all went well, you can go to localhost to see the phame webpage.

### Step by step guide to running PhaME using a web interface on a production machine.
The user input files can require a lot of storage space. Use these instructions if you want to store the users' data on 
a data volume that is different from the main volume where the Docker container is created. 

*Docker and git are required.*

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
3. cd to the project root directory `phame-api`

   `cd phame-api`

4. Update paths in `docker-compose-production.yml` to the volume where you want to store the users' upload files for the 
`phame` and `web` containers. For example: `/vol_d/api/uploads:/api/static/uploads` if you want to store the upload files
on `/vol_d`
    ```
    phame:
        volumes:
          - phame_data:/phame_api/media
          - /path/to/api/uploads:/api/static/uploads
    web:
        volumes:
          - phame_data:/phame_api/media
          -/path/to/api/uploads:/api/static/uploads
    ```

5. Create docker containers.

   `docker-compose -f docker-compose-production.yml build`

6. start docker

   `docker-compose -f docker-compose-production.yml up -d`

###Monitoring tasks
Browse to `localhost:5555` to see the Flower Dashboard. Here you can see the status of the celery workers and their tasks.

You can look at projects run by other users if you create an `admin` account and login to that account. Click on the 
admin user icon in the upper right corner and select the username for the projects you would like to view. 
