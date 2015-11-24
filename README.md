# collectd_to_cloudwatch
POC of collectd to cloudwatch

* Usage
 * copy collectd_to_cloudwatch.py where you want (ex /var/lib/collectd/python)
 * copy collectd_to_cloudwatch.conf and collectd_to_cloudwatch.yaml to your collectd.conf includedir configuration (generally /etc/collectd.d/ or /etc/collectd/collectd.d/)
 * edit collectd_to_cloudwatch.conf, define the path to collectd_to_cloudwatch.py and to collectd_to_cloudwatch.yaml and change the region
 * restart collectd

* Extra configuration
 * By default values will be writed in the namespace "COLLECTD" you can change it (for exemple AWS/EC2)
 * You can define more plugin/type in collectd_to_cloudwatch.yaml, all defined plugin/type will be send to cloudwatch.

* collectd_to_cloudwatch.yaml format :
```yaml
plugin name:
   type name:
     unit: optional default is None. Cloudwatch unit for the plugin/type (must be one of the cloudwatch supported unit, currently : Seconds | Microseconds | Milliseconds | Bytes | Kilobytes | Megabytes | Gigabytes | Terabytes | Bits | Kilobits | Megabits | Gigabits | Terabits | Percent | Count | Bytes/Second | Kilobytes/Second | Megabytes/Second | Gigabytes/Second | Terabytes/Second | Bits/Second | Kilobits/Second | Megabits/Second | Gigabits/Second | Terabits/Second | Count/Second | None)
     # optional :
     type-instance:
        type-intance1-name: Cloudwatch unit for the plugin/type/type-instance
        type-intance2-name: Cloudwatch unit for the plugin/type/type-instance
```
