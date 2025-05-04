# TODO

## Design Questions

- For auto-closing containers: should all connections to the same account be on the same session (e.g. share one tmux window)? And then you could probably track if there's no behavior vs behavior and shut it down that way
- Or you can do normal terminal, have multiple sessions, and when there are no sessions it stops (but then it doesn't continue ever)
    - You could have a special edge case where if you run this script with a python file/directory then that python project will run and stay alive after you close all sessions?

## MVP

- Google account login DONE
- Session tracking DONE
- Logout DONE
- Containers auto-close when not running
- Terminate button
- Upload files
- Containers have better resource caps on CPU, network, RAM, etc
- Half-decent UI

## Important

- IDE for editing your whole project (look for something online)
- Auto-terminate after 7 non-login days
- If server overloaded, disallow new entries
- Give an ip address
- ip tracking for security
- Loading until it loads
- If user loses connection with container go back to loading screen

## Other Stuff

- Admin view on resources/containers
    - way to see malicious users and ban them
- email users on 5th consecutive non-login day
- something with ddos