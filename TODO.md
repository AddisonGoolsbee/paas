# TODO

## Proof of Concept

- Terminal which streams stdout, stderr, and stdin
- Docker container spawned for each process

## MVP

- Google account login
- Database to keep track of users -> logged in user pulls up previous project
- Upload a zip file optionally, and server will unzip and run project
- Containers auto-close when not running
- Containers have resource caps on CPU, network, RAM, etc
- Terminate button

## Important

- IDE for editing your whole project (look for something online)
- Auto-terminate after 7 non-login days
- If server overloaded, disallow new entries
- ip tracking

## Other Stuff

- Admin view on resources/containers
    - way to see malicious users and ban them
- email users on 5th consecutive non-login day
- something with ddos