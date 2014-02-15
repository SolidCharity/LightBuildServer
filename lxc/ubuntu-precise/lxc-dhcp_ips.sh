awk '{ print $4,$3 }' /var/lib/misc/dnsmasq.leases | column -t
