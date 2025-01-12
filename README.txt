1. RUN file 'config.sh' to build image of server and node from dockerfile 
        (WARNING!!!: it will remove all the images of docker engine --> use "-nr" to not remove other images).
2. RUN file 'run.sh':
    2.1. run.sh -s 1  --> mondatory starting server.
    2.2. run.sh -n x  --> x is the number of node from 1 to 10.
    2.3. run.sh -nn N --> N is the name of a node (e.g. node5).
3. PLAY and ENJOY with P2P File Sharing APP!
4. RUN file 'reset.sh' to remove temporary file and to stop and delete docker containers.
