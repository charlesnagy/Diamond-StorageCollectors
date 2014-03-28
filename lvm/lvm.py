#import diamond.collector
import logging
import subprocess
import diamond

class LvmCollector(diamond.collector.Collector):
    """
    collect PV, VG, LV stats
    """

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        return {
            'path': 'lvm',
            # Leave unset to publish all
            #name parameters are essentail don't remove them
            'publish': {
                'pv': ('pv_name', 'pv_uuid', 'pe_start', 'pv_size', 'pv_free', 'pv_used', 'pv_pe_count', 'pv_pe_alloc_count'),
                'vg': ('vg_fmt', 'vg_uuid', 'vg_name', 'vg_size', 'vg_free', 'vg_extent_size', 'vg_extent_count', 'vg_free_count', 'max_lv', 'max_pv', 'pv_count', 'lv_count', 'snap_count', 'vg_seqno'),
                'lv': ('vg_name', 'lv_uuid', 'lv_name', 'lv_major', 'lv_minor', 'lv_kernel_major', 'lv_kernel_minor', 'lv_kernel_read_ahead', 'lv_size', 'seg_count', 'origin_size', 'snap_percent'),
            },
            'identifiers': {
                'pv': ('pv_name',),
                'vg': ('vg_name',),
                'lv': ('vg_name', 'lv_name'),
            },
            'commands': {
                'pv': 'pvs',
                'vg': 'vgs',
                'lv': 'lvs',
            }
        }

    def get_stats(self):
        stats = {}
        for dataset, attrs in self.config.get('publish', {}).iteritems():
            stats[dataset] = {}
            for identifier, values in self._get_attrs(dataset, attrs).iteritems():
                stats[dataset][identifier] = {}
                for metric, value in values.iteritems():
                    try:
                        if '.' in value:
                            _v = float(value)
                        else:
                            _v = int(value)
                        stats[dataset][identifier][metric] = _v
                    except ValueError:
                        pass
        return stats

    def _get_attrs(self, section, attrs):
        _command = self.config.get('commands', {}).get(section)
        ret = {}
        try:
            proc = subprocess.Popen([_command, '--nosuffix', '--noheadings', '--units', 'b', '--separator',  ':', '-o', (',').join(attrs)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
        except OSError, e:
            self.log.error('Got exception running %s command: %s' % (_command, e))
        else:
            if not proc.returncode == 0:
                self.log.error("%s" % err.replace("\n", " ").strip())
            else:
                for line in out.split("\n"):
                    _metrics = dict(zip(attrs, [ x.strip() for x in line.split(":") ]))
                    if len(_metrics) == len(attrs):
                        _identifier = '_'.join([ _metrics.get(x).replace('/', '_') for x in self.config.get('identifiers', {}).get(section, {}) ] )
                        ret[_identifier] = _metrics
        return ret

    def collect(self):
        stats = self.get_stats()
        # figure out what we're configured to get, defaulting to everything
        desired = self.config.get('publish', stats.keys())
        # for everything we want
        for stat in desired:
            if stat in stats:
		for identifier, metrics in stats[stat].iteritems():
                    for metric, value in metrics.iteritems():
                        # we have it
                        _id = '%s.%s.%s' % (stat, identifier, metric)
                        self.publish(_id, value)
            else:
                # we don't, must be somehting configured in publish so we
                # should log an error about it
                self.log.error("No such key '%s' available, issue 'stats' for "
                               "a full list", stat)

    
