### Phame App
This Dockerized application contains all of the code you need to run PhaME as a standalone app. It has containers for 
the PhaME application, the web interface, Celery and Redis queues and a PostGREs database.

### Step by step guide to running PhaME using a web interface on a local machine. 
*Docker and git are required.*

1. clone the repo  

   ```git clone git@github.com:LANL-Bioinformatics/phame-app.git```

2. cd to the project root directory `phame-app`

   `cd phame-app`

3. run `cp .envs/.local/.postgres_template phame-app/.envs/.local/.postgres` and `cp .envs/.local/.email_template phame-app/.envs/.local/.email`.  
    Edit the `.postgres` file and change the values for `POSTGRES_USER` and `POSTGRES_PASSWORD`

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

Go through steps 1-3 as for the local installation and then:
    
1. Run `mkdir -p /path/to/api/uploads`
2. Update paths in `docker-compose-production.yml` to the volume where you want to store the users' upload files for the 
`phame` and `web` containers.
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
    For example set volumes to `-/vol_d/api/uploads:/api/static/uploads` if you want to store the upload files
on `/vol_d`
5. Create docker containers.

   `docker-compose -f docker-compose-production.yml build`

6. start docker

   `docker-compose -f docker-compose-production.yml up -d`

### Monitoring tasks
Browse to `localhost:5555` to see the Flower Dashboard. Here you can see the status of the celery workers and their tasks.

You can look at projects run by other users if you create an `admin` account and login to that account. Click on the 
admin user icon in the upper right corner and select the username for the projects you would like to view. 

### Email notifications
If you would like users to receive email notifications with the error and execution logs when their projects have finished running:
1. Setup an email client.
   We use https://www.mailgun.com/
    
2. Edit the `.email` file and change the values for `API_KEY`, `EMAIL_URL` and `SENDER`

3. Edit `phame-app/api/config.py` and set `SEND_NOTIFICATIONS = True`
