#!/bin/bash
#
# description: Starts and stops the LightBuildServer, running with Python pyBottle
# to install: ln -s /root/lightbuildserver/web/lbs-service-ubuntu.sh /etc/init.d/lbs
#
### BEGIN INIT INFO
# Provides:             lbs
# Required-Start:
# Required-Stop:
# Should-Start:
# Should-Stop:
# Default-Start:        2 3 4 5
# Default-Stop:         0 1 6
# Short-Description:    LightBuildServer
### END INIT INFO

. /lib/lsb/init-functions

# start the LightBuildServer
start() {
    log_daemon_msg "Starting LightBuildServer"
    cd /root/lightbuildserver/web
    python3 ./lbs.py &
    status=0
    log_end_msg $status
}

stop() {
    log_daemon_msg "Stopping LightBuildServer"
    kill `pgrep -f "python3 ./lbs.py"`
    status=$?
    log_end_msg $status
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0
