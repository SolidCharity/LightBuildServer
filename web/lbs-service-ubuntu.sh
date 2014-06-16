#!/bin/bash
#
# description: Starts and stops the LightBuildServer, running with Python pyBottle
# to install:
#    ln -s /root/lightbuildserver/web/lbs-service-ubuntu.sh /etc/init.d/lbs
#    update-rc.d lbs defaults
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
    nohup python3 ./lbs.py &
    status=0
    log_end_msg $status
}

stop() {
    log_daemon_msg "Stopping LightBuildServer"
    pid=`pgrep -f "python3 ./lbs.py"`
    if [[ -z $pid ]]
    then
      #echo "LightBuildServer is not running"
      status=1
    else
      kill $pid
      status=$?
    fi
    log_end_msg $status
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac

exit 0
