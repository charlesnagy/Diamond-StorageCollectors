# coding=utf-8

"""
Collect flashcache stats

#### Example Configuration

MemcachedCollector.conf
```
    enabled = True
```
"""

import diamond.collector
import re
import os
from collections import defaultdict


class FlashcacheCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(FlashcacheCollector, self).get_default_config_help()
        config_help.update({
            'publish': "Which rows of 'status' you would like to publish."
            + " type 'cat /proc/flashcache/<cache name>/flashcache_stats' and hit enter to see the list"
            + " of possibilities. Leave unset to publish all.",
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(FlashcacheCollector, self).get_default_config()
        config.update({
            'path':     'flashcache',
        })
        return config

    def get_raw_stats(self):
        data = dict()
        # connect
        try:
            d = '/proc/flashcache'
            for _device in os.listdir(d): 
                if os.path.isdir(os.path.join(d,_device)):
                    with open(os.path.join(d, _device, 'flashcache_stats'), 'r') as _stats:
                        data[_device] = _stats.read().strip('\n')
        except IOError:
            self.log.exception('Failed to read stats')
        return data

    def get_stats(self):
        stats = defaultdict(dict)
        data = self.get_raw_stats()

        # parse stats
        for _device, _stats in data.iteritems():
            for metric, value in [ _s.split('=') for _s in _stats.split(' ')]:
                if metric and value:
                    stats[_device][metric] = value
        return dict(stats)

    def collect(self):
        stats = self.get_stats()

        for device, _stats in stats.iteritems():
            # figure out what we're configured to get, defaulting to everything
            desired = self.config.get('publish', _stats.keys())
            for stat in desired:
                if stat in _stats:
                    self.publish(device + "." + stat, _stats[stat])
                else:
                    # we don't, must be somehting configured in publish so we
                    # should log an error about it
                    self.log.error("No such key '%s' available, issue 'stats' "
                                   "for a full list", stat)
