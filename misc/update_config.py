import sys

from btcx import cfgmanager

if __name__ == "__main__":
    if len(sys.argv) == 2:
        backup = cfgmanager.update(sys.argv[1])
    else:
        backup = cfgmanager.update()

    if backup is None:
        print "Your configuration is already updated."
    else:
        print "Configuration updated. Backup saved to: %s" % backup
