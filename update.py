import sys

from btcx import cfgmanager

if __name__ == "__main__":
    if len(sys.argv) == 2:
        backup = cfgmanager.update(sys.argv[1])
    else:
        backup = cfgmanager.update()

    print "Configuration updated. Backup saved to: %s" % backup
